"""Modelos ORM (tablas). Importar este paquete registra todas las tablas."""

from app.db.models.catalogo import (
    AutorORM,
    CategoriaORM,
    EjemplarORM,
    LibroAutorORM,
    LibroORM,
    MovimientoEjemplarORM,
)
from app.db.models.devolucion import DevolucionORM, MultaORM
from app.db.models.geografia import LocalidadORM, ProvinciaORM
from app.db.models.prestamo import (
    DetalleRemitoORM,
    IncidenciaORM,
    MovimientoPrestamoORM,
    MovimientoRemitoORM,
    ParametroORM,
    PrestamoORM,
    RemitoORM,
    ReservaORM,
)
from app.db.models.sede import (
    ExcepcionHorarioSedeORM,
    HistorialSedeORM,
    HorarioSedeORM,
    SedeORM,
)
from app.db.models.socio import SocioORM
from app.db.models.usuario import UsuarioORM

__all__ = [
    "DetalleRemitoORM",
    "DevolucionORM",
    "MultaORM",
    "IncidenciaORM",
    "MovimientoPrestamoORM",
    "MovimientoRemitoORM",
    "ParametroORM",
    "PrestamoORM",
    "RemitoORM",
    "ReservaORM",
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
