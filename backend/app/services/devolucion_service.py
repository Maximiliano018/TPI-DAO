"""Casos de uso de devoluciones y multas: registrar la devolución, saldar y consultar multas."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from app.exceptions import (
    EjemplarNoEncontrado,
    MultaNoEncontrada,
    PermisoDenegado,
    PrestamoNoEncontrado,
)
from app.models.devolucion import Devolucion, EstadoMulta, EstadoRecibido, Multa
from app.models.ejemplar import Ejemplar, EstadoFisico
from app.models.incidencia import Incidencia, OrigenIncidencia, TipoIncidencia
from app.models.paginacion import Pagina
from app.models.policies.multa import MultaFijaPorDia
from app.models.prestamo import Prestamo
from app.models.remito import Remito
from app.models.reserva import Reserva
from app.models.socio import Socio
from app.models.usuario import Permiso, Usuario, UsuarioRef
from app.models.valores import error_de_campo
from app.repositories.interfaces.devolucion_repository import FiltroMultas
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.services.remito_service import RemitoService
from app.utils.reloj import Reloj


@dataclass(frozen=True)
class ResultadoDevolucion:
    """Todo lo que cambió con la devolución, para mostrarlo de una vez."""

    prestamo: Prestamo
    devolucion: Devolucion
    multa: Multa | None
    remito_retorno: Remito | None
    reserva_asignada: Reserva | None
    socio: Socio | None


class DevolucionService:
    """Devoluciones y multas (proceso obligatorio 8)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- registrar ------------------------------------------------------------------------

    def registrar(
        self,
        actor: Usuario,
        prestamo_id: int,
        estado_recibido: EstadoRecibido,
        observaciones: str | None = None,
        fecha_hora: datetime | None = None,
    ) -> ResultadoDevolucion:
        """Registra la devolución en la sede destino del préstamo (CU-DEV-01 a 04).

        En una sola transacción: cierra el préstamo, genera la multa si hay atraso, reevalúa al
        socio y resuelve el ejemplar según cómo llegó:

        * ``Bueno`` o ``Regular`` en un préstamo local: queda ``Disponible`` y se ofrece a la
          cola de reservas del libro (CA-DEV-11, CA-DEV-15).
        * ``Bueno``, ``Regular`` o ``Dañado`` en uno interbibliotecario: queda ``Apartado`` y se
          genera el remito de retorno a su sede propietaria (CA-DEV-12). Si llegó dañado, la
          revisión la hace la sede propietaria al recibirlo.
        * ``Dañado`` en uno local: pasa a ``En revisión`` con una incidencia (CA-DEV-13).
        * ``Extraviado``: pasa a ``Baja`` con una incidencia (CA-DEV-14).

        Raises:
            PermisoDenegado: No es la sede destino del préstamo (CA-DEV-03, CA-ACC-02).
            TransicionInvalida: El préstamo no está activo ni vencido (CA-DEV-02).
            ErrorDeValidacion: Fecha futura o anterior a la entrega (CA-DEV-04), u observaciones
                faltantes ante un daño o extravío.
        """
        actor.exigir(Permiso.DEVOLUCION_REGISTRAR)
        with self._transaccion():
            prestamo = self._uow.prestamos.obtener_para_modificar(prestamo_id)
            if prestamo is None:
                raise PrestamoNoEncontrado("El préstamo solicitado no existe.")
            if not actor.opera_en(prestamo.sede_destino_id):
                sede = prestamo.sede_destino_nombre or "la sede destino"
                raise PermisoDenegado(
                    f"La devolución del préstamo {prestamo.numero} se registra en {sede}.",
                    [{"campo": "sede_destino_id", "valor": prestamo.sede_destino_id}],
                )
            ahora, hoy = self._reloj.ahora(), self._reloj.hoy()
            momento = self._momento(fecha_hora, ahora)
            zona = self._reloj.ahora_local().tzinfo
            parametros = self._uow.parametros.vigentes()
            yo = _ref(actor)
            devolucion, multa = Devolucion.registrar(
                prestamo=prestamo,
                fecha_hora=momento,
                fecha=momento.astimezone(zona).date(),
                hoy=hoy,
                estado_recibido=estado_recibido,
                observaciones=observaciones,
                politica=MultaFijaPorDia(parametros.multa_por_dia),
                actor=yo,
            )
            prestamo.devolver(momento, yo, ahora)
            self._uow.prestamos.guardar(prestamo)
            self._uow.devoluciones.agregar(devolucion)
            if multa is not None:
                self._uow.multas.agregar(multa)
            socio = self._reevaluar_socio(
                prestamo.socio_id, yo, ahora, f"Devolución del préstamo {prestamo.numero}"
            )
            ejemplar = self._ejemplar(prestamo.ejemplar_id)
            remito, reserva = self._resolver_ejemplar(prestamo, ejemplar, devolucion, yo, ahora)
        return ResultadoDevolucion(
            prestamo=self._uow.prestamos.obtener(prestamo_id) or prestamo,
            devolucion=devolucion,
            multa=self._uow.multas.de_prestamo(prestamo_id),
            remito_retorno=remito,
            reserva_asignada=reserva,
            socio=socio,
        )

    # --- multas ---------------------------------------------------------------------------

    def saldar_multa(self, actor: Usuario, multa_id: int) -> Multa:
        """Marca la multa como saldada y reevalúa al socio (CU-DEV-05, CA-DEV-10)."""
        actor.exigir(Permiso.MULTA_SALDAR)
        with self._transaccion():
            multa = self._uow.multas.obtener_para_modificar(multa_id)
            if multa is None:
                raise MultaNoEncontrada("La multa solicitada no existe.")
            ahora = self._reloj.ahora()
            yo = _ref(actor)
            multa.saldar(yo, ahora)
            self._uow.multas.guardar(multa)
            self._reevaluar_socio(
                multa.socio_id,
                yo,
                ahora,
                f"Multa del préstamo {multa.numero_prestamo or multa.prestamo_id} saldada",
            )
        return self._uow.multas.obtener(multa_id) or multa

    def listar_multas(
        self,
        actor: Usuario,
        socio_id: int | None,
        estado: EstadoMulta | None,
        page: int,
        size: int,
    ) -> Pagina[Multa]:
        """El personal ve las de la red; el socio, solo las propias (CA-DEV-16)."""
        if actor.puede(Permiso.MULTA_LEER):
            pass
        elif actor.puede(Permiso.MULTA_VER_PROPIAS):
            socio_id = actor.socio_id
        else:
            raise PermisoDenegado("No tiene permiso para consultar multas.")
        multas, total = self._uow.multas.listar(FiltroMultas(socio_id, estado), page, size)
        return Pagina(multas, total, page, size)

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

    def _momento(self, fecha_hora: datetime | None, ahora: datetime) -> datetime:
        """Fecha y hora de la devolución; sin zona se toma la de negocio."""
        if fecha_hora is None:
            return ahora
        if fecha_hora.tzinfo is None:
            fecha_hora = fecha_hora.replace(tzinfo=self._reloj.ahora_local().tzinfo)
        if fecha_hora > ahora:
            raise error_de_campo("fecha_hora", "La fecha de devolución no puede ser futura.")
        return fecha_hora

    def _reevaluar_socio(
        self, socio_id: int, actor: UsuarioRef, ahora: datetime, origen: str
    ) -> Socio | None:
        socio = self._uow.socios.obtener_para_modificar(socio_id)
        if socio is None:
            return None
        situacion = self._uow.socios.situacion(socio_id)
        if socio.reevaluar(situacion, actor=actor, ahora=ahora, origen=origen):
            self._uow.socios.guardar(socio)
        return socio

    def _ejemplar(self, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._uow.ejemplares.obtener_para_modificar(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado("El ejemplar del préstamo no existe.")
        return ejemplar

    def _resolver_ejemplar(
        self,
        prestamo: Prestamo,
        ejemplar: Ejemplar,
        devolucion: Devolucion,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> tuple[Remito | None, Reserva | None]:
        estado = devolucion.estado_recibido
        texto = f"Devuelto ({prestamo.numero})"
        if estado == EstadoRecibido.EXTRAVIADO:
            ejemplar.registrar_baja(f"Extraviado por el socio ({prestamo.numero})", actor, ahora)
            self._incidencia(TipoIncidencia.EXTRAVIO, prestamo, devolucion, actor, ahora)
            self._uow.ejemplares.guardar(ejemplar)
            return None, None
        if estado == EstadoRecibido.DANADO:
            self._incidencia(TipoIncidencia.DANIO, prestamo, devolucion, actor, ahora)
            if not prestamo.es_interbibliotecario:
                ejemplar.enviar_a_revision(actor, ahora, f"{texto}: dañado")
                self._uow.ejemplares.guardar(ejemplar)
                return None, None
        ejemplar.estado_fisico = EstadoFisico(estado.value)
        if prestamo.es_interbibliotecario:
            ejemplar.apartar(actor, ahora, f"{texto}: espera el retorno a su sede")
            self._uow.ejemplares.guardar(ejemplar)
            remito = RemitoService(self._uow, self._reloj).generar_retorno(
                prestamo, ejemplar, actor
            )
            return remito, None
        ejemplar.liberar(actor, ahora, texto)
        self._uow.ejemplares.guardar(ejemplar)
        return None, ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, actor)

    def _incidencia(
        self,
        tipo: TipoIncidencia,
        prestamo: Prestamo,
        devolucion: Devolucion,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> None:
        """Incidencia asociada al socio, sin penalización económica (RF-DEV-12)."""
        self._uow.incidencias.agregar(
            Incidencia(
                tipo=tipo,
                origen=OrigenIncidencia.DEVOLUCION,
                ejemplar_id=prestamo.ejemplar_id,
                descripcion=devolucion.observaciones or "Sin observación",
                fecha=ahora,
                usuario=actor,
                socio_id=prestamo.socio_id,
                prestamo_id=prestamo.id,
            )
        )


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
