"""Casos de uso de reservas: reservar, cancelar, retirar, consultar y vencer."""

from collections.abc import Iterator
from contextlib import contextmanager

from app.exceptions import (
    EjemplarNoEncontrado,
    ErrorDeValidacion,
    HayEjemplaresDisponibles,
    LibroNoEncontrado,
    LibroSinEjemplares,
    LimiteReservasExcedido,
    PermisoDenegado,
    ReservaDuplicada,
    ReservaNoEncontrada,
    SocioNoEncontrado,
)
from app.models.ejemplar import Ejemplar
from app.models.factories.prestamo_factory import PrestamoFactory
from app.models.paginacion import Pagina
from app.models.prestamo import Prestamo
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef
from app.repositories.interfaces.prestamo_repository import FiltroReservas
from app.repositories.unit_of_work import UnitOfWork
from app.services.cola_reservas import ColaDeReservas
from app.utils.reloj import Reloj


class ReservaService:
    """Reservas sobre libros sin ejemplares disponibles (proceso obligatorio 7)."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    # --- reservar y cancelar --------------------------------------------------------------

    def reservar(
        self, actor: Usuario, libro_id: int, sede_retiro_id: int, socio_id: int | None = None
    ) -> Reserva:
        """El socio reserva para sí; el bibliotecario, en nombre de un socio (CU-RES-01).

        Raises:
            PermisoDenegado, SocioNoEncontrado, LibroNoEncontrado.
            SocioInhabilitado, SocioEnBaja (CA-RES-02); SedeEnBaja (CA-RES-03).
            LibroSinEjemplares: No hay ejemplares activos en la red.
            HayEjemplaresDisponibles: Hay disponibles en la sede de retiro (CA-RES-01).
            ReservaDuplicada (CA-RES-04); LimiteReservasExcedido (CA-RES-05).
        """
        socio_id = self._socio_de_la_reserva(actor, socio_id)
        with self._transaccion():
            socio = self._uow.socios.obtener_para_modificar(socio_id)
            if socio is None:
                raise SocioNoEncontrado("El socio indicado no existe.")
            socio.validar_puede_operar()
            sede = self._uow.sedes.obtener_para_operar(sede_retiro_id)
            libro = self._uow.libros.obtener(libro_id)
            if libro is None:
                raise LibroNoEncontrado("El libro indicado no existe.")
            if self._uow.ejemplares.activos_de_libro(libro_id) == 0:
                raise LibroSinEjemplares(
                    f"«{libro.titulo}» no tiene ejemplares en la red: no se puede reservar."
                )
            if self._uow.ejemplares.disponibles_en_sede(libro_id, sede_retiro_id):
                raise HayEjemplaresDisponibles(
                    f"Hay ejemplares disponibles de «{libro.titulo}» en {sede.nombre}: "
                    "corresponde un préstamo, no una reserva.",
                    [{"campo": "libro_id", "problema": "hay_disponibles"}],
                )
            activas = self._uow.reservas.activas_de_socio(socio_id)
            if any(r.libro_id == libro_id for r in activas):
                raise ReservaDuplicada(
                    "El socio ya tiene una reserva activa de este libro.",
                    [{"campo": "libro_id", "problema": "reserva_duplicada"}],
                )
            maximo = self._uow.parametros.vigentes().reservas_maximas_por_socio
            if len(activas) >= maximo:
                raise LimiteReservasExcedido(
                    f"El socio ya tiene {maximo} reservas activas.",
                    [{"campo": "socio_id", "problema": "limite", "maximo": maximo}],
                )
            reserva = Reserva(
                id=None,
                numero=self._uow.reservas.siguiente_numero(self._reloj.hoy().year),
                socio_id=socio_id,
                libro_id=libro_id,
                sede_retiro_id=sede_retiro_id,
                fecha_reserva=self._reloj.ahora(),
            )
            self._uow.reservas.agregar(reserva)
        return self._releer(reserva)

    def cancelar(self, actor: Usuario, reserva_id: int) -> Reserva:
        """Cancela una reserva activa; si tenía ejemplar, se ofrece al siguiente (CU-RES-05).

        Raises:
            ReservaNoEncontrada: No existe o es de otro socio.
            TransicionInvalida: Ya está cumplida, cancelada o vencida (CA-RES-11).
        """
        with self._transaccion():
            reserva = self._uow.reservas.obtener_para_modificar(reserva_id)
            if reserva is None or not self._puede_ver(actor, reserva):
                raise ReservaNoEncontrada("La reserva solicitada no existe.")
            ejemplar_id = (
                reserva.ejemplar_id
                if reserva.estado_nombre == EstadoReservaEnum.DISPONIBLE_PARA_RETIRO
                else None
            )
            reserva.cancelar(self._reloj.ahora())
            self._uow.reservas.guardar(reserva)
            if ejemplar_id is not None:
                self._liberar(ejemplar_id, _ref(actor), f"Reserva {reserva.numero} cancelada")
        return self._releer(reserva)

    def cancelar_del_socio(self, socio_id: int, actor: UsuarioRef) -> int:
        """Cancela las reservas activas de un socio que se da de baja (CU-SOC-04, A2).

        No abre transacción: corre dentro de la baja del socio.
        """
        canceladas = 0
        for reserva in self._uow.reservas.activas_de_socio(socio_id):
            ejemplar_id = (
                reserva.ejemplar_id
                if reserva.estado_nombre == EstadoReservaEnum.DISPONIBLE_PARA_RETIRO
                else None
            )
            reserva.cancelar(self._reloj.ahora())
            self._uow.reservas.guardar(reserva)
            if ejemplar_id is not None:
                self._liberar(ejemplar_id, actor, f"Reserva {reserva.numero} cancelada (baja)")
            canceladas += 1
        return canceladas

    # --- retiro y vencimiento -------------------------------------------------------------

    def retirar(self, actor: Usuario, reserva_id: int) -> Prestamo:
        """El socio retira el ejemplar reservado: la reserva se cumple y nace el préstamo activo
        (CU-RES-03, CA-RES-12).

        Raises:
            PermisoDenegado: No es bibliotecario de la sede de retiro.
            TransicionInvalida: La reserva no está disponible para retiro.
            SocioInhabilitado: El socio quedó inhabilitado (CU-RES-03, A1).
        """
        actor.exigir(Permiso.RESERVA_REGISTRAR)
        with self._transaccion():
            reserva = self._uow.reservas.obtener_para_modificar(reserva_id)
            if reserva is None:
                raise ReservaNoEncontrada("La reserva solicitada no existe.")
            if not actor.opera_en(reserva.sede_retiro_id):
                raise PermisoDenegado("La reserva se retira en otra sede.")
            reserva.estado.cumplir()  # valida el estado antes de crear el préstamo
            assert reserva.ejemplar_id is not None
            ejemplar = self._ejemplar(reserva.ejemplar_id)
            socio = self._uow.socios.obtener_para_modificar(reserva.socio_id)
            assert socio is not None
            sede = self._uow.sedes.obtener_para_operar(reserva.sede_retiro_id)
            ahora, hoy = self._reloj.ahora(), self._reloj.hoy()
            fabrica = PrestamoFactory(self._uow.parametros.vigentes())
            prestamo = fabrica.crear(
                numero=self._uow.prestamos.siguiente_numero(hoy.year),
                socio=socio,
                ejemplar=ejemplar,
                sede_origen=sede,
                sede_destino=sede,
                abiertos_del_socio=self._uow.prestamos.abiertos_de_socio(reserva.socio_id),
                actor=_ref(actor),
                ahora=ahora,
                reservado=True,
            )
            prestamo.entregar(hoy, fabrica.politica(prestamo.tipo), _ref(actor), ahora)
            ejemplar.prestar(_ref(actor), ahora, f"Retiro de la reserva {reserva.numero}")
            self._uow.prestamos.agregar(prestamo)
            assert prestamo.id is not None
            reserva.cumplir(prestamo.id, ahora)
            self._uow.reservas.guardar(reserva)
            self._uow.ejemplares.guardar(ejemplar)
        return self._uow.prestamos.obtener(prestamo.id) or prestamo

    def vencer_reservas(self, actor: Usuario | None = None) -> int:
        """Vence las reservas no retiradas a tiempo y reasigna sus ejemplares (CU-RES-04).

        Corre una vez por día con las demás tareas; el administrador también puede ejecutarla.
        """
        if actor is not None:
            actor.exigir(Permiso.TAREAS_EJECUTAR)
        hoy, ahora = self._reloj.hoy(), self._reloj.ahora()
        cantidad = 0
        with self._transaccion():
            for reserva in self._uow.reservas.vencidas(hoy):
                if reserva.vencer(hoy, ahora):
                    self._uow.reservas.guardar(reserva)
                    cantidad += 1
                    assert reserva.ejemplar_id is not None
                    self._liberar(
                        reserva.ejemplar_id, None, f"Reserva {reserva.numero} vencida sin retirar"
                    )
        return cantidad

    # --- lectura --------------------------------------------------------------------------

    def detalle(self, actor: Usuario, reserva_id: int) -> Reserva:
        reserva = self._uow.reservas.obtener(reserva_id)
        if reserva is None or not self._puede_ver(actor, reserva):
            raise ReservaNoEncontrada("La reserva solicitada no existe.")
        return reserva

    def listar(
        self,
        actor: Usuario,
        socio_id: int | None,
        libro_id: int | None,
        estado: EstadoReservaEnum | None,
        page: int,
        size: int,
    ) -> Pagina[Reserva]:
        """El socio ve solo las propias (CA-RES-13); el personal, todas (la cola de un libro)."""
        if not actor.puede(Permiso.RESERVA_LEER):
            actor.exigir(Permiso.RESERVA_PROPIA)
            socio_id = actor.socio_id
        filtro = FiltroReservas(socio_id=socio_id, libro_id=libro_id, estado=estado)
        reservas, total = self._uow.reservas.listar(filtro, page, size)
        return Pagina(reservas, total, page, size)

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

    @staticmethod
    def _socio_de_la_reserva(actor: Usuario, socio_id: int | None) -> int:
        if actor.rol == Rol.SOCIO:
            actor.exigir(Permiso.RESERVA_PROPIA)
            assert actor.socio_id is not None
            return actor.socio_id
        actor.exigir(Permiso.RESERVA_REGISTRAR)
        if socio_id is None:
            raise ErrorDeValidacion(
                "Indique el socio de la reserva.",
                [{"campo": "socio_id", "problema": "obligatorio"}],
            )
        return socio_id

    @staticmethod
    def _puede_ver(actor: Usuario, reserva: Reserva) -> bool:
        if actor.puede(Permiso.RESERVA_LEER):
            return True
        return actor.puede(Permiso.RESERVA_PROPIA) and actor.socio_id == reserva.socio_id

    def _ejemplar(self, ejemplar_id: int) -> Ejemplar:
        ejemplar = self._uow.ejemplares.obtener_para_modificar(ejemplar_id)
        if ejemplar is None:
            raise EjemplarNoEncontrado("El ejemplar no existe.")
        return ejemplar

    def _liberar(self, ejemplar_id: int, actor: UsuarioRef | None, motivo: str) -> None:
        ejemplar = self._ejemplar(ejemplar_id)
        ejemplar.liberar(actor, self._reloj.ahora(), motivo)
        self._uow.ejemplares.guardar(ejemplar)
        ColaDeReservas(self._uow, self._reloj).ofrecer(ejemplar, actor)

    def _releer(self, reserva: Reserva) -> Reserva:
        assert reserva.id is not None
        return self._uow.reservas.obtener(reserva.id) or reserva


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
