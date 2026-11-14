"""Endpoints de reportes (R1 a R6)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.controllers.dependencies import get_reporte_service, usuario_actual
from app.models.usuario import Usuario
from app.services.reports.reporte_service import ReporteService

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])

Servicio = Annotated[ReporteService, Depends(get_reporte_service)]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]

_ERRORES = {
    401: {"description": "No autenticado (`TOKEN_INVALIDO`)"},
    403: {"description": "El rol no puede emitir este reporte (`FORBIDDEN`)"},
    422: {"description": "Rango de fechas inválido (`VALIDACION`)"},
}
Desde = Annotated[date | None, Query(description="Desde (inclusive), aaaa-mm-dd")]
Hasta = Annotated[date | None, Query(description="Hasta (inclusive), aaaa-mm-dd")]
SedeId = Annotated[int | None, Query(description="Sede (el bibliotecario siempre ve la suya)")]


class _Modelo(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- R1 --------------------------------------------------------------------------------------


class RutaResponse(_Modelo):
    sede_origen_id: int
    sede_origen: str
    sede_destino_id: int
    sede_destino: str
    envios: int
    ejemplares: int
    tiempo_promedio_transito_dias: float


class MovimientoResponse(_Modelo):
    desde: date | None
    hasta: date | None
    rutas: list[RutaResponse]
    total_envios: int
    total_ejemplares: int


@router.get(
    "/movimiento-entre-sedes",
    response_model=MovimientoResponse,
    summary="R1. Movimiento de ejemplares entre sedes",
    responses=_ERRORES,
)
def movimiento_entre_sedes(
    servicio: Servicio,
    actor: Autenticado,
    desde: Desde = None,
    hasta: Hasta = None,
    sede_id: SedeId = None,
) -> MovimientoResponse:
    """Por ruta origen → destino: envíos, ejemplares y tiempo promedio de tránsito.

    Solo cuentan los remitos recibidos (con o sin incidencias) en el período.
    """
    resultado = servicio.movimiento_entre_sedes(actor, desde, hasta, sede_id)
    return MovimientoResponse.model_validate(resultado)


# --- R2 --------------------------------------------------------------------------------------


class _Conteo(_Modelo):
    total_envios: int
    recibidos: int
    extraviados: int
    danados: int
    destruidos: int
    incompletos: int
    tasa_exito: float | None
    tasa_incidencias: float | None


class EnviosDeSedeResponse(_Conteo):
    sede_id: int
    sede: str


class EnviosResponse(_Conteo):
    desde: date | None
    hasta: date | None
    por_sede: list[EnviosDeSedeResponse]


@router.get(
    "/envios-e-incidencias",
    response_model=EnviosResponse,
    summary="R2. Envíos exitosos e incidencias",
    responses=_ERRORES,
)
def envios_e_incidencias(
    servicio: Servicio,
    actor: Autenticado,
    desde: Desde = None,
    hasta: Hasta = None,
    sede_id: SedeId = None,
) -> EnviosResponse:
    """Tasa de remitos recibidos sin problemas frente a extraviados, dañados, destruidos e
    incompletos (recibidos con faltantes).

    Solo el administrador. Excluye los anulados y los que siguen abiertos.
    """
    return EnviosResponse.model_validate(
        servicio.envios_e_incidencias(actor, desde, hasta, sede_id)
    )


# --- R3 --------------------------------------------------------------------------------------


class LibroSolicitadoResponse(_Modelo):
    posicion: int
    libro_id: int
    titulo: str
    prestamos: int
    sede_origen_frecuente: str | None
    sede_destino_frecuente: str | None


class LibrosSolicitadosResponse(_Modelo):
    desde: date | None
    hasta: date | None
    libros: list[LibroSolicitadoResponse]


@router.get(
    "/libros-mas-solicitados",
    response_model=LibrosSolicitadosResponse,
    summary="R3. Libros más solicitados entre sedes",
    responses=_ERRORES,
)
def libros_mas_solicitados(
    servicio: Servicio,
    actor: Autenticado,
    desde: Desde = None,
    hasta: Hasta = None,
    categoria_id: int | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 10,
) -> LibrosSolicitadosResponse:
    """Ranking por préstamos interbibliotecarios no cancelados. Solo el administrador."""
    return LibrosSolicitadosResponse.model_validate(
        servicio.libros_mas_solicitados(actor, desde, hasta, categoria_id, limite)
    )


# --- R4 --------------------------------------------------------------------------------------


class VencidoResponse(_Modelo):
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


class MultaReporteResponse(_Modelo):
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


class VencidosResponse(_Modelo):
    fecha: date
    monto_por_dia: Decimal
    vencidos: list[VencidoResponse]
    multas: list[MultaReporteResponse]
    total_acumulado_vencidos: Decimal
    total_multas_pendientes: Decimal
    total_adeudado: Decimal


@router.get(
    "/vencidos-y-multas",
    response_model=VencidosResponse,
    summary="R4. Préstamos vencidos y multas",
    responses=_ERRORES,
)
def vencidos_y_multas(
    servicio: Servicio,
    actor: Autenticado,
    sede_id: SedeId = None,
    socio_id: int | None = None,
    estado_multa: Literal["PENDIENTE", "SALDADA"] | None = None,
    desde: Desde = None,
    hasta: Hasta = None,
) -> VencidosResponse:
    """Vencidos con días de atraso y multa acumulada a hoy, más las multas generadas.

    El período (`desde`, `hasta`) filtra las multas por su fecha de generación.
    """
    return VencidosResponse.model_validate(
        servicio.vencidos_y_multas(actor, sede_id, socio_id, estado_multa, desde, hasta)
    )


# --- R5 --------------------------------------------------------------------------------------


class DisponibilidadResponse(_Modelo):
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


class PaginaDisponibilidadResponse(_Modelo):
    items: list[DisponibilidadResponse]
    total: int
    page: int
    size: int


@router.get(
    "/disponibilidad-por-sede",
    response_model=PaginaDisponibilidadResponse,
    summary="R5. Disponibilidad de catálogo por sede",
    responses={401: _ERRORES[401]},
)
def disponibilidad_por_sede(
    servicio: Servicio,
    actor: Autenticado,
    sede_id: int | None = None,
    libro_id: int | None = None,
    categoria_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaginaDisponibilidadResponse:
    """Ejemplares activos por libro y sede: totales, disponibles, prestados, reservados y en
    tránsito. Lo pueden emitir todos los roles."""
    return PaginaDisponibilidadResponse.model_validate(
        servicio.disponibilidad_por_sede(actor, sede_id, libro_id, categoria_id, page, size)
    )


# --- R6 --------------------------------------------------------------------------------------


class PrestamoEnCursoResponse(_Modelo):
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


class RemitoAbiertoResponse(_Modelo):
    remito_id: int
    numero: str
    motivo: str
    estado: str
    sede_origen: str
    sede_destino: str
    fecha_generacion: datetime
    antiguedad_dias: int
    ejemplares: int


class ActivosResponse(_Modelo):
    fecha: date
    prestamos: list[PrestamoEnCursoResponse]
    remitos: list[RemitoAbiertoResponse]


@router.get(
    "/prestamos-activos-y-en-transito",
    response_model=ActivosResponse,
    summary="R6. Préstamos activos y remitos abiertos",
    responses=_ERRORES,
)
def activos_y_en_transito(
    servicio: Servicio, actor: Autenticado, sede_id: SedeId = None
) -> ActivosResponse:
    """Préstamos en manos de socios con su vencimiento y remitos abiertos con su antigüedad."""
    return ActivosResponse.model_validate(servicio.activos_y_en_transito(actor, sede_id))
