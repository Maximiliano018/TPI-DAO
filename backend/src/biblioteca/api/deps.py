from collections.abc import Iterator

from sqlalchemy.orm import Session

from biblioteca.infrastructure.db.session import SessionLocal


def get_db() -> Iterator[Session]:
    """Abre una sesión por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
