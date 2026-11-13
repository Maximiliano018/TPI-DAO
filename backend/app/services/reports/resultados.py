"""Resultados de los reportes (solo datos, sin lógica)."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Periodo:
    desde: date | None
    hasta: date | None


# --- R1. Movimiento entre sedes --------------------------------------------------------------


@dataclass(frozen=True)
class RutaEntreSedes:
    sede_origen_id: int
    sede_origen: str
    sede_destino_id: int
    sede_destino: str
    envios: int
    ejemplares: int
    tiempo_promedio_transito_dias: float


@dataclass(frozen=True)
class MovimientoEntreSedes:
    desde: date | None
    hasta: date | None
    rutas: list[RutaEntreSedes]
    total_envios: int
    total_ejemplares: int


# --- R2. Envíos e incidencias ----------------------------------------------------------------


@dataclass(frozen=True)
class ConteoDeEnvios:
    total_envios: int
    recibidos: int
    extraviados: int
    danados: int
    destruidos: int

    @property
    def tasa_exito(self) -> float | None:
        return round(self.recibidos / self.total_envios, 4) if self.total_envios else None

    @property
    def tasa_incidencias(self) -> float | None:
        if not self.total_envios:
            return None
        return round((self.total_envios - self.recibidos) / self.total_envios, 4)


@dataclass(frozen=True)
class EnviosDeSede(ConteoDeEnvios):
    sede_id: int = 0
    sede: str = ""


@dataclass(frozen=True)
class EnviosEIncidencias(ConteoDeEnvios):
    desde: date | None = None
    hasta: date | None = None
    por_sede: list[EnviosDeSede] = field(default_factory=list)


# --- R3. Libros más solicitados entre sedes --------------------------------------------------


@dataclass(frozen=True)
class LibroSolicitado:
    posicion: int
    libro_id: int
    titulo: str
    prestamos: int
    sede_origen_frecuente: str | None
    sede_destino_frecuente: str | None


@dataclass(frozen=True)
class LibrosMasSolicitados:
    desde: date | None
    hasta: date | None
    libros: list[LibroSolicitado]


# --- R4. Vencidos y multas -------------------------------------------------------------------


@dataclass(frozen=True)
class PrestamoVencido:
    prestamo_id: int
    numero: str
    socio_id: int
    socio: str
    numero_socio: str
    libro: str
    sede: str
    fecha_vencimiento: date
    dias_atraso: int
    multa_acumulada: Decimal


@dataclass(frozen=True)
class MultaDelReporte:
    multa_id: int
    prestamo_id: int
    numero_prestamo: str
    socio_id: int
    socio: str
    libro: str
    dias_atraso: int
    monto_total: Decimal
    estado: str
    fecha_generacion: datetime


@dataclass(frozen=True)
class VencidosYMultas:
    fecha: date
    monto_por_dia: Decimal
    vencidos: list[PrestamoVencido]
    multas: list[MultaDelReporte]
    total_acumulado_vencidos: Decimal
    total_multas_pendientes: Decimal
    total_adeudado: Decimal


# --- R5. Disponibilidad por sede -------------------------------------------------------------


@dataclass(frozen=True)
class DisponibilidadLibroSede:
    libro_id: int
    titulo: str
    sede_id: int
    sede: str
    totales: int
    disponibles: int
    prestados: int
    reservados: int
    en_transito: int
    otros: int


@dataclass(frozen=True)
class DisponibilidadPorSede:
    items: list[DisponibilidadLibroSede]
    total: int
    page: int
    size: int


# --- R6. Préstamos activos y remitos en tránsito ---------------------------------------------


@dataclass(frozen=True)
class PrestamoEnCurso:
    prestamo_id: int
    numero: str
    tipo: str
    estado: str
    socio: str
    libro: str
    sede_origen: str
    sede_destino: str
    fecha_vencimiento: date | None
    dias_para_vencer: int | None


@dataclass(frozen=True)
class RemitoAbierto:
    remito_id: int
    numero: str
    motivo: str
    estado: str
    sede_origen: str
    sede_destino: str
    fecha_generacion: datetime
    antiguedad_dias: int
    ejemplares: int


@dataclass(frozen=True)
class ActivosYEnTransito:
    fecha: date
    prestamos: list[PrestamoEnCurso]
    remitos: list[RemitoAbierto]
