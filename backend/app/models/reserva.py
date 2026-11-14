"""Entidad de dominio ``Reserva``: un lugar en la cola de espera de un libro.

La reserva es sobre el **libro** (cualquier ejemplar). La cola se ordena por fecha y hora (FIFO)
y, al liberarse un ejemplar, se le asigna a la primera reserva elegible (ver
``services/cola_reservas.py``).

Cada cambio de estado queda en ``movimientos_pendientes`` (fecha, autor y observación) y el
repositorio lo guarda en el historial de solo inserción ``movimiento_reserva`` (RF-RES-16). Las
acciones automáticas de la cola tienen autor ``None``: las hizo el sistema (RF-RES-14).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models.states.reserva import (
    ACTIVAS,
    EstadoReserva,
    EstadoReservaEnum,
    Pendiente,
)
from app.models.usuario import UsuarioRef


@dataclass(frozen=True)
class MovimientoReserva:
    estado_anterior: EstadoReservaEnum | None
    estado_nuevo: EstadoReservaEnum
    fecha_hora: datetime
    usuario: UsuarioRef | None
    observacion: str | None = None


@dataclass
class Reserva:
    id: int | None
    numero: str
    socio_id: int
    libro_id: int
    sede_retiro_id: int
    fecha_reserva: datetime
    estado: EstadoReserva = field(default_factory=Pendiente)
    ejemplar_id: int | None = None
    vencimiento_retiro: date | None = None
    prestamo_id: int | None = None
    fecha_cierre: datetime | None = None
    # Quién la registró: el socio o el bibliotecario en su nombre.
    registrada_por: UsuarioRef | None = None
    movimientos_pendientes: list[MovimientoReserva] = field(default_factory=list)
    # Datos para mostrar (los completa el repositorio).
    socio_nombre: str | None = None
    numero_socio: str | None = None
    libro_titulo: str | None = None
    sede_retiro_nombre: str | None = None
    codigo_ejemplar: str | None = None
    posicion_en_cola: int | None = None

    @classmethod
    def registrar(
        cls,
        *,
        numero: str,
        socio_id: int,
        libro_id: int,
        sede_retiro_id: int,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Reserva":
        """Nueva reserva ``Pendiente`` al final de la cola (CU-RES-01)."""
        reserva = cls(
            id=None,
            numero=numero,
            socio_id=socio_id,
            libro_id=libro_id,
            sede_retiro_id=sede_retiro_id,
            fecha_reserva=ahora,
            registrada_por=actor,
        )
        reserva.movimientos_pendientes.append(
            MovimientoReserva(None, reserva.estado_nombre, ahora, actor, "Reserva registrada")
        )
        return reserva

    @property
    def estado_nombre(self) -> EstadoReservaEnum:
        return self.estado.nombre

    @property
    def esta_activa(self) -> bool:
        return self.estado_nombre in ACTIVAS

    def asignar(
        self, ejemplar_id: int, hoy: date, vigencia_dias: int, ahora: datetime, codigo: str
    ) -> None:
        """El ejemplar ya está en la sede de retiro: el socio tiene ``vigencia_dias`` para
        retirarlo (RF-RES-07, 09). La asigna el sistema."""
        nuevo = self.estado.asignar()
        self.ejemplar_id = ejemplar_id
        self.vencimiento_retiro = hoy + timedelta(days=vigencia_dias)
        self._transicion(
            nuevo,
            None,
            ahora,
            f"Ejemplar {codigo} asignado: retirar hasta el "
            f"{self.vencimiento_retiro.strftime('%d/%m/%Y')}",
        )

    def convertir_en_prestamo(
        self, ejemplar_id: int, prestamo_id: int, ahora: datetime, numero_prestamo: str
    ) -> None:
        """El ejemplar está en otra sede: se cumple con un préstamo interbibliotecario."""
        nuevo = self.estado.convertir_en_prestamo()
        self.ejemplar_id = ejemplar_id
        self.prestamo_id = prestamo_id
        self.fecha_cierre = ahora
        self._transicion(
            nuevo, None, ahora, f"Se cumple con el préstamo entre sedes {numero_prestamo}"
        )

    def cumplir(
        self, prestamo_id: int, actor: UsuarioRef, ahora: datetime, numero_prestamo: str
    ) -> None:
        """Retiro: la reserva se transforma en préstamo (RF-RES-11)."""
        nuevo = self.estado.cumplir()
        self.prestamo_id = prestamo_id
        self.fecha_cierre = ahora
        self._transicion(nuevo, actor, ahora, f"Retirada: préstamo {numero_prestamo}")

    def vencer(self, hoy: date, ahora: datetime) -> bool:
        """Pasa a ``Vencida`` si pasó la vigencia de retiro. El día de vencimiento todavía vale."""
        if self.estado_nombre != EstadoReservaEnum.DISPONIBLE_PARA_RETIRO:
            return False
        assert self.vencimiento_retiro is not None
        if hoy <= self.vencimiento_retiro:
            return False
        nuevo = self.estado.vencer()
        self.fecha_cierre = ahora
        self._transicion(nuevo, None, ahora, "Venció el plazo de retiro")
        return True

    def cancelar(self, ahora: datetime, actor: UsuarioRef | None, motivo: str | None) -> None:
        """Cancela la reserva. ``actor`` es ``None`` si la cancela el sistema."""
        nuevo = self.estado.cancelar()
        self.fecha_cierre = ahora
        self._transicion(nuevo, actor, ahora, motivo or "Cancelada")

    def _transicion(
        self,
        nuevo: EstadoReserva,
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
    ) -> None:
        anterior = self.estado_nombre
        self.estado = nuevo
        self.movimientos_pendientes.append(
            MovimientoReserva(anterior, nuevo.nombre, ahora, actor, observacion)
        )
