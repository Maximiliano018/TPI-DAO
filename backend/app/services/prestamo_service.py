"""Casos de uso de préstamos: registrar, entregar, renovar, cancelar y detectar vencidos."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date

from app.exceptions import (
    DisponibilidadCambiada,
    EjemplarNoEncontrado,
    EjemplarNoRecibido,
    LibroNoEncontrado,
    PermisoDenegado,
    PrestamoNoEncontrado,
    SedeNoEncontrada,
    SinEjemplaresDisponibles,
    SocioNoEncontrado,
    TransicionInvalida,
)
from app.models.devolucion import Devolucion, Multa
from app.models.ejemplar import Ejemplar
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.paginacion import Pagina
from app.models.policies.asignacion_prestamo import elegir_sede_origen
from app.models.prestamo import MovimientoPrestamo, Prestamo, TipoPrestamo
from app.models.remito import Remito
from app.models.sede import Sede
from app.models.socio import Socio
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef
from app.repositories.interfaces.prestamo_repository import FiltroPrestamos
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.services.remito_service import RemitoService
from app.utils.reloj import Reloj

# Reintentos si otra solicitud se lleva el último ejemplar de la sede elegida entre la consulta
# de disponibilidad y el bloqueo.
_REINTENTOS_DE_ASIGNACION = 3


@dataclass(frozen=True)
class PropuestaPrestamo:
    """Lo que el sistema haría con una solicitud por libro, sin apartar nada todavía."""

    tipo: TipoPrestamo
    libro_id: int
    libro_titulo: str
    sede_origen: Sede
    sede_destino: Sede
    plazo_dias: int
    retiro_hasta: date | None  # solo en el local: el interbibliotecario empieza al llegar


@dataclass(frozen=True)
class DetallePrestamo:
    prestamo: Prestamo
    historial: list[MovimientoPrestamo]
    remitos: list[Remito]
    devolucion: Devolucion | None = None
    multa: Multa | None = None


class PrestamoService:
    """Préstamos locales e interbibliotecarios (proceso obligatorio 4)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- registrar ------------------------------------------------------------------------

    def registrar(
        self,
        actor: Usuario,
        socio_id: int,
        ejemplar_id: int,
        sede_destino_id: int | None = None,
    ) -> Prestamo:
        """Registra la solicitud en nombre del socio y aparta el ejemplar (CU-PRE-01, 02).

        El destino es la sede del bibliotecario (donde el socio retira y devuelve); el origen es
        la sede donde está el ejemplar. Si son la misma sede, el préstamo es local y queda con
        plazo de retiro.

        Raises:
            PermisoDenegado: No es bibliotecario o indica otra sede destino.
            SocioNoEncontrado, EjemplarNoEncontrado, SedeNoEncontrada.
            Las reglas de ``PrestamoFactory.crear``.
        """
        actor.exigir(Permiso.PRESTAMO_REGISTRAR)
        destino_id = sede_destino_id or actor.sede_id
        if destino_id is None or not actor.opera_en(destino_id):
            raise PermisoDenegado(
                "El préstamo se registra en la sede donde el socio lo retira: la suya."
            )
        with self._transaccion():
            ejemplar = self._ejemplar(ejemplar_id)
            origen_id = ejemplar.sede_actual_id
            sede_origen = self._uow.sedes.obtener_para_operar(origen_id)
            sede_destino = (
                sede_origen
                if destino_id == origen_id
                else self._uow.sedes.obtener_para_operar(destino_id)
            )
            socio = self._uow.socios.obtener_para_modificar(socio_id)
            if socio is None:
                raise SocioNoEncontrado("El socio indicado no existe.")
            ahora = self._reloj.ahora()
            prestamo = self._fabrica().crear(
                numero=self._uow.prestamos.siguiente_numero(self._reloj.hoy().year),
                socio=socio,
                ejemplar=ejemplar,
                sede_origen=sede_origen,
                sede_destino=sede_destino,
                abiertos_del_socio=self._uow.prestamos.abiertos_de_socio(socio_id),
                actor=_ref(actor),
                ahora=ahora,
                hoy=self._reloj.hoy(),
            )
            self._uow.prestamos.agregar(prestamo)
            self._uow.ejemplares.guardar(ejemplar)
        return self._releer(prestamo)

    # --- autogestión del socio ------------------------------------------------------------

    def proponer(
        self,
        actor: Usuario,
        libro_id: int,
        sede_destino_id: int | None = None,
        socio_id: int | None = None,
    ) -> PropuestaPrestamo:
        """Qué préstamo se haría si el socio pide el libro ahora (CU-PRE-00, paso 6).

        No aparta nada: la asignación definitiva se hace al confirmar (``solicitar``).

        Raises:
            Las mismas reglas que ``solicitar``.
        """
        socio = self._socio_propio(actor, socio_id, bloquear=False)
        destino = self._sede_destino_del_socio(socio, sede_destino_id, bloquear=False)
        fabrica = self._fabrica()
        fabrica.validar_socio(socio, self._abiertos(socio), libro_id)
        titulo = self._titulo_del_libro(libro_id)
        origen = self._elegir_origen(libro_id, destino, bloquear=False)
        local = origen.id == destino.id
        tipo = TipoPrestamo.LOCAL if local else TipoPrestamo.INTERBIBLIOTECARIO
        return PropuestaPrestamo(
            tipo=tipo,
            libro_id=libro_id,
            libro_titulo=titulo,
            sede_origen=origen,
            sede_destino=destino,
            plazo_dias=fabrica.politica(tipo).dias,
            retiro_hasta=fabrica.limite_de_retiro(self._reloj.hoy()) if local else None,
        )

    def solicitar(
        self,
        actor: Usuario,
        libro_id: int,
        sede_destino_id: int | None = None,
        socio_id: int | None = None,
        sede_origen_esperada_id: int | None = None,
    ) -> Prestamo:
        """El socio pide un libro para sí; el sistema elige el tipo y el ejemplar (CU-PRE-00).

        * El socio es siempre el de la sesión: si ``socio_id`` indica otro, se rechaza.
        * La sede destino es la que elige el socio (por defecto, su sede de alta).
        * Si hay disponibles en la sede destino, el préstamo es local y queda con plazo de
          retiro; si no, es interbibliotecario desde la sede con más disponibles.
        * ``sede_origen_esperada_id`` es la sede de la propuesta que vio el socio: si cambió,
          se rechaza con la nueva propuesta para que la confirme (CU-PRE-00, A5).

        Raises:
            PermisoDenegado: Sin ``PRESTAMO_SOLICITAR_PROPIO`` o a nombre de otro socio.
            SocioInhabilitado, SocioEnBaja, LimitePrestamosExcedido, LibroYaPrestado: se
                controlan antes de buscar ejemplares.
            SedeEnBaja, LibroNoEncontrado.
            SinEjemplaresDisponibles: Ninguna sede activa tiene el libro (se ofrece reservar).
            DisponibilidadCambiada: La sede origen ya no es la de la propuesta.
        """
        with self._transaccion():
            socio = self._socio_propio(actor, socio_id, bloquear=True)
            destino = self._sede_destino_del_socio(socio, sede_destino_id, bloquear=True)
            fabrica = self._fabrica()
            abiertos = self._abiertos(socio)
            fabrica.validar_socio(socio, abiertos, libro_id)
            self._titulo_del_libro(libro_id)
            for _ in range(_REINTENTOS_DE_ASIGNACION):
                origen = self._elegir_origen(libro_id, destino, bloquear=True)
                assert origen.id is not None
                if sede_origen_esperada_id is not None and origen.id != sede_origen_esperada_id:
                    raise DisponibilidadCambiada(
                        "La disponibilidad cambió mientras confirmaba: revise la nueva propuesta.",
                        [
                            {
                                "campo": "sede_origen_id",
                                "problema": "cambio",
                                "sede_origen_id": origen.id,
                            }
                        ],
                    )
                ejemplar = self._uow.ejemplares.tomar_disponible(libro_id, origen.id)
                if ejemplar is not None:
                    break
            else:
                raise self._sin_disponibles(libro_id, destino)
            ahora = self._reloj.ahora()
            prestamo = fabrica.crear(
                numero=self._uow.prestamos.siguiente_numero(self._reloj.hoy().year),
                socio=socio,
                ejemplar=ejemplar,
                sede_origen=origen,
                sede_destino=destino,
                abiertos_del_socio=abiertos,
                actor=_ref(actor),
                ahora=ahora,
                hoy=self._reloj.hoy(),
            )
            self._uow.prestamos.agregar(prestamo)
            self._uow.ejemplares.guardar(ejemplar)
        return self._releer(prestamo)

    # --- entregar y renovar ---------------------------------------------------------------

    def entregar(self, actor: Usuario, prestamo_id: int) -> Prestamo:
        """Entrega al socio en la sede destino: empieza el plazo (RF-PRE-09).

        En un interbibliotecario el ejemplar tiene que haber llegado (remito recibido).

        Raises:
            PermisoDenegado, TransicionInvalida, EjemplarNoRecibido.
        """
        with self._transaccion():
            prestamo = self._de_mi_sede(actor, prestamo_id, solo_destino=True)
            ejemplar = self._ejemplar(prestamo.ejemplar_id)
            if (
                prestamo.es_interbibliotecario
                and prestamo.estado_nombre == (EstadoPrestamoEnum.EN_ENVIO)
                and not self._llego_a_destino(prestamo, ejemplar)
            ):
                raise EjemplarNoRecibido(
                    f"El ejemplar del préstamo {prestamo.numero} todavía no llegó a la sede "
                    "destino: hay que recibir el remito primero."
                )
            if prestamo.es_interbibliotecario and (
                prestamo.estado_nombre == EstadoPrestamoEnum.SOLICITADO
            ):
                raise EjemplarNoRecibido(
                    f"El préstamo {prestamo.numero} es entre sedes: primero la sede origen "
                    "genera y despacha el remito."
                )
            ahora = self._reloj.ahora()
            prestamo.entregar(
                self._reloj.hoy(), self._fabrica().politica(prestamo.tipo), _ref(actor), ahora
            )
            ejemplar.prestar(_ref(actor), ahora, f"Entregado al socio ({prestamo.numero})")
            self._uow.ejemplares.guardar(ejemplar)
            self._uow.prestamos.guardar(prestamo)
        return self._releer(prestamo)

    def renovar(self, actor: Usuario, prestamo_id: int) -> Prestamo:
        """Extiende el vencimiento si no venció, no hay reservas y no llegó al máximo."""
        with self._transaccion():
            prestamo = self._de_mi_sede(actor, prestamo_id, solo_destino=True)
            parametros = self._uow.parametros.vigentes()
            prestamo.renovar(
                self._reloj.hoy(),
                self._fabrica().politica(prestamo.tipo),
                maximo=parametros.renovaciones_maximas,
                hay_reservas=self._hay_reservas_pendientes(prestamo.libro_id),
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            self._uow.prestamos.guardar(prestamo)
        return self._releer(prestamo)

    # --- cancelar -------------------------------------------------------------------------

    def cancelar(self, actor: Usuario, prestamo_id: int, motivo: str | None = None) -> Prestamo:
        """Cancela un préstamo antes de la entrega (RF-PRE-13).

        * ``Solicitado``: el ejemplar vuelve a ``Disponible`` (CA-PRE-15).
        * ``En envío`` ya recibido en destino (el socio no lo retiró): se genera el remito de
          retorno a la sede origen (CU-PRE-02, A6).
        * ``En envío`` con el remito todavía abierto: se rechaza; hay que anular el remito o
          esperar la recepción (CU-PRE-05, A1).

        El socio (``PRESTAMO_SOLICITAR_PROPIO``) cancela solo sus préstamos y solo mientras
        están ``Solicitado``: después ya hay un envío en marcha que maneja el personal.
        """
        with self._transaccion():
            if actor.puede(Permiso.PRESTAMO_REGISTRAR):
                prestamo = self._de_mi_sede(actor, prestamo_id, solo_destino=False)
                texto = " ".join((motivo or "").split()) or "Cancelado por el personal"
            else:
                prestamo = self._propio_para_cancelar(actor, prestamo_id)
                texto = " ".join((motivo or "").split()) or "Cancelado por el socio"
            self._cancelar(prestamo, texto, _ref(actor))
        return self._releer(prestamo)

    def vencer_retiros(self, actor: Usuario | None = None) -> int:
        """Cancela los préstamos que nadie retiró dentro del plazo (RF-PRE-20).

        Un local libera el ejemplar (y lo ofrece a la cola de reservas); uno interbibliotecario
        que ya llegó vuelve a su sede con un remito de retorno. Corre una vez por día con las
        demás tareas; el administrador también puede ejecutarla.

        Returns:
            Cantidad de préstamos cancelados.
        """
        if actor is not None:
            actor.exigir(Permiso.TAREAS_EJECUTAR)
        hoy = self._reloj.hoy()
        cantidad = 0
        with self._transaccion():
            for prestamo in self._uow.prestamos.retiros_vencidos(hoy):
                if not prestamo.retiro_vencido(hoy):
                    continue
                assert prestamo.fecha_limite_retiro is not None
                limite = prestamo.fecha_limite_retiro
                self._cancelar(
                    prestamo, f"No se retiró a tiempo (vencía el {limite:%d/%m/%Y})", None
                )
                cantidad += 1
        return cantidad

    # --- vencimientos ---------------------------------------------------------------------

    def detectar_vencidos(self, actor: Usuario | None = None) -> int:
        """Marca ``Vencido`` los préstamos cuyo plazo pasó e inhabilita a sus socios (CU-PRE-04).

        Corre una vez por día (y al iniciar) desde el programador de tareas; el administrador
        también puede ejecutarla. El día de vencimiento todavía está en término (CA-PRE-14).

        Returns:
            Cantidad de préstamos que pasaron a ``Vencido``.
        """
        if actor is not None:
            actor.exigir(Permiso.TAREAS_EJECUTAR)
        hoy, ahora = self._reloj.hoy(), self._reloj.ahora()
        cantidad = 0
        with self._transaccion():
            for prestamo in self._uow.prestamos.activos_vencidos(hoy):
                if prestamo.marcar_vencido(hoy, ahora):
                    self._uow.prestamos.guardar(prestamo)
                    cantidad += 1
                    socio = self._uow.socios.obtener_para_modificar(prestamo.socio_id)
                    if socio is not None and socio.reevaluar(
                        self._uow.socios.situacion(prestamo.socio_id),
                        actor=None,
                        ahora=ahora,
                        origen=f"Préstamo {prestamo.numero} vencido",
                    ):
                        self._uow.socios.guardar(socio)
        return cantidad

    # --- lectura --------------------------------------------------------------------------

    def detalle(self, actor: Usuario, prestamo_id: int) -> DetallePrestamo:
        """Préstamo con su historial, sus remitos, la devolución y la multa (RF-PRE-15, DEV-13).

        El socio ve solo los propios; el bibliotecario, los de su sede como origen o destino.
        """
        prestamo = self._uow.prestamos.obtener(prestamo_id)
        if prestamo is None or not self._puede_ver(actor, prestamo):
            raise PrestamoNoEncontrado("El préstamo solicitado no existe.")
        return DetallePrestamo(
            prestamo,
            self._uow.prestamos.historial(prestamo_id),
            self._uow.remitos.de_prestamo(prestamo_id),
            self._uow.devoluciones.de_prestamo(prestamo_id),
            self._uow.multas.de_prestamo(prestamo_id),
        )

    def listar(
        self,
        actor: Usuario,
        estado: EstadoPrestamoEnum | None,
        tipo: TipoPrestamo | None,
        socio_id: int | None,
        numero: str | None,
        page: int,
        size: int,
    ) -> Pagina[Prestamo]:
        """El administrador ve todos; el bibliotecario, los de su sede; el socio, los suyos."""
        sede_id = None
        if actor.puede(Permiso.PRESTAMO_LEER):
            if actor.rol == Rol.BIBLIOTECARIO:
                sede_id = actor.sede_id
        elif actor.puede(Permiso.PRESTAMO_VER_PROPIOS):
            socio_id = actor.socio_id
        else:
            raise PermisoDenegado("No tiene permiso para consultar préstamos.")
        filtro = FiltroPrestamos(estado, tipo, socio_id, sede_id, numero)
        prestamos, total = self._uow.prestamos.listar(filtro, page, size)
        return Pagina(prestamos, total, page, size)

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

    def _fabrica(self) -> PrestamoFactory:
        return PrestamoFactory(self._uow.parametros.vigentes())

    def _hay_reservas_pendientes(self, libro_id: int) -> bool:
        """Si hay socios esperando el libro (CA-PRE-17)."""
        return self._uow.reservas.hay_pendientes(libro_id)

    def _ejemplar(self, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._uow.ejemplares.obtener_para_modificar(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado(
                "El ejemplar indicado no existe.",
                [{"campo": "ejemplar_id", "problema": "no_existe"}],
            )
        return ejemplar

    @staticmethod
    def _llego_a_destino(prestamo: Prestamo, ejemplar: Ejemplar) -> bool:
        return (
            ejemplar.estado_nombre == EstadoEjemplarEnum.APARTADO
            and ejemplar.sede_actual_id == prestamo.sede_destino_id
        )

    def _cancelar(self, prestamo: Prestamo, texto: str, yo: UsuarioRef | None) -> None:
        """Cancela y resuelve el ejemplar según dónde está (ver ``cancelar``)."""
        ejemplar = self._ejemplar(prestamo.ejemplar_id)
        ahora = self._reloj.ahora()
        if prestamo.estado_nombre == EstadoPrestamoEnum.EN_ENVIO:
            if not self._llego_a_destino(prestamo, ejemplar):
                raise TransicionInvalida(
                    f"El préstamo {prestamo.numero} está en camino: anule el remito (si "
                    "no salió) o espere a recibirlo para cancelarlo.",
                    [{"campo": "estado", "problema": "remito_abierto"}],
                )
            prestamo.cancelar(texto, yo, ahora)
            RemitoService(self._uow, self._reloj).generar_retorno(prestamo, ejemplar, yo)
        else:
            prestamo.cancelar(texto, yo, ahora)
            ejemplar.liberar(yo, ahora, f"Préstamo {prestamo.numero} cancelado")
            self._uow.ejemplares.guardar(ejemplar)
            self._uow.prestamos.guardar(prestamo)
            ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, yo)
        self._uow.prestamos.guardar(prestamo)

    def _propio_para_cancelar(self, actor: Usuario, prestamo_id: int) -> Prestamo:
        actor.exigir(Permiso.PRESTAMO_SOLICITAR_PROPIO)
        prestamo = self._uow.prestamos.obtener_para_modificar(prestamo_id)
        # Un préstamo ajeno responde igual que uno inexistente: no se revela que existe.
        if prestamo is None or actor.socio_id is None or prestamo.socio_id != actor.socio_id:
            raise PrestamoNoEncontrado("El préstamo solicitado no existe.")
        if not prestamo.cancelable_por_el_socio:
            raise TransicionInvalida(
                f"El préstamo {prestamo.numero} ya está en marcha: para cancelarlo, consulte en "
                "la biblioteca.",
                [{"campo": "estado", "problema": prestamo.estado_nombre.value}],
            )
        return prestamo

    def _socio_propio(self, actor: Usuario, socio_id: int | None, *, bloquear: bool) -> Socio:
        """El socio de la sesión. Nunca otro: ``socio_id`` distinto se rechaza (CA-ACC-15)."""
        actor.exigir(Permiso.PRESTAMO_SOLICITAR_PROPIO)
        if actor.socio_id is None:
            raise PermisoDenegado("Su usuario no tiene una ficha de socio.")
        if socio_id is not None and socio_id != actor.socio_id:
            raise PermisoDenegado(
                "Solo puede solicitar préstamos para usted.",
                [{"campo": "socio_id", "problema": "ajeno"}],
            )
        socio = (
            self._uow.socios.obtener_para_modificar(actor.socio_id)
            if bloquear
            else self._uow.socios.obtener(actor.socio_id)
        )
        if socio is None:
            raise SocioNoEncontrado("El socio indicado no existe.")
        return socio

    def _sede_destino_del_socio(
        self, socio: Socio, sede_destino_id: int | None, *, bloquear: bool
    ) -> Sede:
        """La sede que eligió el socio o, por defecto, su sede de alta. Tiene que estar activa."""
        return self._sede_activa(sede_destino_id or socio.sede_alta_id, bloquear=bloquear)

    def _sede_activa(self, sede_id: int, *, bloquear: bool) -> Sede:
        """Al confirmar se bloquea (``FOR SHARE``); en la propuesta solo se consulta."""
        if bloquear:
            return self._uow.sedes.obtener_para_operar(sede_id)
        sede = self._uow.sedes.obtener(sede_id)
        if sede is None:
            raise SedeNoEncontrada("La sede indicada no existe.")
        sede.validar_operativa()
        return sede

    def _abiertos(self, socio: Socio) -> list[Prestamo]:
        assert socio.id is not None
        return self._uow.prestamos.abiertos_de_socio(socio.id)

    def _titulo_del_libro(self, libro_id: int) -> str:
        libro = self._uow.libros.obtener(libro_id)
        if libro is None:
            raise LibroNoEncontrado(
                "El libro indicado no existe.", [{"campo": "libro_id", "problema": "no_existe"}]
            )
        return libro.titulo

    def _elegir_origen(self, libro_id: int, destino: Sede, *, bloquear: bool) -> Sede:
        assert destino.id is not None
        disponibles = self._uow.ejemplares.disponibles_por_sede(libro_id)
        origen_id = elegir_sede_origen(disponibles, destino.id)
        if origen_id is None:
            raise self._sin_disponibles(libro_id, destino)
        if origen_id == destino.id:
            return destino
        return self._sede_activa(origen_id, bloquear=bloquear)

    @staticmethod
    def _sin_disponibles(libro_id: int, destino: Sede) -> SinEjemplaresDisponibles:
        return SinEjemplaresDisponibles(
            "No hay ejemplares disponibles de este libro en ninguna sede: puede reservarlo para "
            "retirarlo cuando se libere.",
            [{"campo": "libro_id", "problema": "sin_disponibles", "sede_destino_id": destino.id}],
        )

    def _de_mi_sede(self, actor: Usuario, prestamo_id: int, *, solo_destino: bool) -> Prestamo:
        actor.exigir(Permiso.PRESTAMO_REGISTRAR)
        prestamo = self._uow.prestamos.obtener_para_modificar(prestamo_id)
        if prestamo is None:
            raise PrestamoNoEncontrado("El préstamo solicitado no existe.")
        permitido = (
            actor.opera_en(prestamo.sede_destino_id)
            if solo_destino
            else prestamo.interviene(actor.sede_id)
        )
        if not permitido:
            raise PermisoDenegado("El préstamo no es de su sede.")
        return prestamo

    @staticmethod
    def _puede_ver(actor: Usuario, prestamo: Prestamo) -> bool:
        if actor.puede(Permiso.PRESTAMO_LEER):
            return actor.rol == Rol.ADMIN or prestamo.interviene(actor.sede_id)
        return actor.puede(Permiso.PRESTAMO_VER_PROPIOS) and actor.socio_id == prestamo.socio_id

    def _releer(self, prestamo: Prestamo) -> Prestamo:
        assert prestamo.id is not None
        return self._uow.prestamos.obtener(prestamo.id) or prestamo


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
