"""Incidencias: extravío, daño o destrucción de un ejemplar (en un envío o en una devolución)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models.usuario import UsuarioRef


class TipoIncidencia(StrEnum):
    EXTRAVIO = "EXTRAVIO"
    DANIO = "DANIO"
    DESTRUCCION = "DESTRUCCION"


class OrigenIncidencia(StrEnum):
    REMITO = "REMITO"
    DEVOLUCION = "DEVOLUCION"


@dataclass(frozen=True)
class Incidencia:
    """Registro de un problema con un ejemplar. Alimenta el reporte de envíos e incidencias."""

    tipo: TipoIncidencia
    origen: OrigenIncidencia
    ejemplar_id: int
    descripcion: str
    fecha: datetime
    usuario: UsuarioRef | None
    socio_id: int | None = None
    prestamo_id: int | None = None
    remito_id: int | None = None
