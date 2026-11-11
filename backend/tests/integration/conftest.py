"""Base PostgreSQL de pruebas.

* Se crea una base ``<nombre>_test`` (o la de ``DATABASE_URL_TEST``) si no existe.
* El esquema se rehace y se aplica con ``alembic upgrade head`` una vez por sesión de pruebas:
  así las migraciones se prueban de verdad.
* Cada prueba corre dentro de una transacción que se revierte al terminar.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.config import get_settings

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def url_de_prueba() -> str:
    """URL de la base de pruebas: ``DATABASE_URL_TEST`` o la de desarrollo con sufijo ``_test``."""
    settings = get_settings()
    if settings.database_url_test:
        return settings.database_url_test
    url = make_url(settings.database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _crear_base_si_no_existe(url: str) -> None:
    destino = make_url(url)
    admin = create_engine(destino.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as con:
        existe = con.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": destino.database}
        ).scalar()
        if not existe:
            con.execute(text(f'CREATE DATABASE "{destino.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine_prueba() -> Iterator[Engine]:
    url = url_de_prueba()
    _crear_base_si_no_existe(url)
    engine = create_engine(url)
    with engine.begin() as con:
        con.execute(text("DROP SCHEMA public CASCADE"))
        con.execute(text("CREATE SCHEMA public"))
    os.environ["ALEMBIC_URL"] = url
    config = Config(str(RAIZ_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def sesion(engine_prueba: Engine) -> Iterator[Session]:
    """Sesión dentro de una transacción externa que se revierte al terminar la prueba."""
    conexion = engine_prueba.connect()
    transaccion = conexion.begin()
    s = Session(bind=conexion, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield s
    s.close()
    transaccion.rollback()
    conexion.close()
