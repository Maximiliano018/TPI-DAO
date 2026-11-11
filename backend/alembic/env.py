"""Entorno de Alembic: toma la URL de la configuración de la aplicación."""

import os

from sqlalchemy import create_engine

from alembic import context
from app.config import get_settings
from app.db import models  # noqa: F401  (registra las tablas en el metadata)
from app.db.base import Base

target_metadata = Base.metadata


def _url() -> str:
    """URL de destino: ``ALEMBIC_URL`` (pruebas) o ``DATABASE_URL``."""
    return os.environ.get("ALEMBIC_URL") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
