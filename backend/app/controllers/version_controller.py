from fastapi import APIRouter

from app.dtos.response.version_response import VersionResponse

VERSION = "0.1.0"

router = APIRouter(prefix="/api", tags=["Sistema"])


@router.get("/version", response_model=VersionResponse, summary="Estado y versión del backend")
def obtener_version() -> VersionResponse:
    """Indica que el backend está en línea y su versión."""
    return VersionResponse(servicio="backend", estado="ok", version=VERSION)
