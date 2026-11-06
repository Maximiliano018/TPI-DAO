from pydantic import BaseModel


class VersionResponse(BaseModel):
    """Estado y versión del backend."""

    servicio: str
    estado: str
    version: str
