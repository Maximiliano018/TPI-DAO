"""Entidad de dominio ``Prestamo``: un ejemplar prestado a un socio.

Un préstamo tiene un solo ejemplar y dos sedes: origen (donde está el ejemplar) y destino (donde
el socio lo retira y devuelve). En el préstamo local coinciden. El ciclo de vida sigue el patrón
State (``models/states/prestamo.py``) y cada cambio queda en su historial (CA-PRE-18).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from app.exceptions import RenovacionNoPermitida
from app.models.policies.plazo import PoliticaPlazo
from app.models.states.prestamo import (
    ABIERTOS,
    EstadoPrestamo,
    EstadoPrestamoEnum,
    Solicitado,
)
from app.models.usuario import UsuarioRef


class TipoPrestamo(StrEnum):
    LOCAL = "LOCAL"
    INTERBIBLIOTECARIO = "INTERBIBLIOTECARIO"


@dataclass(frozen=True)
class MovimientoPrestamo:
    estado_anterior: EstadoPrestamoEnum | None
    estado_nuevo: EstadoPrestamoEnum
    fecha_hora: datetime
    usuario: UsuarioRef | None
    observacion: str | None = None


def formatear_numero(prefijo: str, anio: int, secuencia: int) -> str:
    """Número legible con año y secuencia: ``P-2026-000118``."""
    return f"{prefijo}-{anio}-{secuencia:06d}"


@dataclass
class Prestamo:
    """Préstamo de un ejemplar a un socio."""

    id: int | None
    numero: str
    tipo: TipoPrestamo
    socio_id: int
    ejemplar_id: int
    libro_id: int
    sede_origen_id: int
    sede_destino_id: int
    fecha_solicitud: datetime
    registrado_por: UsuarioRef | None
    estado: EstadoPrestamo = field(default_factory=Solicitado)
    fecha_inicio: date | None = None
    fecha_vencimiento: date | None = None
    fecha_devolucion: datetime | None = None
    renovaciones: int = 0
    # Último día para retirarlo en la sede destino; vencido, se cancela solo (RF-PRE-20).
    fecha_limite_retiro: date | None = None
    movimientos_pendientes: list[MovimientoPrestamo] = field(default_factory=list)
    # Datos para mostrar (los completa el repositorio).
    socio_nombre: str | None = None
    numero_socio: str | None = None
    codigo_ejemplar: str | None = None
    libro_titulo: str | None = None
    sede_origen_nombre: str | None = None
    sede_destino_nombre: str | None = None

    # --- consultas ------------------------------------------------------------------------

    @property
    def estado_nombre(self) -> EstadoPrestamoEnum:
        return self.estado.nombre

    @property
    def esta_abierto(self) -> bool:
        """Solicitado, en envío, activo o vencido: todavía ocupa el ejemplar y el cupo del socio."""
        return self.estado_nombre in ABIERTOS

    @property
    def es_interbibliotecario(self) -> bool:
        return self.tipo == TipoPrestamo.INTERBIBLIOTECARIO

    def dias_de_atraso(self, fecha: date) -> int:
        """Días después del vencimiento (el día de vencimiento todavía está en término)."""
        if self.fecha_vencimiento is None:
            return 0
        return max(0, (fecha - self.fecha_vencimiento).days)

    @property
    def cancelable_por_el_socio(self) -> bool:
        """El socio puede cancelar su solicitud mientras no salió de la sede origen."""
        return self.estado_nombre == EstadoPrestamoEnum.SOLICITADO

    def retiro_vencido(self, hoy: date) -> bool:
        """Pasó el último día para retirarlo y todavía no se entregó (el día límite vale)."""
        return (
            self.estado_nombre in (EstadoPrestamoEnum.SOLICITADO, EstadoPrestamoEnum.EN_ENVIO)
            and self.fecha_limite_retiro is not None
            and hoy > self.fecha_limite_retiro
        )

    def interviene(self, sede_id: int | None) -> bool:
        """La sede es origen o destino del préstamo."""
        return sede_id in (self.sede_origen_id, self.sede_destino_id)

    # --- transiciones ---------------------------------------------------------------------

    def registrar_alta(self, actor: UsuarioRef | None, ahora: datetime) -> None:
        """Primer movimiento del historial (lo usa la fábrica al crearlo)."""
        self.movimientos_pendientes.append(
            MovimientoPrestamo(None, self.estado_nombre, ahora, actor, "Solicitud registrada")
        )

    def habilitar_retiro(self, hasta: date, actor: UsuarioRef | None, ahora: datetime) -> None:
        """El ejemplar ya está en la sede destino: el socio tiene hasta ``hasta`` para retirarlo.

        Queda en el historial sin cambiar de estado.
        """
        self.fecha_limite_retiro = hasta
        self._transicion(
            self.estado, actor, ahora, f"Disponible para retirar hasta el {hasta:%d/%m/%Y}"
        )

    def enviar(self, actor: UsuarioRef, ahora: datetime, remito: str) -> None:
        """El ejemplar sale de la sede origen con un remito (solo interbibliotecario)."""
        self._transicion(self.estado.enviar(), actor, ahora, f"Incluido en el remito {remito}")

    def entregar(
        self, hoy: date, politica: PoliticaPlazo, actor: UsuarioRef, ahora: datetime
    ) -> None:
        """Entrega al socio: el préstamo empieza y se calcula el vencimiento (RF-PRE-09)."""
        nuevo = self.estado.entregar()
        self.fecha_inicio = hoy
        self.fecha_vencimiento = politica.vencimiento(hoy)
        self._transicion(nuevo, actor, ahora, "Entregado al socio")

    def renovar(
        self,
        hoy: date,
        politica: PoliticaPlazo,
        *,
        maximo: int,
        hay_reservas: bool,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> None:
        """Extiende el vencimiento un plazo más (RF-PRE-14).

        Raises:
            TransicionInvalida: No está activo.
            RenovacionNoPermitida: Ya venció, hay reservas del libro o alcanzó el máximo.
        """
        nuevo = self.estado.renovar()
        assert self.fecha_vencimiento is not None
        if hoy > self.fecha_vencimiento:
            raise RenovacionNoPermitida(
                f"El préstamo {self.numero} está vencido: no se puede renovar."
            )
        if hay_reservas:
            raise RenovacionNoPermitida(
                "Hay socios esperando este libro (reservas pendientes): no se puede renovar."
            )
        if self.renovaciones >= maximo:
            raise RenovacionNoPermitida(
                f"El préstamo {self.numero} ya alcanzó el máximo de {maximo} renovación(es)."
            )
        self.renovaciones += 1
        self.fecha_vencimiento = politica.vencimiento(self.fecha_vencimiento)
        texto = f"Renovado hasta el {self.fecha_vencimiento:%d/%m/%Y}"
        self._transicion(nuevo, actor, ahora, texto)

    def marcar_vencido(self, hoy: date, ahora: datetime) -> bool:
        """Pasa a ``Vencido`` si ya pasó el día de vencimiento (CA-PRE-13 y 14).

        Returns:
            ``True`` si cambió de estado.
        """
        if self.estado_nombre != EstadoPrestamoEnum.ACTIVO or self.fecha_vencimiento is None:
            return False
        if hoy <= self.fecha_vencimiento:
            return False
        self._transicion(self.estado.marcar_vencido(), None, ahora, "Venció el plazo")
        return True

    def devolver(self, fecha: datetime, actor: UsuarioRef, ahora: datetime) -> None:
        """El socio devolvió el ejemplar."""
        nuevo = self.estado.devolver()
        self.fecha_devolucion = fecha
        self._transicion(nuevo, actor, ahora, "Devuelto")

    def cancelar(self, motivo: str, actor: UsuarioRef | None, ahora: datetime) -> None:
        """Anula el préstamo antes de entregarlo (RF-PRE-13)."""
        self._transicion(self.estado.cancelar(), actor, ahora, motivo)

    def _transicion(
        self,
        nuevo: EstadoPrestamo,
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
    ) -> None:
        anterior = self.estado_nombre
        self.estado = nuevo
        self.movimientos_pendientes.append(
            MovimientoPrestamo(anterior, nuevo.nombre, ahora, actor, observacion)
        )
