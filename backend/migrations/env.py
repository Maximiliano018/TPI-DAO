from logging.config import fileConfig
from typing import Any, Literal

from alembic import context
from sqlalchemy import engine_from_config, pool

from biblioteca.config import settings
from biblioteca.infrastructure.db.tables import metadata
from biblioteca.infrastructure.db.tipos import FechaHoraUTC

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# La URL de la base sale de biblioteca.config (y del .env), no de alembic.ini.
# Si quien invoca a Alembic ya fijó una URL (CLI de tests, por ejemplo), se respeta.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata del esquema (SQLAlchemy Core) para `alembic revision --autogenerate`.
target_metadata = metadata


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    """Escribe los tipos propios como su tipo SQL base.

    Así las migraciones no importan código de la aplicación, que puede cambiar después.
    """
    if type_ == "type" and isinstance(obj, FechaHoraUTC):
        return "sa.DateTime()"
    return False


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite casi no soporta ALTER TABLE: "batch" recrea la tabla al modificarla.
            render_as_batch=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
