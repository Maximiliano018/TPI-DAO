from pathlib import Path

from alembic import command
from alembic.config import Config

# backend/alembic.ini (este archivo está en backend/src/biblioteca/infrastructure/db/).
ALEMBIC_INI = Path(__file__).resolve().parents[4] / "alembic.ini"


def configuracion_alembic(url: str | None = None) -> Config:
    """Configuración de Alembic. Sin `url`, migrations/env.py usa la de `settings`."""
    config = Config(str(ALEMBIC_INI))
    if url is not None:
        config.set_main_option("sqlalchemy.url", url)
    return config


def aplicar_migraciones(url: str | None = None) -> None:
    command.upgrade(configuracion_alembic(url), "head")
