"""Motor y sesiones de SQLAlchemy."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Crea (una sola vez) el motor de la base configurada en ``DATABASE_URL``."""
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def crear_fabrica_sesiones(engine: Engine | None = None) -> sessionmaker[Session]:
    """Devuelve una fábrica de sesiones sobre el motor indicado (o el configurado)."""
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False)


def sesion_por_solicitud() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por solicitud, cerrada al terminar."""
    sesion = crear_fabrica_sesiones()()
    try:
        yield sesion
    finally:
        sesion.close()
