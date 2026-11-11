"""Dependencias compartidas de los controladores: sesión, usuario actual y permisos."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import sesion_por_solicitud
from app.exceptions import TokenInvalido
from app.models.policies.verificacion_baja_sede import VerificadorBajaSede
from app.models.usuario import Permiso, Usuario
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWork
from app.services.auth_service import AuthService
from app.services.sede_service import SedeService
from app.services.usuario_service import UsuarioService
from app.services.verificadores_baja_sede import VerificadorBibliotecariosAsignados
from app.utils.reloj import Reloj, RelojSistema

_esquema_bearer = HTTPBearer(auto_error=False)


def get_reloj(settings: Settings = Depends(get_settings)) -> Reloj:
    return RelojSistema(settings.tz_negocio)


def get_uow(sesion: Session = Depends(sesion_por_solicitud)) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(sesion)


def get_auth_service(
    uow: UnitOfWork = Depends(get_uow),
    reloj: Reloj = Depends(get_reloj),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(uow, reloj, settings)


def get_verificador_baja_sede(uow: UnitOfWork = Depends(get_uow)) -> VerificadorBajaSede:
    """Compuesto de verificadores de impedimentos de baja.

    Cada módulo registra el suyo acá cuando se implementa; ver ``TIPOS_PENDIENTES_DE_MODULO``
    en la prueba de contrato.
    """
    return VerificadorBajaSede([VerificadorBibliotecariosAsignados(uow.usuarios)])


def get_sede_service(
    uow: UnitOfWork = Depends(get_uow),
    reloj: Reloj = Depends(get_reloj),
    verificador: VerificadorBajaSede = Depends(get_verificador_baja_sede),
) -> SedeService:
    return SedeService(uow, reloj, verificador)


def get_usuario_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> UsuarioService:
    return UsuarioService(uow, reloj)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> Usuario:
    """Usuario autenticado de la solicitud (recargado de la base)."""
    if credenciales is None:
        raise TokenInvalido("Falta iniciar sesión.")
    return auth.autenticar(credenciales.credentials)


def requiere(*permisos: Permiso) -> Callable[[Usuario], Usuario]:
    """Dependencia que exige estar autenticado y tener **todos** los permisos indicados."""

    def _dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        for permiso in permisos:
            usuario.exigir(permiso)
        return usuario

    return _dependencia
