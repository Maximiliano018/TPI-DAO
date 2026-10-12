from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from biblioteca.api.deps import Actor, get_auth_service
from biblioteca.api.schemas.auth import TokenSalida, UsuarioActualSalida
from biblioteca.application.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/login")
def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenSalida:
    """Inicia sesión con usuario y contraseña (form-data) y devuelve un JWT."""
    emitido = auth.login(formulario.username, formulario.password)
    return TokenSalida(access_token=emitido.token, expira_en=emitido.expira_en)


@router.get("/yo")
def yo(actor: Actor) -> UsuarioActualSalida:
    """Datos del usuario de la sesión actual."""
    return UsuarioActualSalida(
        id=actor.id,
        username=actor.username,
        nombre_completo=actor.nombre_completo,
        rol=actor.rol,
        sede_id=actor.sede_id,
    )
