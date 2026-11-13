"""Endpoints de reservas."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict

from app.controllers.dependencies import get_reserva_service, requiere, usuario_actual
from app.dtos.response.prestamo_response import PrestamoResponse, TareaResponse
from app.models.paginacion import Pagina
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum
from app.models.usuario import Permiso, Usuario
from app.services.reserva_service import ReservaService

router = APIRouter(prefix="/api/v1", tags=["Reservas"])

Servicio = Annotated[ReservaService, Depends(get_reserva_service)]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_404 = {"description": "No existe o no es visible (`RESERVA_NO_ENCONTRADA`)"}


class ReservaRequest(BaseModel):
    """El socio omite ``socio_id`` (se toma de su sesión); el bibliotecario lo indica."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"libro_id": 12, "sede_retiro_id": 2, "socio_id": 45}}
    )

    libro_id: int
    sede_retiro_id: int
    socio_id: int | None = None


class ReservaResponse(BaseModel):
    id: int
    numero: str
    estado: str
    socio_id: int
    socio: str | None
    numero_socio: str | None
    libro_id: int
    libro: str | None
    sede_retiro_id: int
    sede_retiro: str | None
    fecha_reserva: datetime
    posicion_en_cola: int | None
    ejemplar_id: int | None
    codigo_ejemplar: str | None
    vencimiento_retiro: date | None
    prestamo_id: int | None

    @classmethod
    def desde(cls, r: Reserva) -> "ReservaResponse":
        assert r.id is not None
        return cls(
            id=r.id,
            numero=r.numero,
            estado=r.estado_nombre.value,
            socio_id=r.socio_id,
            socio=r.socio_nombre,
            numero_socio=r.numero_socio,
            libro_id=r.libro_id,
            libro=r.libro_titulo,
            sede_retiro_id=r.sede_retiro_id,
            sede_retiro=r.sede_retiro_nombre,
            fecha_reserva=r.fecha_reserva,
            posicion_en_cola=r.posicion_en_cola,
            ejemplar_id=r.ejemplar_id,
            codigo_ejemplar=r.codigo_ejemplar,
            vencimiento_retiro=r.vencimiento_retiro,
            prestamo_id=r.prestamo_id,
        )


class PaginaReservasResponse(BaseModel):
    items: list[ReservaResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Reserva]) -> "PaginaReservasResponse":
        return cls(
            items=[ReservaResponse.desde(r) for r in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )


@router.post(
    "/reservas",
    response_model=ReservaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar un libro",
    responses={
        401: _401,
        403: _403,
        404: {"description": "Socio, libro o sede inexistentes"},
        409: {
            "description": "`HAY_EJEMPLARES_DISPONIBLES`, `SOCIO_INHABILITADO`, `SEDE_EN_BAJA`, "
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
    return ReservaResponse.desde(reserva)


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
    estado: EstadoReservaEnum | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaReservasResponse:
    """El socio ve las propias con su posición en la cola; el personal, todas."""
    return PaginaReservasResponse.desde(
        servicio.listar(actor, socio_id, libro_id, estado, page, size)
    )


@router.get(
    "/reservas/{reserva_id}",
    response_model=ReservaResponse,
    summary="Detalle y posición en la cola",
    responses={401: _401, 404: _404},
)
def obtener_reserva(reserva_id: int, servicio: Servicio, actor: Autenticado) -> ReservaResponse:
    return ReservaResponse.desde(servicio.detalle(actor, reserva_id))


@router.post(
    "/reservas/{reserva_id}/cancelar",
    response_model=ReservaResponse,
    summary="Cancelar una reserva",
    responses={401: _401, 404: _404, 409: {"description": "`TRANSICION_INVALIDA`"}},
)
def cancelar_reserva(reserva_id: int, servicio: Servicio, actor: Autenticado) -> ReservaResponse:
    """Si tenía un ejemplar asignado, se ofrece a la siguiente reserva de la cola."""
    return ReservaResponse.desde(servicio.cancelar(actor, reserva_id))


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
    return PrestamoResponse.desde(servicio.retirar(actor, reserva_id))


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
