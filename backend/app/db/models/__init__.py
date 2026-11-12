"""Modelos ORM (tablas). Importar este paquete registra todas las tablas."""

from app.db.models.geografia import LocalidadORM, ProvinciaORM
from app.db.models.sede import (
    ExcepcionHorarioSedeORM,
    HistorialSedeORM,
    HorarioSedeORM,
    SedeORM,
)
from app.db.models.socio import SocioORM
from app.db.models.usuario import UsuarioORM

__all__ = [
    "ExcepcionHorarioSedeORM",
    "HistorialSedeORM",
    "HorarioSedeORM",
    "LocalidadORM",
    "ProvinciaORM",
    "SedeORM",
    "SocioORM",
    "UsuarioORM",
]
