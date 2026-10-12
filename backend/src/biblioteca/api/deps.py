from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from biblioteca.infrastructure.db.session import SessionLocal
from biblioteca.infrastructure.repositories.unidad_de_trabajo import SqlUnidadDeTrabajo


def get_db() -> Iterator[Session]:
    """Abre una sesión por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ahora() -> datetime:
    """Instante actual en UTC. Es una dependencia para poder fijarlo en los tests."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class Paginacion:
    limit: int
    offset: int


def get_paginacion(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginacion:
    return Paginacion(limit, offset)


Db = Annotated[Session, Depends(get_db)]
Ahora = Annotated[datetime, Depends(get_ahora)]
Pagina = Annotated[Paginacion, Depends(get_paginacion)]


def get_uow(db: Db) -> SqlUnidadDeTrabajo:
    """Unidad de trabajo del request, sobre la misma sesión."""
    return SqlUnidadDeTrabajo(db)


Uow = Annotated[SqlUnidadDeTrabajo, Depends(get_uow)]
