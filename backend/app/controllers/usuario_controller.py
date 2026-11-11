"""Endpoints de usuarios del personal: solo el administrador."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import get_usuario_service, requiere
from app.dtos.request.usuario_request import UsuarioCrearRequest, UsuarioModificarRequest
from app.dtos.response.usuario_response import PaginaUsuariosResponse, UsuarioPersonalResponse
from app.models.usuario import Permiso, Rol, Usuario
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios del personal"])

Servicio = Annotated[UsuarioService, Depends(get_usuario_service)]
Administrador = Annotated[Usuario, Depends(requiere(Permiso.USUARIO_ADMINISTRAR))]

_ERROR_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_ERROR_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_ERROR_404 = {
    "description": "El usuario o la sede no existen (`USUARIO_NO_ENCONTRADO`, `SEDE_NO_ENCONTRADA`)"
}
_ERROR_422 = {"description": "Datos inválidos (`VALIDACION`)"}


@router.post(
    "",
    response_model=UsuarioPersonalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de personal",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "Usuario repetido (`DUPLICADO`) o sede en baja (`SEDE_EN_BAJA`)"},
        422: _ERROR_422,
    },
)
def crear_usuario(
    datos: UsuarioCrearRequest, response: Response, servicio: Servicio, actor: Administrador
) -> UsuarioPersonalResponse:
    """Crea un administrador o un bibliotecario. Este último exige una sede activa."""
    usuario = servicio.crear(actor, datos.a_datos())
    response.headers["Location"] = f"/api/v1/usuarios/{usuario.id}"
    return UsuarioPersonalResponse.desde(usuario)


@router.get(
    "",
    response_model=PaginaUsuariosResponse,
    summary="Listado paginado del personal",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def listar_usuarios(
    servicio: Servicio,
    actor: Administrador,
    rol: Rol | None = None,
    sede_id: int | None = None,
    activo: bool | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Nombre o usuario")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaUsuariosResponse:
    """Lista administradores y bibliotecarios; los socios no aparecen."""
    return PaginaUsuariosResponse.desde(servicio.listar(actor, rol, sede_id, activo, q, page, size))


@router.get(
    "/{usuario_id}",
    response_model=UsuarioPersonalResponse,
    summary="Detalle de un usuario del personal",
    responses={401: _ERROR_401, 403: _ERROR_403, 404: _ERROR_404},
)
def obtener_usuario(
    usuario_id: int, servicio: Servicio, actor: Administrador
) -> UsuarioPersonalResponse:
    return UsuarioPersonalResponse.desde(servicio.obtener(actor, usuario_id))


@router.put(
    "/{usuario_id}",
    response_model=UsuarioPersonalResponse,
    summary="Modificar nombre y sede",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "La sede destino está en baja (`SEDE_EN_BAJA`)"},
        422: _ERROR_422,
    },
)
def modificar_usuario(
    usuario_id: int, datos: UsuarioModificarRequest, servicio: Servicio, actor: Administrador
) -> UsuarioPersonalResponse:
    """Cambia el nombre y reasigna al bibliotecario a otra sede activa.

    El cambio rige desde la siguiente solicitud del usuario. El rol y el usuario no cambian.
    """
    return UsuarioPersonalResponse.desde(
        servicio.modificar(actor, usuario_id, datos.nombre, datos.sede_id)
    )


@router.post(
    "/{usuario_id}/baja",
    response_model=UsuarioPersonalResponse,
    summary="Dar de baja a un usuario",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "Ya estaba dado de baja (`USUARIO_YA_EN_BAJA`)"},
        422: {"description": "El administrador no puede darse de baja a sí mismo (`VALIDACION`)"},
    },
)
def dar_de_baja_usuario(
    usuario_id: int, servicio: Servicio, actor: Administrador
) -> UsuarioPersonalResponse:
    """Baja lógica: conserva el historial y desvincula al bibliotecario de su sede."""
    return UsuarioPersonalResponse.desde(servicio.dar_de_baja(actor, usuario_id))


@router.post(
    "/{usuario_id}/reactivar",
    response_model=UsuarioPersonalResponse,
    summary="Reactivar a un usuario",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`USUARIO_YA_ACTIVO` o `SEDE_EN_BAJA` (reasignarlo primero)"},
    },
)
def reactivar_usuario(
    usuario_id: int, servicio: Servicio, actor: Administrador
) -> UsuarioPersonalResponse:
    """Reactiva al usuario; un bibliotecario cuya sede está en baja debe reasignarse antes."""
    return UsuarioPersonalResponse.desde(servicio.reactivar(actor, usuario_id))
