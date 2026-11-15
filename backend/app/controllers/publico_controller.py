"""Endpoints públicos: lo que se ve antes de ingresar al sistema."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.controllers.dependencies import get_publico_service
from app.services.publico_service import PublicoService

router = APIRouter(prefix="/api/v1/publico", tags=["Público"])

Servicio = Annotated[PublicoService, Depends(get_publico_service)]


class _Modelo(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LibroDestacadoResponse(_Modelo):
    libro_id: int
    titulo: str
    autores: list[str]
    portada_url: str | None
    pedidos: int


class InicioPublicoResponse(_Modelo):
    sedes_activas: int
    libros: int
    ejemplares: int
    destacados: list[LibroDestacadoResponse]


@router.get(
    "/inicio",
    response_model=InicioPublicoResponse,
    summary="Datos de la página de inicio pública",
)
def inicio_publico(
    servicio: Servicio, limite: Annotated[int, Query(ge=1, le=24)] = 12
) -> InicioPublicoResponse:
    """Cuántas sedes, libros y ejemplares tiene la red y sus libros más pedidos (con portada).

    No pide sesión: solo informa sobre la colección, nunca sobre socios ni préstamos.
    """
    return InicioPublicoResponse.model_validate(servicio.inicio(limite))
