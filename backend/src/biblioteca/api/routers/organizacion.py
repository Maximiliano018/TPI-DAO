from typing import Any

from fastapi import APIRouter

from biblioteca.api.deps import Db, Pagina
from biblioteca.api.schemas.organizacion import SedeOut, SocioOut
from biblioteca.application.services.sedes import listar_sedes
from biblioteca.application.services.socios import listar_socios

router = APIRouter(tags=["organización"])


@router.get("/sedes", response_model=list[SedeOut])
def get_sedes(db: Db) -> list[dict[str, Any]]:
    return listar_sedes(db)


@router.get("/socios", response_model=list[SocioOut])
def get_socios(db: Db, pagina: Pagina, buscar: str | None = None) -> list[dict[str, Any]]:
    """Busca por DNI, número de socio, nombre o apellido."""
    return listar_socios(db, buscar, pagina.limit, pagina.offset)
