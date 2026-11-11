"""Cuerpos de entrada de la API de usuarios del personal."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.usuario import Rol
from app.services.usuario_service import DatosUsuarioNuevo


class UsuarioCrearRequest(BaseModel):
    """Alta de un administrador o un bibliotecario.

    El formato de ``username``, ``nombre`` y ``password`` lo valida el dominio.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "bibliotecario.norte",
                "password": "Clave-segura-123",
                "nombre": "Lucía Gómez",
                "rol": "BIBLIOTECARIO",
                "sede_id": 2,
            }
        }
    )

    username: str = Field(max_length=100)
    password: str = Field(max_length=300)
    nombre: str = Field(max_length=300)
    rol: Rol
    sede_id: int | None = None

    def a_datos(self) -> DatosUsuarioNuevo:
        return DatosUsuarioNuevo(
            username=self.username,
            password=self.password,
            nombre=self.nombre,
            rol=self.rol,
            sede_id=self.sede_id,
        )


class UsuarioModificarRequest(BaseModel):
    """Modificación: el nombre y, para un bibliotecario, la sede. No cambia el rol ni el usuario."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"nombre": "Lucía Gómez", "sede_id": 3}}
    )

    nombre: str = Field(max_length=300)
    sede_id: int | None = None
