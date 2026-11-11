"""Endpoints de sedes: administración, consulta según rol, excepciones de horario e historial."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import get_sede_service, requiere
from app.dtos.request.sede_request import (
    ExcepcionHorarioRequest,
    SedeBajaRequest,
    SedeCrearRequest,
    SedeModificarRequest,
    SedeReactivarRequest,
)
from app.dtos.response.sede_response import (
    EventoSedeResponse,
    ExcepcionHorarioResponse,
    LocalidadResponse,
    PaginaHistorialResponse,
    PaginaSedesResponse,
    ProvinciaResponse,
    SedeAdminResponse,
    SedeResponse,
    SedesResumenResponse,
    pagina_de_sedes,
    sede_a_response,
)
from app.models.sede import TipoEventoSede
from app.models.usuario import Permiso, Usuario
from app.repositories.interfaces.sede_repository import FiltroEstado, FiltroHistorial, OrdenSedes
from app.services.sede_service import SedeService

router = APIRouter(prefix="/api/v1", tags=["Sedes"])

_ERROR_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_ERROR_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_ERROR_404 = {"description": "La sede no existe o no está disponible (`SEDE_NO_ENCONTRADA`)"}
_ERROR_409_VERSION = {
    "description": "La sede cambió o su estado no lo permite (`CONFLICTO_DE_VERSION`)"
}
_ERROR_422 = {
    "description": "Datos inválidos (`VALIDACION`, `HORARIO_INVALIDO`, `LOCALIDAD_INVALIDA`)"
}

Servicio = Annotated[SedeService, Depends(get_sede_service)]
Lector = Annotated[Usuario, Depends(requiere(Permiso.SEDE_LEER_PUBLICO))]
Administrador = Annotated[Usuario, Depends(requiere(Permiso.SEDE_ADMINISTRAR))]
Pagina = Annotated[int, Query(ge=1, description="Número de página, desde 1")]
Tamanio = Annotated[int, Query(ge=1, le=100, description="Resultados por página")]


@router.post(
    "/sedes",
    response_model=SedeAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alta de sede",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        409: {
            "description": (
                "Duplicados (`SEDE_CODIGO_DUPLICADO`, `SEDE_NOMBRE_DUPLICADO`) o dirección "
                "repetida sin confirmar (`DIRECCION_DUPLICADA`)"
            )
        },
        422: _ERROR_422,
    },
)
def crear_sede(
    datos: SedeCrearRequest, response: Response, servicio: Servicio, actor: Administrador
) -> SedeAdminResponse:
    """Crea una sede activa. Solo el administrador.

    Si ya hay una sede en la misma dirección responde `409 DIRECCION_DUPLICADA`; para aceptarla
    se reenvía el mismo cuerpo con `confirmar_direccion_duplicada: true`.
    """
    vista = servicio.crear(
        actor, datos.codigo, datos.a_datos(), datos.confirmar_direccion_duplicada
    )
    response.headers["Location"] = f"/api/v1/sedes/{vista.sede.id}"
    respuesta = sede_a_response(vista, actor)
    assert isinstance(respuesta, SedeAdminResponse)
    return respuesta


@router.get(
    "/sedes",
    response_model=PaginaSedesResponse,
    summary="Listado paginado de sedes",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def listar_sedes(
    servicio: Servicio,
    usuario: Lector,
    estado: Annotated[
        FiltroEstado | None, Query(description="Por defecto: TODAS (admin), ACTIVA")
    ] = None,
    q: Annotated[
        str | None, Query(max_length=100, description="Texto en nombre, código, calle o localidad")
    ] = None,
    localidad_id: int | None = None,
    orden: OrdenSedes = OrdenSedes.NOMBRE,
    page: Pagina = 1,
    size: Tamanio = 20,
) -> PaginaSedesResponse:
    """Lista sedes. El esquema de cada elemento depende del rol; el socio solo ve las activas."""
    pagina = servicio.listar(usuario, estado, q, localidad_id, orden, page, size)
    return pagina_de_sedes(pagina, usuario)


@router.get(
    "/sedes/resumen",
    response_model=SedesResumenResponse,
    summary="Cantidad de sedes por estado",
    responses={401: _ERROR_401, 403: _ERROR_403},
)
def resumen_sedes(servicio: Servicio, usuario: Administrador) -> SedesResumenResponse:
    """Totales de sedes activas y en baja (inicio del administrador)."""
    return SedesResumenResponse(**servicio.resumen(usuario))


@router.get(
    "/sedes/{sede_id}",
    response_model=SedeResponse,
    summary="Detalle de una sede",
    responses={401: _ERROR_401, 403: _ERROR_403, 404: _ERROR_404},
)
def obtener_sede(sede_id: int, servicio: Servicio, usuario: Lector) -> SedeResponse:
    """Detalle con los campos que corresponden al rol. Un socio no ve sedes en baja (404)."""
    return sede_a_response(servicio.obtener(usuario, sede_id), usuario)


@router.put(
    "/sedes/{sede_id}",
    response_model=SedeAdminResponse,
    summary="Modificar una sede",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: _ERROR_409_VERSION,
        422: _ERROR_422,
    },
)
def modificar_sede(
    sede_id: int, datos: SedeModificarRequest, servicio: Servicio, actor: Administrador
) -> SedeAdminResponse:
    """Reemplaza los datos y el horario semanal. Exige la `version` leída (409 si cambió)."""
    vista = servicio.modificar(
        actor,
        sede_id,
        datos.version,
        datos.a_datos(),
        datos.codigo,
        datos.confirmar_direccion_duplicada,
    )
    respuesta = sede_a_response(vista, actor)
    assert isinstance(respuesta, SedeAdminResponse)
    return respuesta


@router.post(
    "/sedes/{sede_id}/baja",
    response_model=SedeAdminResponse,
    summary="Dar de baja una sede",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {
            "description": (
                "`SEDE_CON_ACTIVIDAD_PENDIENTE` (con el detalle por tipo), `SEDE_YA_EN_BAJA` "
                "o `CONFLICTO_DE_VERSION`"
            )
        },
        422: _ERROR_422,
    },
)
def dar_de_baja_sede(
    sede_id: int, datos: SedeBajaRequest, servicio: Servicio, actor: Administrador
) -> SedeAdminResponse:
    """Baja con motivo. Se rechaza, sin cambiar nada, si la sede tiene actividad pendiente."""
    vista = servicio.dar_de_baja(actor, sede_id, datos.version, datos.motivo)
    respuesta = sede_a_response(vista, actor)
    assert isinstance(respuesta, SedeAdminResponse)
    return respuesta


@router.post(
    "/sedes/{sede_id}/reactivar",
    response_model=SedeAdminResponse,
    summary="Reactivar una sede",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`SEDE_YA_ACTIVA` o `CONFLICTO_DE_VERSION`"},
    },
)
def reactivar_sede(
    sede_id: int, datos: SedeReactivarRequest, servicio: Servicio, actor: Administrador
) -> SedeAdminResponse:
    """Vuelve a activar una sede en baja sin condiciones; limpia los datos de la baja."""
    vista = servicio.reactivar(actor, sede_id, datos.version)
    respuesta = sede_a_response(vista, actor)
    assert isinstance(respuesta, SedeAdminResponse)
    return respuesta


@router.get(
    "/sedes/{sede_id}/excepciones-horario",
    response_model=list[ExcepcionHorarioResponse],
    summary="Excepciones de horario de una sede",
    responses={401: _ERROR_401, 403: _ERROR_403, 404: _ERROR_404},
)
def listar_excepciones(
    sede_id: int,
    servicio: Servicio,
    usuario: Lector,
    incluir_pasadas: Annotated[bool, Query(description="Solo administrador")] = False,
) -> list[ExcepcionHorarioResponse]:
    """Cierres de hoy y futuros; el administrador puede pedir también los pasados."""
    excepciones = servicio.excepciones(usuario, sede_id, incluir_pasadas)
    return [ExcepcionHorarioResponse.desde(e) for e in excepciones]


@router.post(
    "/sedes/{sede_id}/excepciones-horario",
    response_model=list[ExcepcionHorarioResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un cierre por fecha o rango",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: _ERROR_404,
        409: {"description": "`EXCEPCION_HORARIO_SUPERPUESTA` o `SEDE_EN_BAJA`"},
        422: {"description": "`EXCEPCION_HORARIO_INVALIDA`"},
    },
)
def agregar_excepciones(
    sede_id: int, datos: ExcepcionHorarioRequest, servicio: Servicio, actor: Administrador
) -> list[ExcepcionHorarioResponse]:
    """Crea una excepción por día del rango (todo o nada). No cambia la versión de la sede."""
    creadas = servicio.agregar_excepciones(actor, sede_id, datos.a_datos())
    return [ExcepcionHorarioResponse.desde(e) for e in creadas]


@router.delete(
    "/sedes/{sede_id}/excepciones-horario/{excepcion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar un cierre de hoy o futuro",
    responses={
        401: _ERROR_401,
        403: _ERROR_403,
        404: {"description": "`SEDE_NO_ENCONTRADA` o `EXCEPCION_HORARIO_NO_ENCONTRADA`"},
        409: {"description": "`SEDE_EN_BAJA`"},
        422: {"description": "`EXCEPCION_HORARIO_INVALIDA` (fecha pasada)"},
    },
)
def quitar_excepcion(
    sede_id: int, excepcion_id: int, servicio: Servicio, actor: Administrador
) -> Response:
    """Elimina un cierre vigente; los pasados se conservan como historial."""
    servicio.quitar_excepcion(actor, sede_id, excepcion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sedes/{sede_id}/historial",
    response_model=PaginaHistorialResponse,
    summary="Historial de la sede",
    responses={401: _ERROR_401, 403: _ERROR_403, 404: _ERROR_404},
)
def historial_sede(
    sede_id: int,
    servicio: Servicio,
    usuario: Annotated[Usuario, Depends(requiere(Permiso.SEDE_VER_HISTORIAL))],
    tipo_evento: TipoEventoSede | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: Pagina = 1,
    size: Tamanio = 20,
) -> PaginaHistorialResponse:
    """Eventos de auditoría del más reciente al más antiguo (solo administrador)."""
    pagina = servicio.historial(
        usuario, sede_id, FiltroHistorial(tipo_evento, desde, hasta), page, size
    )
    return PaginaHistorialResponse(
        items=[EventoSedeResponse.desde(e) for e in pagina.items],
        total=pagina.total,
        page=pagina.page,
        size=pagina.size,
    )


@router.get(
    "/provincias",
    response_model=list[ProvinciaResponse],
    summary="Catálogo de provincias",
    responses={401: _ERROR_401},
)
def listar_provincias(servicio: Servicio, _: Lector) -> list[ProvinciaResponse]:
    """Provincias habilitadas (lista cerrada)."""
    return [ProvinciaResponse(id=i, nombre=n) for i, n in servicio.provincias()]


@router.get(
    "/localidades",
    response_model=list[LocalidadResponse],
    summary="Catálogo de localidades",
    responses={401: _ERROR_401},
)
def listar_localidades(
    servicio: Servicio,
    _: Lector,
    provincia_id: int | None = None,
    q: Annotated[
        str | None, Query(max_length=100, description="Sin distinguir mayúsculas ni tildes")
    ] = None,
) -> list[LocalidadResponse]:
    """Localidades habilitadas, ordenadas por nombre."""
    return [LocalidadResponse.desde(loc) for loc in servicio.localidades(provincia_id, q)]
