"""Puertos de préstamos, remitos, incidencias y parámetros de negocio."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.models.incidencia import Incidencia
from app.models.parametros import Parametros
from app.models.prestamo import MovimientoPrestamo, Prestamo, TipoPrestamo
from app.models.remito import MotivoRemito, MovimientoRemito, Remito
from app.models.reserva import Reserva
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.states.remito import EstadoRemitoEnum
from app.models.states.reserva import EstadoReservaEnum


@dataclass(frozen=True)
class FiltroPrestamos:
    estado: EstadoPrestamoEnum | None = None
    tipo: TipoPrestamo | None = None
    socio_id: int | None = None
    sede_id: int | None = None  # origen o destino
    numero: str | None = None


@dataclass(frozen=True)
class FiltroRemitos:
    estado: EstadoRemitoEnum | None = None
    motivo: MotivoRemito | None = None
    sede_id: int | None = None  # origen o destino
    numero: str | None = None
    solo_abiertos: bool = False


@dataclass(frozen=True)
class Parametro:
    clave: str
    valor: str
    descripcion: str


class ParametroRepository(Protocol):
    def vigentes(self) -> Parametros:
        """Valores actuales, convertidos y validados."""
        ...

    def listar(self) -> list[Parametro]: ...

    def actualizar(self, clave: str, valor: str) -> Parametro | None:
        """Cambia un valor (ya validado) y lo devuelve; ``None`` si la clave no existe."""
        ...


class PrestamoRepository(Protocol):
    def siguiente_numero(self, anio: int) -> str:
        """Número correlativo ``P-<año>-<secuencia>``."""
        ...

    def agregar(self, prestamo: Prestamo) -> None:
        """Persiste el préstamo y su primer movimiento (asigna ``id``)."""
        ...

    def guardar(self, prestamo: Prestamo) -> None:
        """Persiste estado, fechas y renovaciones, y los movimientos pendientes."""
        ...

    def obtener(self, prestamo_id: int) -> Prestamo | None: ...

    def obtener_para_modificar(self, prestamo_id: int) -> Prestamo | None:
        """Préstamo con la fila bloqueada (``FOR UPDATE``)."""
        ...

    def abiertos_de_socio(self, socio_id: int) -> list[Prestamo]:
        """Préstamos solicitados, en envío, activos o vencidos del socio."""
        ...

    def activos_vencidos(self, hoy: date) -> list[Prestamo]:
        """Préstamos ``Activo`` cuyo vencimiento ya pasó, bloqueados para cambiarlos."""
        ...

    def listar(
        self, filtro: FiltroPrestamos, page: int, size: int
    ) -> tuple[list[Prestamo], int]: ...

    def historial(self, prestamo_id: int) -> list[MovimientoPrestamo]: ...

    def en_curso_de_sede(self, sede_id: int, limite: int) -> tuple[list[Prestamo], int]:
        """Préstamos abiertos con la sede como origen o destino (impiden su baja)."""
        ...


class RemitoRepository(Protocol):
    def siguiente_numero(self, anio: int) -> str:
        """Número correlativo ``R-<año>-<secuencia>``."""
        ...

    def agregar(self, remito: Remito) -> None: ...

    def guardar(self, remito: Remito) -> None: ...

    def obtener(self, remito_id: int) -> Remito | None: ...

    def obtener_para_modificar(self, remito_id: int) -> Remito | None: ...

    def listar(self, filtro: FiltroRemitos, page: int, size: int) -> tuple[list[Remito], int]: ...

    def historial(self, remito_id: int) -> list[MovimientoRemito]: ...

    def abierto_con_ejemplar(self, ejemplar_id: int) -> Remito | None:
        """Remito no finalizado que incluye al ejemplar, si lo hay."""
        ...

    def de_prestamo(self, prestamo_id: int) -> list[Remito]:
        """Remitos (ida y vuelta) con una línea del préstamo, del más antiguo al más nuevo."""
        ...

    def abiertos_de_sede(self, sede_id: int, limite: int) -> tuple[list[Remito], int]:
        """Remitos no finalizados con la sede como origen o destino (impiden su baja)."""
        ...


class IncidenciaRepository(Protocol):
    def agregar(self, incidencia: Incidencia) -> None: ...

    def de_remito(self, remito_id: int) -> list[Incidencia]: ...


@dataclass(frozen=True)
class FiltroReservas:
    socio_id: int | None = None
    libro_id: int | None = None
    sede_id: int | None = None  # sede de retiro
    estado: EstadoReservaEnum | None = None


class ReservaRepository(Protocol):
    def siguiente_numero(self, anio: int) -> str:
        """Número correlativo ``RS-<año>-<secuencia>``."""
        ...

    def agregar(self, reserva: Reserva) -> None:
        """Persiste la reserva (asigna ``id``).

        Raises:
            ReservaDuplicada: El socio ya tiene una reserva activa del libro (índice único).
        """
        ...

    def guardar(self, reserva: Reserva) -> None: ...

    def obtener(self, reserva_id: int) -> Reserva | None:
        """Reserva con su posición en la cola si está pendiente."""
        ...

    def obtener_para_modificar(self, reserva_id: int) -> Reserva | None: ...

    def activas_de_socio(self, socio_id: int) -> list[Reserva]: ...

    def cola_del_libro(self, libro_id: int) -> list[Reserva]:
        """Reservas pendientes del libro en orden FIFO, bloqueadas para asignarlas."""
        ...

    def vencidas(self, hoy: date) -> list[Reserva]:
        """Disponibles para retiro cuya vigencia ya pasó, bloqueadas."""
        ...

    def hay_pendientes(self, libro_id: int) -> bool: ...

    def listar(self, filtro: FiltroReservas, page: int, size: int) -> tuple[list[Reserva], int]: ...

    def activas_de_sede(self, sede_id: int, limite: int) -> tuple[list[Reserva], int]:
        """Reservas activas con retiro en la sede (impiden su baja)."""
        ...
