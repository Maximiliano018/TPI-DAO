"""Entidad de dominio ``Reserva``: un lugar en la cola de espera de un libro.

La reserva es sobre el **libro** (cualquier ejemplar). La cola se ordena por fecha y hora (FIFO)
y, al liberarse un ejemplar, se le asigna a la primera reserva elegible (ver
``services/cola_reservas.py``).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models.states.reserva import (
    ACTIVAS,
    EstadoReserva,
    EstadoReservaEnum,
    Pendiente,
)


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
    # Datos para mostrar (los completa el repositorio).
    socio_nombre: str | None = None
    numero_socio: str | None = None
    libro_titulo: str | None = None
    sede_retiro_nombre: str | None = None
    codigo_ejemplar: str | None = None
    posicion_en_cola: int | None = None

    @property
    def estado_nombre(self) -> EstadoReservaEnum:
        return self.estado.nombre

    @property
    def esta_activa(self) -> bool:
        return self.estado_nombre in ACTIVAS

    def asignar(self, ejemplar_id: int, hoy: date, vigencia_dias: int) -> None:
        """El ejemplar ya está en la sede de retiro: el socio tiene ``vigencia_dias`` para
        retirarlo (RF-RES-07, 09)."""
        self.estado = self.estado.asignar()
        self.ejemplar_id = ejemplar_id
        self.vencimiento_retiro = hoy + timedelta(days=vigencia_dias)

    def convertir_en_prestamo(self, ejemplar_id: int, prestamo_id: int, ahora: datetime) -> None:
        """El ejemplar está en otra sede: se cumple con un préstamo interbibliotecario."""
        self.estado = self.estado.convertir_en_prestamo()
        self.ejemplar_id = ejemplar_id
        self.prestamo_id = prestamo_id
        self.fecha_cierre = ahora

    def cumplir(self, prestamo_id: int, ahora: datetime) -> None:
        """Retiro: la reserva se transforma en préstamo (RF-RES-11)."""
        self.estado = self.estado.cumplir()
        self.prestamo_id = prestamo_id
        self.fecha_cierre = ahora

    def vencer(self, hoy: date, ahora: datetime) -> bool:
        """Pasa a ``Vencida`` si pasó la vigencia de retiro. El día de vencimiento todavía vale."""
        if self.estado_nombre != EstadoReservaEnum.DISPONIBLE_PARA_RETIRO:
            return False
        assert self.vencimiento_retiro is not None
        if hoy <= self.vencimiento_retiro:
            return False
        self.estado = self.estado.vencer()
        self.fecha_cierre = ahora
        return True

    def cancelar(self, ahora: datetime) -> None:
        self.estado = self.estado.cancelar()
        self.fecha_cierre = ahora
