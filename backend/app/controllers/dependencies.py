"""Raíz de composición: **inyección de dependencias** con ``Depends`` de FastAPI.

Arma, una vez por solicitud, la sesión y la ``UnitOfWork``, el reloj, el verificador de baja de
sede con sus estrategias concretas y cada servicio, y resuelve el usuario actual y sus permisos
(``requiere``). Es el único lugar que conoce las clases concretas; las pruebas las reemplazan con
``app.dependency_overrides``. Ver ``docs/tecnica/05-patrones-de-diseno.md``, sección 8.
"""

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import sesion_por_solicitud
from app.exceptions import TokenInvalido
from app.models.policies.verificacion_baja_sede import VerificadorBajaSede
from app.models.usuario import Permiso, Usuario
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWork
from app.services.auth_service import AuthService
from app.services.catalogo_service import CatalogoService
from app.services.devolucion_service import DevolucionService
from app.services.pago_service import PagoService
from app.services.parametro_service import ParametroService
from app.services.prestamo_service import PrestamoService
from app.services.remito_service import RemitoService
from app.services.reports.reporte_service import ReporteService
from app.services.reserva_service import ReservaService
from app.services.sede_service import SedeService
from app.services.socio_service import SocioService
from app.services.usuario_service import UsuarioService
from app.services.verificadores_baja_sede import (
    VerificadorBibliotecariosAsignados,
    VerificadorEjemplaresEnSede,
    VerificadorEjemplaresPropiosFuera,
    VerificadorPrestamosEnCurso,
    VerificadorRemitosAbiertos,
    VerificadorReservasPendientes,
)
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

    Es el **cliente** de Strategy: el único lugar que conoce las estrategias concretas, las crea
    con su repositorio y se las entrega al contexto (``VerificadorBajaSede``).

    Cada módulo registra el suyo acá cuando se implementa; ver ``TIPOS_PENDIENTES_DE_MODULO``
    en la prueba de contrato.
    """
    return VerificadorBajaSede(
        [
            VerificadorBibliotecariosAsignados(uow.usuarios),
            VerificadorEjemplaresEnSede(uow.ejemplares),
            VerificadorEjemplaresPropiosFuera(uow.ejemplares),
            VerificadorPrestamosEnCurso(uow.prestamos),
            VerificadorRemitosAbiertos(uow.remitos),
            VerificadorReservasPendientes(uow.reservas),
        ]
    )


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


def get_socio_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> SocioService:
    return SocioService(uow, reloj)


def get_catalogo_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> CatalogoService:
    return CatalogoService(uow, reloj)


def get_prestamo_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> PrestamoService:
    return PrestamoService(uow, reloj)


def get_remito_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> RemitoService:
    return RemitoService(uow, reloj)


def get_parametro_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> ParametroService:
    return ParametroService(uow, reloj)


def get_reserva_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> ReservaService:
    return ReservaService(uow, reloj)


def get_devolucion_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> DevolucionService:
    return DevolucionService(uow, reloj)


def get_pago_service(
    uow: UnitOfWork = Depends(get_uow), reloj: Reloj = Depends(get_reloj)
) -> PagoService:
    return PagoService(uow, reloj)


def get_reporte_service(
    sesion: Session = Depends(sesion_por_solicitud), reloj: Reloj = Depends(get_reloj)
) -> ReporteService:
    return ReporteService(sesion, reloj)


def usuario_actual(
    request: Request,
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> Usuario:
    """Usuario autenticado de la solicitud (recargado de la base).

    Deja su id en ``request.state`` para la línea de log de la solicitud
    (``app/utils/registro.py``).
    """
    if credenciales is None:
        raise TokenInvalido("Falta iniciar sesión.")
    usuario = auth.autenticar(credenciales.credentials)
    request.state.usuario_id = usuario.id
    return usuario


def requiere(*permisos: Permiso) -> Callable[[Usuario], Usuario]:
    """Dependencia que exige estar autenticado y tener **todos** los permisos indicados."""

    def _dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        for permiso in permisos:
            usuario.exigir(permiso)
        return usuario

    return _dependencia
