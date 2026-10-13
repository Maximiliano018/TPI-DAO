from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from biblioteca.api.deps import Actor, Hasher, Tokens, Uow
from biblioteca.api.schemas.auth import TokenSalida, UsuarioActualSalida
from biblioteca.application.services.auth import iniciar_sesion

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/login", response_model=TokenSalida)
def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: Uow,
    hasher: Hasher,
    tokens: Tokens,
) -> TokenSalida:
    """Inicia sesión con usuario y contraseña (form-data) y devuelve un JWT."""
    emitido = iniciar_sesion(uow, hasher, tokens, formulario.username, formulario.password)
    return TokenSalida(access_token=emitido.token, expira_en=emitido.expira_en)


@router.get("/yo", response_model=UsuarioActualSalida)
def yo(actor: Actor) -> UsuarioActualSalida:
    """Datos del usuario de la sesión actual."""
    return UsuarioActualSalida(
        id=actor.id,
        username=actor.username,
        nombre_completo=actor.nombre_completo,
        rol=actor.rol,
        sede_id=actor.sede_id,
    )
