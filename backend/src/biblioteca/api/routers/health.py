from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from biblioteca.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Verifica que la API responde y que la base de datos está accesible."""
    db.execute(text("SELECT 1"))
    return {"estado": "ok", "base_de_datos": "ok"}
