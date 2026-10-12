"""Dependencias de la API.

Los tests reemplazan `get_db`, `get_reloj`, `get_ahora` o `get_hasher` con
`app.dependency_overrides`.
"""

import logging
import secrets
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.autorizacion import exigir_rol
from biblioteca.application.security.puertos import HasherContrasenas, ServicioTokens
from biblioteca.application.services.auth import resolver_usuario
from biblioteca.config import settings
from biblioteca.domain.clock import Reloj
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import NoAutenticado
from biblioteca.infrastructure.db.session import SessionLocal
from biblioteca.infrastructure.reloj import RelojSistema
from biblioteca.infrastructure.repositories.unidad_de_trabajo import SqlUnidadDeTrabajo
from biblioteca.infrastructure.security import HasherArgon2, TokensJwt

logger = logging.getLogger(__name__)


def get_db() -> Iterator[Session]:
    """Abre una sesión por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@cache
def get_reloj() -> Reloj:
    """Única fuente de "ahora" y "hoy" (en la zona horaria de la red)."""
    return RelojSistema(settings.zona_horaria)


def get_ahora(reloj: Annotated[Reloj, Depends(get_reloj)]) -> datetime:
    """Instante actual en UTC. Es una dependencia para poder fijarlo en los tests."""
    return reloj.ahora()


@dataclass(frozen=True)
class Paginacion:
    limit: int
    offset: int


def get_paginacion(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginacion:
    return Paginacion(limit, offset)


Db = Annotated[Session, Depends(get_db)]
Ahora = Annotated[datetime, Depends(get_ahora)]
Pagina = Annotated[Paginacion, Depends(get_paginacion)]


def get_uow(db: Db) -> SqlUnidadDeTrabajo:
    """Unidad de trabajo del request, sobre la misma sesión."""
    return SqlUnidadDeTrabajo(db)


Uow = Annotated[SqlUnidadDeTrabajo, Depends(get_uow)]

# --------------------------------------------------------------------------- Seguridad


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


Hasher = Annotated[HasherContrasenas, Depends(get_hasher)]
Tokens = Annotated[ServicioTokens, Depends(get_tokens)]

_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False)


def usuario_actual(
    token: Annotated[str | None, Depends(_oauth2)], uow: Uow, tokens: Tokens
) -> UsuarioActual:
    if token is None:
        raise NoAutenticado("Debe iniciar sesión")
    return resolver_usuario(uow, tokens, token)


def requiere_rol(*roles: Rol) -> Callable[[UsuarioActual], UsuarioActual]:
    """Dependencia que exige uno de los roles. Uso: `Depends(requiere_rol(Rol.ADMIN))`."""

    def dependencia(actor: Annotated[UsuarioActual, Depends(usuario_actual)]) -> UsuarioActual:
        exigir_rol(actor, *roles)
        return actor

    return dependencia


Actor = Annotated[UsuarioActual, Depends(usuario_actual)]
Admin = Annotated[UsuarioActual, Depends(requiere_rol(Rol.ADMIN))]
