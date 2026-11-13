"""Casos de uso de préstamos: registrar, entregar, renovar, cancelar y detectar vencidos."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from app.exceptions import (
    EjemplarNoEncontrado,
    EjemplarNoRecibido,
    PermisoDenegado,
    PrestamoNoEncontrado,
    SocioNoEncontrado,
    TransicionInvalida,
)
from app.models.ejemplar import Ejemplar
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.paginacion import Pagina
from app.models.prestamo import MovimientoPrestamo, Prestamo, TipoPrestamo
from app.models.remito import Remito
from app.models.states.ejemplar import EstadoEjemplarEnum
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef
from app.repositories.interfaces.prestamo_repository import FiltroPrestamos
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.services.remito_service import RemitoService
from app.utils.reloj import Reloj


@dataclass(frozen=True)
class DetallePrestamo:
    prestamo: Prestamo
    historial: list[MovimientoPrestamo]
    remitos: list[Remito]


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
        sede_origen_id: int | None = None,
    ) -> Prestamo:
        """Registra la solicitud en nombre del socio y aparta el ejemplar (CU-PRE-01, 02).

        El destino es la sede del bibliotecario (donde el socio retira y devuelve); el origen es
        la sede del ejemplar. Si son la misma sede, el préstamo es local.

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
            origen_id = sede_origen_id or ejemplar.sede_actual_id
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
        """
        texto = " ".join((motivo or "").split()) or "Cancelado por el personal"
        with self._transaccion():
            prestamo = self._de_mi_sede(actor, prestamo_id, solo_destino=False)
            ejemplar = self._ejemplar(prestamo.ejemplar_id)
            yo = _ref(actor)
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
        return self._releer(prestamo)

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
                        self._uow.socios.situacion(prestamo.socio_id), actor=None, ahora=ahora
                    ):
                        self._uow.socios.guardar(socio)
        return cantidad

    # --- lectura --------------------------------------------------------------------------

    def detalle(self, actor: Usuario, prestamo_id: int) -> DetallePrestamo:
        """Préstamo con su historial y sus remitos (RF-PRE-15).

        El socio ve solo los propios; el bibliotecario, los de su sede como origen o destino.
        """
        prestamo = self._uow.prestamos.obtener(prestamo_id)
        if prestamo is None or not self._puede_ver(actor, prestamo):
            raise PrestamoNoEncontrado("El préstamo solicitado no existe.")
        return DetallePrestamo(
            prestamo,
            self._uow.prestamos.historial(prestamo_id),
            self._uow.remitos.de_prestamo(prestamo_id),
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
