"""Endpoints de devoluciones y multas."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.controllers.dependencies import get_devolucion_service, requiere, usuario_actual
from app.dtos.request.devolucion_request import DevolucionRequest
from app.dtos.response.devolucion_response import PaginaMultasResponse
from app.dtos.response.resultado_devolucion_response import ResultadoDevolucionResponse
from app.models.devolucion import EstadoMulta
from app.models.usuario import Permiso, Usuario
from app.services.devolucion_service import DevolucionService

router = APIRouter(prefix="/api/v1", tags=["Devoluciones y multas"])

Servicio = Annotated[DevolucionService, Depends(get_devolucion_service)]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]
Bibliotecario = Annotated[Usuario, Depends(requiere(Permiso.DEVOLUCION_REGISTRAR))]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso o préstamo de otra sede (`FORBIDDEN`)"}


@router.post(
    "/prestamos/{prestamo_id}/devolucion",
    response_model=ResultadoDevolucionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar la devolución",
    responses={
        401: _401,
        403: _403,
        404: {"description": "`PRESTAMO_NO_ENCONTRADO`"},
        409: {"description": "El préstamo no está activo ni vencido (`TRANSICION_INVALIDA`)"},
        422: {
            "description": "Fecha futura o anterior a la entrega, observaciones faltantes, o "
            "fecha anterior a hoy sin `motivo_fecha`"
        },
    },
)
def registrar_devolucion(
    prestamo_id: int, datos: DevolucionRequest, servicio: Servicio, actor: Bibliotecario
) -> ResultadoDevolucionResponse:
    """Cierra el préstamo en la sede destino; genera la multa si hay atraso.

    Según el estado recibido, el ejemplar queda disponible (o asignado a una reserva), vuelve a
    su sede con un remito de retorno, pasa a revisión o se da de baja.
    """
    resultado = servicio.registrar(
        actor,
        prestamo_id,
        datos.estado_fisico,
        datos.observaciones,
        datos.fecha_hora,
        datos.motivo_fecha,
    )
    return ResultadoDevolucionResponse.desde(resultado, actor)


@router.get(
    "/multas",
    response_model=PaginaMultasResponse,
    summary="Listado de multas",
    responses={401: _401, 403: _403},
)
def listar_multas(
    servicio: Servicio,
    actor: Autenticado,
    socio_id: int | None = None,
    estado: EstadoMulta | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaMultasResponse:
    """El personal ve las de la red (filtrables por socio); el socio, solo las propias."""
    return PaginaMultasResponse.desde(
        servicio.listar_multas(actor, socio_id, estado, page, size), actor
    )
