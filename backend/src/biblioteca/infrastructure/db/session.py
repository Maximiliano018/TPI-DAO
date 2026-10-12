from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from biblioteca.config import settings


class Base(DeclarativeBase):
    """Base de los modelos ORM. Alembic toma de acá la metadata del esquema."""


engine = create_engine(
    settings.database_url,
    # SQLite por defecto no permite usar la conexión desde otro hilo (FastAPI usa varios).
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _activar_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
    # SQLite no controla las claves foráneas salvo que se lo pidamos en cada conexión.
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
