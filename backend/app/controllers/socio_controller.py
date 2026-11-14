"""Endpoints de socios: alta, búsqueda, estados, bajas, reactivación, cuenta e historial.

Las respuestas usan un esquema por rol (ver ``app/dtos/response/socio_response.py``).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import get_socio_service, requiere, usuario_actual
from app.dtos.request.socio_request import (
    BajaRequest,
    CuentaSocioRequest,
    MotivoRequest,
    SocioCrearRequest,
    SocioDatosRequest,
    SolicitudReactivacionRequest,
)
from app.dtos.response.socio_response import (
    PaginaHistorialSocioResponse,
    PaginaSociosResponse,
    SocioResponse,
    SocioResumenResponse,
    socio_a_response,
)
from app.models.socio import EstadoSocio, TipoDocumento
from app.models.usuario import Permiso, Usuario
from app.services.socio_service import SocioService

router = APIRouter(prefix="/api/v1/socios", tags=["Socios"])

Servicio = Annotated[SocioService, Depends(get_socio_service)]
Lector = Annotated[Usuario, Depends(requiere(Permiso.SOCIO_LEER))]
Registrador = Annotated[Usuario, Depends(requiere(Permiso.SOCIO_REGISTRAR))]
Administrador = Annotated[Usuario, Depends(requiere(Permiso.SOCIO_ADMINISTRAR))]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]

_ERROR_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_ERROR_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_ERROR_404 = {"description": "El socio no existe o no es visible (`SOCIO_NO_ENCONTRADO`)"}
_ERROR_422 = {"description": "Datos inválidos (`VALIDACION`)"}


@router.post(
    "",
    response_model=SocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de socio",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: {"description": "La sede de alta no existe (`SEDE_NO_ENCONTRADA`)"},
        409: {
            "description": "Documento repetido (`DUPLICADO`, indica si puede reactivarse), "
            "posible duplicado sin confirmar (`POSIBLE_DUPLICADO`) o sede en baja "
            "(`SEDE_EN_BAJA`)"
        },
        422: _ERROR_422,
    },
)
def crear_socio(
    datos: SocioCrearRequest, response: Response, servicio: Servicio, actor: Registrador
) -> SocioResponse:
    """Registra un socio habilitado con un número de socio nuevo.

    El bibliotecario lo registra en su sede; el administrador indica `sede_alta_id`.
    """
    socio = servicio.crear(
        actor, datos.a_datos(), datos.sede_alta_id, datos.confirmar_posible_duplicado
    )
    response.headers["Location"] = f"/api/v1/socios/{socio.id}"
    return socio_a_response(socio, actor)


@router.get(
    "",
    response_model=PaginaSociosResponse,
    summary="Búsqueda de socios",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def listar_socios(
    servicio: Servicio,
    actor: Lector,
    q: Annotated[
        str | None, Query(max_length=100, description="Número de socio, documento o nombre")
    ] = None,
    documento: Annotated[str | None, Query(max_length=30)] = None,
    estado: EstadoSocio | None = None,
    solicitud_pendiente: Annotated[
        bool, Query(description="Solo socios con una solicitud de reactivación pendiente")
    ] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaSociosResponse:
    """Busca por número de socio, documento o apellido; ordena por apellido y nombre."""
    pagina = servicio.listar(actor, q, documento, estado, page, size, solicitud_pendiente)
    return PaginaSociosResponse.desde(pagina)


@router.get(
    "/posibles-duplicados",
    response_model=list[SocioResumenResponse],
    summary="Búsqueda previa al alta",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def posibles_duplicados(
    servicio: Servicio,
    actor: Registrador,
    tipo_documento: TipoDocumento | None = None,
    nro_documento: Annotated[str | None, Query(max_length=30)] = None,
    nombre: Annotated[str | None, Query(max_length=100)] = None,
    apellido: Annotated[str | None, Query(max_length=100)] = None,
    fecha_nacimiento: date | None = None,
) -> list[SocioResumenResponse]:
    """Socios con el mismo documento, o con el mismo nombre, apellido y fecha de nacimiento."""
    encontrados = servicio.posibles_duplicados(
        actor, tipo_documento, nro_documento, nombre, apellido, fecha_nacimiento
    )
    return [SocioResumenResponse.desde(s) for s in encontrados]


@router.get(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Ficha y situación de un socio",
    responses={401: _ERROR_401, 404: _ERROR_404},
)
def obtener_socio(socio_id: int, servicio: Servicio, actor: Autenticado) -> SocioResponse:
    """Datos, estado y situación (préstamos, multas y reservas). Un socio solo ve la propia.

    El esquema depende del rol: el socio no ve la auditoría ni el id de su cuenta.
    """
    ficha = servicio.ficha(actor, socio_id)
    return socio_a_response(ficha.socio, actor, situacion=ficha.situacion)


@router.get(
    "/{socio_id}/historial",
    response_model=PaginaHistorialSocioResponse,
    summary="Historial del socio",
    responses={401: _ERROR_401, 404: _ERROR_404},
)
def historial_socio(
    socio_id: int,
    servicio: Servicio,
    actor: Autenticado,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaHistorialSocioResponse:
    """Eventos del socio, del más reciente al más antiguo. El socio ve el propio, sin la
    identidad del personal."""
    return PaginaHistorialSocioResponse.desde(
        servicio.historial(actor, socio_id, page, size), actor
    )


@router.put(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Modificar los datos de un socio",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "Documento de otro socio (`DUPLICADO`) o socio en baja"},
        422: _ERROR_422,
    },
)
def modificar_socio(
    socio_id: int, datos: SocioDatosRequest, servicio: Servicio, actor: Registrador
) -> SocioResponse:
    """Reemplaza los datos personales. El socio pide la corrección al personal."""
    return socio_a_response(servicio.modificar(actor, socio_id, datos.a_datos()), actor)


@router.post(
    "/{socio_id}/inhabilitar",
    response_model=SocioResponse,
    summary="Inhabilitación administrativa",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`SOCIO_YA_INHABILITADO` o `SOCIO_EN_BAJA`"},
        422: _ERROR_422,
    },
)
def inhabilitar_socio(
    socio_id: int, datos: MotivoRequest, servicio: Servicio, actor: Administrador
) -> SocioResponse:
    """Inhabilita al socio por decisión administrativa; solo el administrador la levanta."""
    return socio_a_response(servicio.inhabilitar(actor, socio_id, datos.motivo), actor)


@router.post(
    "/{socio_id}/rehabilitar",
    response_model=SocioResponse,
    summary="Rehabilitar a un socio",
    responses={
        401: _ERROR_401,
        403: {"description": "Un bibliotecario no levanta una inhabilitación administrativa"},
        404: _ERROR_404,
        409: {
            "description": "Siguen vigentes causas automáticas (`SOCIO_CON_CAUSAS_VIGENTES`), "
            "ya estaba habilitado (`SOCIO_YA_HABILITADO`) o está en baja (`SOCIO_EN_BAJA`)"
        },
    },
)
def rehabilitar_socio(socio_id: int, servicio: Servicio, actor: Registrador) -> SocioResponse:
    """Rehabilita si no hay causas vigentes. El administrador levanta la causa administrativa."""
    return socio_a_response(servicio.rehabilitar(actor, socio_id), actor)


@router.post(
    "/{socio_id}/baja",
    response_model=SocioResponse,
    summary="Baja lógica de un socio",
    responses={
        401: _ERROR_401,
        403: {
            "description": "Un bibliotecario intenta una baja administrativa o por fallecimiento"
        },
        404: _ERROR_404,
        409: {
            "description": "Préstamos en curso o multas pendientes "
            "(`SOCIO_CON_ACTIVIDAD_PENDIENTE`) o ya en baja (`SOCIO_YA_EN_BAJA`)"
        },
        422: _ERROR_422,
    },
)
def dar_de_baja_socio(
    socio_id: int, datos: BajaRequest, servicio: Servicio, actor: Registrador
) -> SocioResponse:
    """Baja lógica con tipo y motivo; conserva el historial.

    `A_PEDIDO` la registra el personal; `ADMINISTRATIVA` y `FALLECIMIENTO`, solo el
    administrador (la de fallecimiento desactiva la cuenta y no se reactiva). Cancela las
    reservas activas del socio e informa cuántas en `reservas_canceladas`.
    """
    baja = servicio.dar_de_baja(actor, socio_id, datos.tipo, datos.motivo)
    return socio_a_response(baja.socio, actor, reservas_canceladas=baja.reservas_canceladas)


@router.post(
    "/{socio_id}/reactivar",
    response_model=SocioResponse,
    summary="Reactivar a un socio dado de baja (en mostrador)",
    responses={
        401: _ERROR_401,
        403: {"description": "Un bibliotecario intenta reactivar una baja administrativa"},
        404: _ERROR_404,
        409: {"description": "`SOCIO_YA_ACTIVO` o `SOCIO_NO_REACTIVABLE` (fallecimiento)"},
    },
)
def reactivar_socio(socio_id: int, servicio: Servicio, actor: Registrador) -> SocioResponse:
    """Vuelve a dar de alta a un socio dado de baja, en lugar de registrarlo de nuevo.

    Vuelve inhabilitado si tenía una inhabilitación administrativa.
    """
    return socio_a_response(servicio.reactivar(actor, socio_id), actor)


@router.post(
    "/{socio_id}/solicitud-reactivacion",
    response_model=SocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="El socio pide su reactivación",
    responses={
        401: _ERROR_401,
        404: _ERROR_404,
        409: {
            "description": "`SOCIO_YA_ACTIVO`, `SOCIO_NO_REACTIVABLE` o `SOLICITUD_YA_PENDIENTE`"
        },
        422: _ERROR_422,
    },
)
def solicitar_reactivacion(
    socio_id: int, datos: SolicitudReactivacionRequest, servicio: Servicio, actor: Autenticado
) -> SocioResponse:
    """Solo el propio socio dado de baja, desde su cuenta. El personal la aprueba o rechaza."""
    return socio_a_response(servicio.solicitar_reactivacion(actor, socio_id, datos.mensaje), actor)


@router.post(
    "/{socio_id}/solicitud-reactivacion/aprobar",
    response_model=SocioResponse,
    summary="Aprobar la solicitud de reactivación",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`SIN_SOLICITUD_PENDIENTE`"},
    },
)
def aprobar_solicitud(socio_id: int, servicio: Servicio, actor: Registrador) -> SocioResponse:
    """Reactiva al socio; la baja administrativa la resuelve solo el administrador."""
    return socio_a_response(servicio.aprobar_solicitud(actor, socio_id), actor)


@router.post(
    "/{socio_id}/solicitud-reactivacion/rechazar",
    response_model=SocioResponse,
    summary="Rechazar la solicitud de reactivación",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`SIN_SOLICITUD_PENDIENTE`"},
        422: _ERROR_422,
    },
)
def rechazar_solicitud(
    socio_id: int, datos: MotivoRequest, servicio: Servicio, actor: Registrador
) -> SocioResponse:
    """Rechaza con un motivo (5 a 300 caracteres); el socio sigue en baja."""
    return socio_a_response(servicio.rechazar_solicitud(actor, socio_id, datos.motivo), actor)


@router.post(
    "/{socio_id}/cuenta",
    response_model=SocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear la cuenta de acceso del socio",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`SOCIO_CON_CUENTA`, usuario repetido (`DUPLICADO`) o en baja"},
        422: _ERROR_422,
    },
)
def crear_cuenta_socio(
    socio_id: int, datos: CuentaSocioRequest, servicio: Servicio, actor: Registrador
) -> SocioResponse:
    """Crea el usuario (rol `SOCIO`) con el que el socio consulta y reserva."""
    return socio_a_response(
        servicio.crear_cuenta(actor, socio_id, datos.username, datos.password), actor
    )
