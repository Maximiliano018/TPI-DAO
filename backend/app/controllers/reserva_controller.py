"""Endpoints de reservas."""

from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, Query, Response, status

from app.controllers.dependencies import get_reserva_service, requiere, usuario_actual
from app.dtos.request.reserva_request import CancelarReservaRequest, ReservaRequest
from app.dtos.response.prestamo_response import (
    PrestamoResponse,
    TareaResponse,
    prestamo_a_response,
)
from app.dtos.response.reserva_response import (
    PaginaReservasResponse,
    ReservaDetalleResponse,
    ReservaResponse,
    detalle_a_response,
    reserva_a_response,
)
from app.models.states.reserva import EstadoReservaEnum
from app.models.usuario import Permiso, Usuario
from app.services.reserva_service import ReservaService

router = APIRouter(prefix="/api/v1", tags=["Reservas"])

Servicio = Annotated[ReservaService, Depends(get_reserva_service)]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_404 = {"description": "No existe o no es visible (`RESERVA_NO_ENCONTRADA`)"}


@router.post(
    "/reservas",
    response_model=ReservaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar un libro",
    responses={
        401: _401,
        403: {"description": "Sin permiso, o un socio que indica otro `socio_id` (`FORBIDDEN`)"},
        404: {"description": "Socio, libro o sede inexistentes"},
        409: {
            "description": "`HAY_EJEMPLARES_DISPONIBLES` (en la sede de retiro, o en otra sede: "
            "corresponde un préstamo entre sedes), `SOCIO_INHABILITADO`, `SEDE_EN_BAJA`, "
            "`RESERVA_DUPLICADA`, `LIMITE_RESERVAS` o `LIBRO_SIN_EJEMPLARES`"
        },
    },
)
def reservar(
    datos: ReservaRequest, response: Response, servicio: Servicio, actor: Autenticado
) -> ReservaResponse:
    """Entra a la cola del libro (FIFO) para retirarlo en la sede elegida."""
    reserva = servicio.reservar(actor, datos.libro_id, datos.sede_retiro_id, datos.socio_id)
    response.headers["Location"] = f"/api/v1/reservas/{reserva.id}"
    return reserva_a_response(reserva, actor)


@router.get(
    "/reservas",
    response_model=PaginaReservasResponse,
    summary="Listado de reservas",
    responses={401: _401, 403: _403},
)
def listar_reservas(
    servicio: Servicio,
    actor: Autenticado,
    socio_id: int | None = None,
    libro_id: int | None = None,
    sede_retiro_id: int | None = None,
    estado: EstadoReservaEnum | None = None,
    orden: Literal["recientes", "cola"] = "recientes",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaReservasResponse:
    """El socio ve las propias con su posición en la cola; el personal, todas.

    ``orden=cola`` ordena por fecha de reserva (FIFO): con ``libro_id`` y ``estado=PENDIENTE``
    es la cola de espera del libro.
    """
    pagina = servicio.listar(
        actor,
        socio_id,
        libro_id,
        estado,
        page,
        size,
        sede_retiro_id=sede_retiro_id,
        orden_cola=orden == "cola",
    )
    return PaginaReservasResponse.desde(pagina, actor)


@router.get(
    "/reservas/{reserva_id}",
    response_model=ReservaDetalleResponse,
    summary="Detalle, posición en la cola e historial",
    responses={401: _401, 404: _404},
)
def obtener_reserva(
    reserva_id: int, servicio: Servicio, actor: Autenticado
) -> ReservaDetalleResponse:
    """Cada cambio de estado con fecha, autor y observación. Lo automático figura como Sistema."""
    return detalle_a_response(servicio.detalle(actor, reserva_id), actor)


@router.post(
    "/reservas/{reserva_id}/cancelar",
    response_model=ReservaResponse,
    summary="Cancelar una reserva",
    responses={
        401: _401,
        403: {"description": "El personal no opera en la sede de retiro (`FORBIDDEN`)"},
        404: _404,
        409: {"description": "`TRANSICION_INVALIDA`"},
    },
)
def cancelar_reserva(
    reserva_id: int,
    servicio: Servicio,
    actor: Autenticado,
    datos: Annotated[CancelarReservaRequest | None, Body()] = None,
) -> ReservaResponse:
    """La cancela el socio (la propia) o el bibliotecario de la sede de retiro. Si tenía un
    ejemplar asignado, se ofrece a la siguiente reserva de la cola."""
    motivo = datos.motivo if datos else None
    return reserva_a_response(servicio.cancelar(actor, reserva_id, motivo), actor)


@router.post(
    "/reservas/{reserva_id}/retirar",
    response_model=PrestamoResponse,
    summary="Entregar el ejemplar reservado",
    responses={
        401: _401,
        403: _403,
        404: _404,
        409: {"description": "`TRANSICION_INVALIDA` o `SOCIO_INHABILITADO`"},
    },
)
def retirar_reserva(
    reserva_id: int,
    servicio: Servicio,
    actor: Annotated[Usuario, Depends(requiere(Permiso.RESERVA_REGISTRAR))],
) -> PrestamoResponse:
    """La reserva queda cumplida y se crea el préstamo activo con su vencimiento."""
    return prestamo_a_response(servicio.retirar(actor, reserva_id), actor)


@router.post(
    "/admin/tareas/vencer-reservas",
    response_model=TareaResponse,
    summary="Vencer reservas no retiradas",
    tags=["Administración"],
    responses={401: _401, 403: _403},
)
def vencer_reservas(
    servicio: Servicio, actor: Annotated[Usuario, Depends(requiere(Permiso.TAREAS_EJECUTAR))]
) -> TareaResponse:
    """Vence las reservas fuera de plazo y reasigna sus ejemplares. Corre sola cada día."""
    return TareaResponse(tarea="vencer-reservas", cambios=servicio.vencer_reservas(actor))
