"""Composición de dependencias de la API.

Cada request recibe su Unidad de Trabajo y sus servicios. Los tests reemplazan
`get_uow`, `get_reloj` o `get_tokens` con `app.dependency_overrides`.
"""

import logging
import secrets
from collections.abc import Callable, Iterator
from datetime import timedelta
from functools import cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.autorizacion import exigir_rol
from biblioteca.application.security.puertos import HasherContrasenas, ServicioTokens
from biblioteca.application.services.auth_service import AuthService
from biblioteca.application.services.sede_service import SedeService
from biblioteca.application.unit_of_work import UnitOfWork
from biblioteca.config import settings
from biblioteca.domain.clock import Reloj
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import NoAutenticado
from biblioteca.infrastructure.db.session import SessionLocal
from biblioteca.infrastructure.reloj import RelojSistema
from biblioteca.infrastructure.security import HasherArgon2, TokensJwt
from biblioteca.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


def get_db() -> Iterator[Session]:
    """Sesión directa, solo para chequeos técnicos (health). Los casos de uso usan la UoW."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------- Infraestructura


@cache
def get_reloj() -> Reloj:
    return RelojSistema(settings.zona_horaria)


@cache
def get_hasher() -> HasherContrasenas:
    return HasherArgon2()


@cache
def _secreto_jwt() -> str:
    if settings.jwt_secreto:
        return settings.jwt_secreto
    logger.warning(
        "BIBLIOTECA_JWT_SECRETO no está definido: se usa un secreto temporal "
        "y las sesiones se pierden al reiniciar la API."
    )
    return secrets.token_urlsafe(32)


def get_tokens(reloj: Annotated[Reloj, Depends(get_reloj)]) -> ServicioTokens:
    return TokensJwt(_secreto_jwt(), timedelta(minutes=settings.jwt_expira_minutos), reloj)


def get_uow() -> UnitOfWork:
    return SqlAlchemyUnitOfWork(SessionLocal)


# --------------------------------------------------------------------------- Seguridad

oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False)


def get_auth_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    hasher: Annotated[HasherContrasenas, Depends(get_hasher)],
    tokens: Annotated[ServicioTokens, Depends(get_tokens)],
) -> AuthService:
    return AuthService(uow, hasher, tokens)


def usuario_actual(
    token: Annotated[str | None, Depends(oauth2)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UsuarioActual:
    if token is None:
        raise NoAutenticado("Debe iniciar sesión")
    return auth.usuario_actual(token)


def requiere_rol(*roles: Rol) -> Callable[[UsuarioActual], UsuarioActual]:
    """Dependencia que exige uno de los roles. Uso: `Depends(requiere_rol(Rol.ADMIN))`."""

    def dependencia(
        actor: Annotated[UsuarioActual, Depends(usuario_actual)],
    ) -> UsuarioActual:
        exigir_rol(actor, *roles)
        return actor

    return dependencia


Actor = Annotated[UsuarioActual, Depends(usuario_actual)]
Admin = Annotated[UsuarioActual, Depends(requiere_rol(Rol.ADMIN))]

# ---------------------------------------------------------------------------- Servicios


def get_sede_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    reloj: Annotated[Reloj, Depends(get_reloj)],
) -> SedeService:
    return SedeService(uow, reloj)
