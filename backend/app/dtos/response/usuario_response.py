"""Respuestas de la API de usuarios del personal (nunca incluyen la contraseña ni su hash)."""

from datetime import datetime

from pydantic import BaseModel

from app.dtos.response.auth_response import SedeResumenResponse
from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.paginacion import Pagina
from app.models.usuario import Usuario


class UsuarioPersonalResponse(BaseModel):
    """Un usuario del personal con su sede y su auditoría."""

    id: int
    username: str
    nombre: str
    rol: str
    activo: bool
    sede_id: int | None
    sede: SedeResumenResponse | None
    creado_en: datetime | None
    creado_por: UsuarioRefResponse | None
    actualizado_en: datetime | None
    actualizado_por: UsuarioRefResponse | None

    @classmethod
    def desde(cls, usuario: Usuario) -> "UsuarioPersonalResponse":
        assert usuario.id is not None
        sede = (
            SedeResumenResponse(
                id=usuario.sede.id, codigo=usuario.sede.codigo, nombre=usuario.sede.nombre
            )
            if usuario.sede
            else None
        )
        return cls(
            id=usuario.id,
            username=usuario.username,
            nombre=usuario.nombre,
            rol=usuario.rol.value,
            activo=usuario.activo,
            sede_id=usuario.sede_id,
            sede=sede,
            creado_en=usuario.creado_en,
            creado_por=UsuarioRefResponse.desde(usuario.creado_por) if usuario.creado_por else None,
            actualizado_en=usuario.actualizado_en,
            actualizado_por=(
                UsuarioRefResponse.desde(usuario.actualizado_por)
                if usuario.actualizado_por
                else None
            ),
        )


class PaginaUsuariosResponse(BaseModel):
    items: list[UsuarioPersonalResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Usuario]) -> "PaginaUsuariosResponse":
        return cls(
            items=[UsuarioPersonalResponse.desde(u) for u in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
