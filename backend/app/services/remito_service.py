"""Casos de uso de remitos: generar, empaquetar, despachar, recibir, anular y extraviar.

El remito decide su estado (patrón State); este servicio orquesta los efectos sobre ejemplares,
préstamos e incidencias en una sola transacción (ver ``docs/tecnica/03-maquinas-de-estado.md``,
«Acoplamiento entre máquinas»).
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from app.exceptions import (
    EjemplarEnOtroRemito,
    EjemplarNoDisponible,
    EjemplarNoEncontrado,
    EjemplarNoPerteneceASede,
    PermisoDenegado,
    PrestamoNoEncontrado,
    RemitoInvalido,
    RemitoNoEncontrado,
)
from app.models.ejemplar import Ejemplar, EstadoFisico
from app.models.incidencia import Incidencia, OrigenIncidencia, TipoIncidencia
from app.models.paginacion import Pagina
from app.models.prestamo import Prestamo
from app.models.remito import (
    LineaRemito,
    MotivoRemito,
    MovimientoRemito,
    RecepcionLinea,
    Remito,
    ResultadoLinea,
)
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.states.remito import EstadoRemitoEnum
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef
from app.repositories.interfaces.prestamo_repository import FiltroRemitos
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.utils.reloj import Reloj


@dataclass(frozen=True)
class LineaNueva:
    ejemplar_id: int
    prestamo_id: int | None = None


@dataclass(frozen=True)
class DetalleRemito:
    remito: Remito
    historial: list[MovimientoRemito]
    incidencias: list[Incidencia]


class RemitoService:
    """Envíos entre sedes con trazabilidad (proceso obligatorio 5)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- generar --------------------------------------------------------------------------

    def generar(
        self,
        actor: Usuario,
        sede_destino_id: int,
        motivo: MotivoRemito,
        lineas: Sequence[LineaNueva],
        observaciones: str | None = None,
    ) -> Remito:
        """Genera un remito desde la sede del bibliotecario (CU-REM-01).

        Un envío lleva préstamos interbibliotecarios ``Solicitado`` con ese origen y destino; un
        traslado lleva ejemplares disponibles de la sede. Los retornos los genera el sistema.

        Raises:
            PermisoDenegado, RemitoInvalido, SedeEnBaja (CA-REM-11), EjemplarNoPerteneceASede
            (CA-REM-12), EjemplarEnOtroRemito (CA-REM-13), EjemplarNoDisponible.
        """
        actor.exigir(Permiso.REMITO_OPERAR)
        if motivo == MotivoRemito.RETORNO:
            raise RemitoInvalido(
                "Los remitos de retorno se generan al registrar la devolución.",
                [{"campo": "motivo", "problema": "retorno_automatico"}],
            )
        assert actor.sede_id is not None
        with self._transaccion():
            origen = self._uow.sedes.obtener_para_operar(actor.sede_id)
            destino = self._uow.sedes.obtener_para_operar(sede_destino_id)
            assert origen.id is not None and destino.id is not None
            ahora = self._reloj.ahora()
            numero = self._uow.remitos.siguiente_numero(self._reloj.hoy().year)
            ejemplares: list[Ejemplar] = []
            prestamos: list[Prestamo] = []
            detalle: list[LineaRemito] = []
            for nueva in lineas:
                ejemplar = self._ejemplar_libre(nueva.ejemplar_id)
                if not ejemplar.pertenece_a(origen.id) or ejemplar.sede_actual_id != origen.id:
                    raise EjemplarNoPerteneceASede(
                        f"El ejemplar {ejemplar.codigo_inventario} no está en la sede origen "
                        f"{origen.nombre}.",
                        [
                            {
                                "campo": "lineas",
                                "problema": "fuera_de_sede_origen",
                                "ejemplar_id": ejemplar.id,
                            }
                        ],
                    )
                if motivo == MotivoRemito.ENVIO:
                    prestamos.append(self._prestamo_para_enviar(nueva, ejemplar, destino.id))
                elif not ejemplar.esta_disponible:
                    raise EjemplarNoDisponible(
                        f"El ejemplar {ejemplar.codigo_inventario} no está disponible para "
                        "trasladarlo.",
                        [
                            {
                                "campo": "lineas",
                                "problema": "no_disponible",
                                "ejemplar_id": ejemplar.id,
                            }
                        ],
                    )
                ejemplares.append(ejemplar)
                detalle.append(
                    LineaRemito(nueva.ejemplar_id, nueva.prestamo_id, ejemplar.estado_fisico)
                )
            remito = Remito.generar(
                numero=numero,
                sede_origen_id=origen.id,
                sede_destino_id=destino.id,
                motivo=motivo,
                lineas=detalle,
                observaciones=observaciones,
                actor=_ref(actor),
                ahora=ahora,
            )
            self._uow.remitos.agregar(remito)
            for prestamo in prestamos:
                prestamo.enviar(_ref(actor), ahora, numero)
                self._uow.prestamos.guardar(prestamo)
            if motivo == MotivoRemito.TRASLADO:
                for ejemplar in ejemplares:
                    ejemplar.apartar(_ref(actor), ahora, f"Traslado en el remito {numero}")
                    self._uow.ejemplares.guardar(ejemplar)
        return self._releer(remito)

    def generar_retorno(self, prestamo: Prestamo, ejemplar: Ejemplar, actor: UsuarioRef) -> Remito:
        """Remito de vuelta del ejemplar a su sede propietaria (RF-REM-04, RF-DEV-09).

        No abre transacción: lo usan otros casos de uso (devolución, cancelación sin retiro)
        dentro de la suya. El ejemplar tiene que estar ``Apartado`` en la sede donde está.
        """
        assert ejemplar.id is not None
        numero = self._uow.remitos.siguiente_numero(self._reloj.hoy().year)
        remito = Remito.generar(
            numero=numero,
            sede_origen_id=ejemplar.sede_actual_id,
            sede_destino_id=ejemplar.sede_propietaria_id,
            motivo=MotivoRemito.RETORNO,
            lineas=[LineaRemito(ejemplar.id, prestamo.id, ejemplar.estado_fisico)],
            observaciones=f"Retorno del préstamo {prestamo.numero}",
            actor=actor,
            ahora=self._reloj.ahora(),
        )
        self._uow.remitos.agregar(remito)
        return remito

    # --- ciclo de vida --------------------------------------------------------------------

    def empaquetar(self, actor: Usuario, remito_id: int) -> Remito:
        with self._transaccion():
            remito = self._de_mi_sede(actor, remito_id, origen=True)
            remito.empaquetar(_ref(actor), self._reloj.ahora())
            self._uow.remitos.guardar(remito)
        return self._releer(remito)

    def despachar(self, actor: Usuario, remito_id: int) -> Remito:
        """Sale de la sede origen y los ejemplares quedan ``En tránsito`` (CA-REM-09)."""
        with self._transaccion():
            remito = self._de_mi_sede(actor, remito_id, origen=True)
            ahora = self._reloj.ahora()
            remito.despachar(_ref(actor), ahora)
            for linea in remito.lineas:
                ejemplar = self._ejemplar(linea.ejemplar_id)
                ejemplar.poner_en_transito(_ref(actor), ahora, f"Despachado en {remito.numero}")
                self._uow.ejemplares.guardar(ejemplar)
            self._uow.remitos.guardar(remito)
        return self._releer(remito)

    def pasar_a_transito(self, actor: Usuario, remito_id: int) -> Remito:
        with self._transaccion():
            remito = self._de_mi_sede(actor, remito_id, origen=True)
            remito.pasar_a_transito(_ref(actor), self._reloj.ahora())
            self._uow.remitos.guardar(remito)
        return self._releer(remito)

    def recibir(
        self, actor: Usuario, remito_id: int, recepcion: Sequence[RecepcionLinea]
    ) -> DetalleRemito:
        """La sede destino verifica cada ejemplar (CU-REM-04 y 05).

        Según el motivo y el resultado de cada línea:

        * recibido en un **envío**: queda ``Apartado`` en destino hasta que el socio lo retira;
        * recibido en un **retorno**: ``Disponible`` en su sede;
        * recibido en un **traslado**: cambia de sede propietaria y queda ``Disponible``;
        * **dañado**: ``En revisión`` con incidencia; **destruido**: ``Baja`` con incidencia.
          En ambos casos el préstamo del envío se cancela.
        * **retorno de un ejemplar devuelto dañado**: pasa a ``En revisión`` en su sede sin otra
          incidencia (ya se registró en la devolución).
        """
        with self._transaccion():
            remito = self._de_mi_sede(actor, remito_id, origen=False)
            ahora = self._reloj.ahora()
            yo = _ref(actor)
            remito.recibir(recepcion, yo, ahora)
            for linea in remito.lineas:
                ejemplar = self._ejemplar(linea.ejemplar_id)
                ejemplar.llegar_a(remito.sede_destino_id)
                assert linea.estado_fisico_llegada is not None
                ejemplar.estado_fisico = linea.estado_fisico_llegada
                texto = f"Recibido en {remito.numero}"
                if linea.resultado == ResultadoLinea.RECIBIDO:
                    if remito.motivo == MotivoRemito.ENVIO:
                        ejemplar.apartar(yo, ahora, f"{texto}: espera el retiro del socio")
                    else:
                        if remito.motivo == MotivoRemito.TRASLADO:
                            ejemplar.trasladar_a(remito.sede_destino_id)
                        ejemplar.liberar(yo, ahora, texto)
                elif _danio_ya_informado(remito, linea):
                    ejemplar.enviar_a_revision(yo, ahora, f"{texto}: dañado en la devolución")
                else:
                    self._incidencia_de_recepcion(remito, linea, ejemplar, yo)
                self._uow.ejemplares.guardar(ejemplar)
                ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, yo)
            self._uow.remitos.guardar(remito)
        return self.detalle(actor, remito_id)

    def anular(self, actor: Usuario, remito_id: int, motivo: str) -> Remito:
        """Antes del despacho: libera los ejemplares y cancela los préstamos (CA-REM-15)."""
        with self._transaccion():
            remito = self._de_mi_sede(actor, remito_id, origen=True)
            if remito.motivo == MotivoRemito.RETORNO:
                raise RemitoInvalido(
                    "Un remito de retorno no se anula: el ejemplar tiene que volver a su sede.",
                    [{"campo": "motivo", "problema": "retorno"}],
                )
            ahora = self._reloj.ahora()
            yo = _ref(actor)
            remito.anular(motivo, yo, ahora)
            for linea in remito.lineas:
                ejemplar = self._ejemplar(linea.ejemplar_id)
                ejemplar.liberar(yo, ahora, f"Remito {remito.numero} anulado")
                self._uow.ejemplares.guardar(ejemplar)
                self._cancelar_prestamo(linea, yo, f"Remito {remito.numero} anulado")
                ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, yo)
            self._uow.remitos.guardar(remito)
        return self._releer(remito)

    def marcar_extraviado(self, actor: Usuario, remito_id: int, observacion: str) -> Remito:
        """Un envío que superó el plazo de tránsito se da por perdido (CU-REM-06).

        Los ejemplares pasan a ``Baja`` con incidencia y los préstamos del envío se cancelan.
        """
        actor.exigir(Permiso.REMITO_EXTRAVIO)
        with self._transaccion():
            remito = self._para_modificar(remito_id)
            if actor.rol == Rol.BIBLIOTECARIO and not (
                actor.opera_en(remito.sede_origen_id) or actor.opera_en(remito.sede_destino_id)
            ):
                raise PermisoDenegado("El remito no es de su sede.")
            plazo = self._uow.parametros.vigentes().transito_maximo_dias
            ahora = self._reloj.ahora()
            yo = _ref(actor)
            remito.marcar_extraviado(plazo, observacion, yo, ahora)
            for linea in remito.lineas:
                ejemplar = self._ejemplar(linea.ejemplar_id)
                motivo = f"Extraviado en el remito {remito.numero}"
                ejemplar.registrar_baja(motivo, yo, ahora)
                self._uow.ejemplares.guardar(ejemplar)
                self._uow.incidencias.agregar(
                    Incidencia(
                        tipo=TipoIncidencia.EXTRAVIO,
                        origen=OrigenIncidencia.REMITO,
                        ejemplar_id=linea.ejemplar_id,
                        descripcion=observacion,
                        fecha=ahora,
                        usuario=yo,
                        socio_id=self._socio_de(linea.prestamo_id),
                        prestamo_id=linea.prestamo_id,
                        remito_id=remito.id,
                    )
                )
                if remito.motivo == MotivoRemito.ENVIO:
                    self._cancelar_prestamo(linea, yo, motivo)
            self._uow.remitos.guardar(remito)
        return self._releer(remito)

    # --- lectura --------------------------------------------------------------------------

    def detalle(self, actor: Usuario, remito_id: int) -> DetalleRemito:
        """Remito con su detalle, historial e incidencias (CA-REM-07, RF-REM-14)."""
        actor.exigir(Permiso.REMITO_LEER)
        remito = self._uow.remitos.obtener(remito_id)
        if remito is None:
            raise RemitoNoEncontrado("El remito solicitado no existe.")
        self._exigir_visible(actor, remito)
        return DetalleRemito(
            remito,
            self._uow.remitos.historial(remito_id),
            self._uow.incidencias.de_remito(remito_id),
        )

    def listar(
        self,
        actor: Usuario,
        estado: EstadoRemitoEnum | None,
        motivo: MotivoRemito | None,
        sede_id: int | None,
        numero: str | None,
        solo_abiertos: bool,
        page: int,
        size: int,
    ) -> Pagina[Remito]:
        """El bibliotecario ve los remitos de su sede (como origen o destino)."""
        actor.exigir(Permiso.REMITO_LEER)
        if actor.rol == Rol.BIBLIOTECARIO:
            sede_id = actor.sede_id
        filtro = FiltroRemitos(estado, motivo, sede_id, numero, solo_abiertos)
        remitos, total = self._uow.remitos.listar(filtro, page, size)
        return Pagina(remitos, total, page, size)

    # --- internos -------------------------------------------------------------------------

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()

    def _para_modificar(self, remito_id: int) -> Remito:
        remito = self._uow.remitos.obtener_para_modificar(remito_id)
        if remito is None:
            raise RemitoNoEncontrado("El remito solicitado no existe.")
        return remito

    def _de_mi_sede(self, actor: Usuario, remito_id: int, *, origen: bool) -> Remito:
        """Remito bloqueado; exige ser bibliotecario de la sede origen o destino (RF-REM-07)."""
        actor.exigir(Permiso.REMITO_OPERAR)
        remito = self._para_modificar(remito_id)
        sede = remito.sede_origen_id if origen else remito.sede_destino_id
        if not actor.opera_en(sede):
            quien = "origen" if origen else "destino"
            raise PermisoDenegado(f"Solo la sede {quien} del remito puede hacer esta operación.")
        return remito

    def _exigir_visible(self, actor: Usuario, remito: Remito) -> None:
        if actor.rol == Rol.BIBLIOTECARIO and not (
            actor.opera_en(remito.sede_origen_id) or actor.opera_en(remito.sede_destino_id)
        ):
            raise PermisoDenegado("El remito no es de su sede.")

    def _ejemplar(self, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._uow.ejemplares.obtener_para_modificar(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado("El ejemplar no existe.")
        return ejemplar

    def _ejemplar_libre(self, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._ejemplar(ejemplar_id)
        otro = self._uow.remitos.abierto_con_ejemplar(ejemplar_id)
        if otro is not None:
            raise EjemplarEnOtroRemito(
                f"El ejemplar {ejemplar.codigo_inventario} ya está en el remito {otro.numero}.",
                [{"campo": "lineas", "problema": "en_otro_remito", "ejemplar_id": ejemplar_id}],
            )
        return ejemplar

    def _prestamo_para_enviar(
        self, nueva: LineaNueva, ejemplar: Ejemplar, destino_id: int
    ) -> Prestamo:
        prestamo = (
            self._uow.prestamos.obtener_para_modificar(nueva.prestamo_id)
            if nueva.prestamo_id is not None
            else None
        )
        if prestamo is None:
            raise PrestamoNoEncontrado(
                "Cada línea de un envío lleva un préstamo existente.",
                [{"campo": "lineas", "problema": "prestamo_inexistente"}],
            )
        valido = (
            prestamo.es_interbibliotecario
            and prestamo.estado_nombre == EstadoPrestamoEnum.SOLICITADO
            and prestamo.ejemplar_id == ejemplar.id
            and prestamo.sede_destino_id == destino_id
            and ejemplar.estado_nombre == EstadoEjemplarEnum.APARTADO
        )
        if not valido:
            raise RemitoInvalido(
                f"El préstamo {prestamo.numero} no corresponde a este envío: tiene que ser "
                "interbibliotecario, estar solicitado y tener ese ejemplar y esa sede destino.",
                [
                    {
                        "campo": "lineas",
                        "problema": "prestamo_no_corresponde",
                        "prestamo_id": prestamo.id,
                    }
                ],
            )
        return prestamo

    def _cancelar_prestamo(self, linea: LineaRemito, actor: UsuarioRef, motivo: str) -> None:
        if linea.prestamo_id is None:
            return
        prestamo = self._uow.prestamos.obtener_para_modificar(linea.prestamo_id)
        if prestamo is not None and prestamo.estado_nombre in (
            EstadoPrestamoEnum.SOLICITADO,
            EstadoPrestamoEnum.EN_ENVIO,
        ):
            prestamo.cancelar(motivo, actor, self._reloj.ahora())
            self._uow.prestamos.guardar(prestamo)

    def _socio_de(self, prestamo_id: int | None) -> int | None:
        if prestamo_id is None:
            return None
        prestamo = self._uow.prestamos.obtener(prestamo_id)
        return prestamo.socio_id if prestamo else None

    def _incidencia_de_recepcion(
        self, remito: Remito, linea: LineaRemito, ejemplar: Ejemplar, actor: UsuarioRef
    ) -> None:
        ahora = self._reloj.ahora()
        descripcion = linea.observacion or "Sin observación"
        if linea.resultado == ResultadoLinea.DESTRUIDO:
            tipo = TipoIncidencia.DESTRUCCION
            ejemplar.registrar_baja(f"Destruido en el remito {remito.numero}", actor, ahora)
        else:
            tipo = TipoIncidencia.DANIO
            ejemplar.enviar_a_revision(actor, ahora, f"Dañado en el remito {remito.numero}")
        self._uow.incidencias.agregar(
            Incidencia(
                tipo=tipo,
                origen=OrigenIncidencia.REMITO,
                ejemplar_id=linea.ejemplar_id,
                descripcion=descripcion,
                fecha=ahora,
                usuario=actor,
                socio_id=self._socio_de(linea.prestamo_id),
                prestamo_id=linea.prestamo_id,
                remito_id=remito.id,
            )
        )
        if remito.motivo == MotivoRemito.ENVIO:
            self._cancelar_prestamo(linea, actor, f"Ejemplar {tipo.value.lower()} en el envío")

    def _releer(self, remito: Remito) -> Remito:
        assert remito.id is not None
        return self._uow.remitos.obtener(remito.id) or remito


def _danio_ya_informado(remito: Remito, linea: LineaRemito) -> bool:
    """Retorno de un ejemplar que el socio devolvió dañado y llega igual."""
    return (
        remito.motivo == MotivoRemito.RETORNO
        and linea.resultado == ResultadoLinea.DANADO
        and linea.estado_fisico_salida == EstadoFisico.DANADO
    )


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
