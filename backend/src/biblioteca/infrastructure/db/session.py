import sqlite3
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from biblioteca.config import settings


def _configurar_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """PRAGMAs que SQLite necesita en cada conexión (ARCHITECTURE.md §5.4)."""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    # Sin esto, SQLite ignora las claves foráneas.
    cursor.execute("PRAGMA foreign_keys = ON")
    # Lecturas concurrentes con una escritura en curso.
    cursor.execute("PRAGMA journal_mode = WAL")
    # Espera hasta 5 s si otra conexión tiene la base bloqueada, en vez de fallar.
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()


def crear_engine(url: str) -> Engine:
    """Crea un engine configurado. Los tests lo usan con bases temporales."""
    es_sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        # SQLite por defecto no permite usar la conexión desde otro hilo (FastAPI usa varios).
        connect_args={"check_same_thread": False} if es_sqlite else {},
    )
    if es_sqlite:
        event.listen(engine, "connect", _configurar_sqlite)
    return engine


engine = crear_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
