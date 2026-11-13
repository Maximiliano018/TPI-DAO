"""Modelos ORM (tablas). Importar este paquete registra todas las tablas."""

from app.db.models.catalogo import (
    AutorORM,
    CategoriaORM,
    EjemplarORM,
    LibroAutorORM,
    LibroORM,
    MovimientoEjemplarORM,
)
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
    "AutorORM",
    "CategoriaORM",
    "EjemplarORM",
    "LibroAutorORM",
    "LibroORM",
    "MovimientoEjemplarORM",
    "ExcepcionHorarioSedeORM",
    "HistorialSedeORM",
    "HorarioSedeORM",
    "LocalidadORM",
    "ProvinciaORM",
    "SedeORM",
    "SocioORM",
    "UsuarioORM",
]
