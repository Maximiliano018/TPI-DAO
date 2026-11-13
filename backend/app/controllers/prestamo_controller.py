"""Endpoints de préstamos, la tarea de vencimientos y los parámetros de negocio."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import (
    get_parametro_service,
    get_prestamo_service,
    requiere,
    usuario_actual,
)
from app.dtos.request.prestamo_request import (
    CancelarRequest,
    ParametroRequest,
    PrestamoCrearRequest,
)
from app.dtos.response.prestamo_response import (
    PaginaPrestamosResponse,
    ParametroResponse,
    PrestamoDetalleResponse,
    PrestamoResponse,
    TareaResponse,
)
from app.models.prestamo import TipoPrestamo
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.usuario import Permiso, Usuario
from app.services.parametro_service import ParametroService
from app.services.prestamo_service import PrestamoService

router = APIRouter(prefix="/api/v1", tags=["Préstamos"])

Servicio = Annotated[PrestamoService, Depends(get_prestamo_service)]
Bibliotecario = Annotated[Usuario, Depends(requiere(Permiso.PRESTAMO_REGISTRAR))]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]
Administrador = Annotated[Usuario, Depends(requiere(Permiso.PARAMETROS_ADMINISTRAR))]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso o préstamo de otra sede (`FORBIDDEN`)"}
_404 = {"description": "No existe o no es visible (`PRESTAMO_NO_ENCONTRADO`)"}
_409_TRANSICION = {"description": "No corresponde al estado actual (`TRANSICION_INVALIDA`)"}


@router.post(
    "/prestamos",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un préstamo",
    responses={
        401: _401,
        403: _403,
        404: {"description": "Socio, ejemplar o sede inexistentes"},
        409: {
            "description": "`SOCIO_INHABILITADO`, `SOCIO_EN_BAJA`, `EJEMPLAR_NO_DISPONIBLE`, "
            "`SEDE_EN_BAJA`, `LIMITE_PRESTAMOS` o `LIBRO_REPETIDO`"
        },
        422: {"description": "`EJEMPLAR_FUERA_DE_SEDE_ORIGEN` o datos inválidos"},
    },
)
def registrar_prestamo(
    datos: PrestamoCrearRequest, response: Response, servicio: Servicio, actor: Bibliotecario
) -> PrestamoResponse:
    """Registra la solicitud en nombre del socio y aparta el ejemplar.

    Local si el ejemplar es de la sede del bibliotecario; interbibliotecario si es de otra.
    """
    prestamo = servicio.registrar(
        actor, datos.socio_id, datos.ejemplar_id, datos.sede_destino_id, datos.sede_origen_id
    )
    response.headers["Location"] = f"/api/v1/prestamos/{prestamo.id}"
    return PrestamoResponse.desde(prestamo)


@router.get(
    "/prestamos",
    response_model=PaginaPrestamosResponse,
    summary="Listado de préstamos",
    responses={401: _401, 403: _403},
)
def listar_prestamos(
    servicio: Servicio,
    actor: Autenticado,
    estado: EstadoPrestamoEnum | None = None,
    tipo: TipoPrestamo | None = None,
    socio_id: int | None = None,
    numero: Annotated[str | None, Query(max_length=20)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaPrestamosResponse:
    """El administrador ve todos; el bibliotecario, los de su sede; el socio, los propios."""
    return PaginaPrestamosResponse.desde(
        servicio.listar(actor, estado, tipo, socio_id, numero, page, size)
    )


@router.get(
    "/prestamos/{prestamo_id}",
    response_model=PrestamoDetalleResponse,
    summary="Detalle, historial y remitos de un préstamo",
    responses={401: _401, 404: _404},
)
def obtener_prestamo(
    prestamo_id: int, servicio: Servicio, actor: Autenticado
) -> PrestamoDetalleResponse:
    return PrestamoDetalleResponse.desde_detalle(servicio.detalle(actor, prestamo_id))


@router.post(
    "/prestamos/{prestamo_id}/entregar",
    response_model=PrestamoResponse,
    summary="Entregar al socio",
    responses={
        401: _401,
        403: _403,
        404: _404,
        409: {"description": "`TRANSICION_INVALIDA` o todavía no llegó (`EJEMPLAR_NO_RECIBIDO`)"},
    },
)
def entregar_prestamo(
    prestamo_id: int, servicio: Servicio, actor: Bibliotecario
) -> PrestamoResponse:
    """Empieza el plazo: 14 días el local, 21 el interbibliotecario (desde esta entrega)."""
    return PrestamoResponse.desde(servicio.entregar(actor, prestamo_id))


@router.post(
    "/prestamos/{prestamo_id}/renovar",
    response_model=PrestamoResponse,
    summary="Renovar un préstamo",
    responses={
        401: _401,
        403: _403,
        404: _404,
        409: {"description": "`TRANSICION_INVALIDA` o `RENOVACION_NO_PERMITIDA`"},
    },
)
def renovar_prestamo(
    prestamo_id: int, servicio: Servicio, actor: Bibliotecario
) -> PrestamoResponse:
    """Suma un plazo si no venció, no hay reservas del libro y no llegó al máximo."""
    return PrestamoResponse.desde(servicio.renovar(actor, prestamo_id))


@router.post(
    "/prestamos/{prestamo_id}/cancelar",
    response_model=PrestamoResponse,
    summary="Cancelar antes de la entrega",
    responses={401: _401, 403: _403, 404: _404, 409: _409_TRANSICION},
)
def cancelar_prestamo(
    prestamo_id: int, datos: CancelarRequest, servicio: Servicio, actor: Bibliotecario
) -> PrestamoResponse:
    """Libera el ejemplar; si ya había llegado a destino, genera el remito de retorno."""
    return PrestamoResponse.desde(servicio.cancelar(actor, prestamo_id, datos.motivo))


@router.post(
    "/admin/tareas/detectar-vencidos",
    response_model=TareaResponse,
    summary="Detectar préstamos vencidos",
    tags=["Administración"],
    responses={401: _401, 403: _403},
)
def detectar_vencidos(
    servicio: Servicio, actor: Annotated[Usuario, Depends(requiere(Permiso.TAREAS_EJECUTAR))]
) -> TareaResponse:
    """Marca vencidos e inhabilita a sus socios. También corre sola todos los días."""
    return TareaResponse(tarea="detectar-vencidos", cambios=servicio.detectar_vencidos(actor))


@router.get(
    "/parametros",
    response_model=list[ParametroResponse],
    summary="Parámetros de negocio",
    tags=["Administración"],
    responses={401: _401, 403: _403},
)
def listar_parametros(
    actor: Administrador, servicio: Annotated[ParametroService, Depends(get_parametro_service)]
) -> list[ParametroResponse]:
    return [ParametroResponse.desde(p) for p in servicio.listar(actor)]


@router.put(
    "/parametros/{clave}",
    response_model=ParametroResponse,
    summary="Cambiar un parámetro de negocio",
    tags=["Administración"],
    responses={401: _401, 403: _403, 404: {"description": "La clave no existe"}, 422: {}},
)
def actualizar_parametro(
    clave: str,
    datos: ParametroRequest,
    actor: Administrador,
    servicio: Annotated[ParametroService, Depends(get_parametro_service)],
) -> ParametroResponse:
    """Plazos, límites y montos; rige desde la siguiente operación."""
    return ParametroResponse.desde(servicio.actualizar(actor, clave, datos.valor))
