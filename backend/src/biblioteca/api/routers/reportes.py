from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from biblioteca.api.deps import AdminOBibliotecario, Ahora, Alcance, Db, usuario_actual
from biblioteca.api.schemas.reportes import (
    EnviosExitososOut,
    LibroSolicitadoOut,
    MovimientoSedesOut,
    TableroOut,
    VencidosMultasOut,
)
from biblioteca.application.reports.envios_exitosos import envios_exitosos
from biblioteca.application.reports.libros_mas_solicitados import libros_mas_solicitados
from biblioteca.application.reports.movimiento_sedes import movimiento_entre_sedes
from biblioteca.application.reports.tablero import resumen
from biblioteca.application.reports.vencidos_multas import vencidos_y_multas

# Tablero, R1 y R2 (logísticos) los ven todos los roles; R3 y R4, el ADMIN y los
# bibliotecarios. Cada uno ve los datos de su sede; el ADMIN, los de toda la red.
router = APIRouter(tags=["reportes"], dependencies=[Depends(usuario_actual)])


@router.get("/tablero", response_model=TableroOut)
def get_tablero(db: Db, ahora: Ahora, alcance: Alcance) -> dict[str, Any]:
    """Préstamos activos, material en tránsito y alertas (reporte R6)."""
    return resumen(db, ahora, sede_id=alcance)


@router.get("/reportes/movimiento-entre-sedes", response_model=MovimientoSedesOut)
def get_movimiento_entre_sedes(
    db: Db, alcance: Alcance, desde: date | None = None, hasta: date | None = None
) -> dict[str, Any]:
    """R1: envíos por ruta origen → destino y tiempo promedio de tránsito."""
    return movimiento_entre_sedes(db, desde, hasta, sede_id=alcance)


@router.get("/reportes/envios-exitosos", response_model=EnviosExitososOut)
def get_envios_exitosos(
    db: Db, alcance: Alcance, desde: date | None = None, hasta: date | None = None
) -> dict[str, Any]:
    """R2: tasa de envíos recibidos conformes e incidencias por tipo y por sede."""
    return envios_exitosos(db, desde, hasta, sede_id=alcance)


@router.get("/reportes/libros-mas-solicitados", response_model=list[LibroSolicitadoOut])
def get_libros_mas_solicitados(
    db: Db,
    alcance: Alcance,
    _actor: AdminOBibliotecario,
    desde: date | None = None,
    hasta: date | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[dict[str, Any]]:
    """R3: ranking de libros pedidos en préstamos inter-sedes."""
    return libros_mas_solicitados(db, desde, hasta, limite, sede_id=alcance)


@router.get("/reportes/vencidos-y-multas", response_model=VencidosMultasOut)
def get_vencidos_y_multas(
    db: Db, ahora: Ahora, alcance: Alcance, _actor: AdminOBibliotecario
) -> dict[str, Any]:
    """R4: préstamos vencidos y multas acumuladas por socio y por sede."""
    return vencidos_y_multas(db, ahora.date(), sede_id=alcance)
