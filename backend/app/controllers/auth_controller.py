from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.controllers.dependencies import get_auth_service, usuario_actual
from app.dtos.request.auth_request import LoginRequest
from app.dtos.response.auth_response import LoginResponse, UsuarioSesionResponse
from app.models.usuario import Usuario
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

_ERRORES = {
    401: {
        "description": "Credenciales o token inválidos (`CREDENCIALES_INVALIDAS`, `TOKEN_INVALIDO`)"
    },
    422: {"description": "Faltan campos (`VALIDACION`)"},
}


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión",
    responses={401: _ERRORES[401], 422: _ERRORES[422]},
)
def login(
    datos: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """Valida usuario y contraseña y devuelve un token de acceso (Bearer)."""
    resultado = auth.login(datos.username, datos.password)
    usuario = resultado.usuario
    return LoginResponse(
        access_token=resultado.token,
        expires_in=resultado.expira_en_segundos,
        usuario=UsuarioSesionResponse.desde(usuario, settings.es_solo_lectura(usuario.username)),
    )


@router.get(
    "/me",
    response_model=UsuarioSesionResponse,
    summary="Usuario autenticado",
    responses={401: _ERRORES[401]},
)
def yo(
    usuario: Usuario = Depends(usuario_actual), settings: Settings = Depends(get_settings)
) -> UsuarioSesionResponse:
    """Devuelve el usuario de la sesión con su sede, sus permisos y si es de solo lectura."""
    return UsuarioSesionResponse.desde(usuario, settings.es_solo_lectura(usuario.username))
