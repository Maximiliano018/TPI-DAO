"""Endpoints de devoluciones y multas."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.controllers.dependencies import get_devolucion_service, requiere, usuario_actual
from app.dtos.response.devolucion_response import (
    DevolucionResponse,
    MultaResponse,
    PaginaMultasResponse,
)
from app.dtos.response.prestamo_response import PrestamoResponse, RemitoResumenResponse
from app.models.devolucion import EstadoMulta, EstadoRecibido
from app.models.usuario import Permiso, Usuario
from app.services.devolucion_service import DevolucionService, ResultadoDevolucion

router = APIRouter(prefix="/api/v1", tags=["Devoluciones y multas"])

Servicio = Annotated[DevolucionService, Depends(get_devolucion_service)]
Autenticado = Annotated[Usuario, Depends(usuario_actual)]
Bibliotecario = Annotated[Usuario, Depends(requiere(Permiso.DEVOLUCION_REGISTRAR))]
Personal = Annotated[Usuario, Depends(requiere(Permiso.MULTA_SALDAR))]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso o préstamo de otra sede (`FORBIDDEN`)"}


class DevolucionRequest(BaseModel):
    """Si no se indica ``fecha_hora`` se toma el momento actual."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"estado_fisico": "BUENO", "observaciones": "Sin novedades"}}
    )

    estado_fisico: EstadoRecibido
    observaciones: str | None = Field(default=None, max_length=300)
    fecha_hora: datetime | None = None


class SocioEstadoResponse(BaseModel):
    id: int
    estado: str
    motivo: str | None


class ResultadoDevolucionResponse(BaseModel):
    """Lo que cambió con la devolución: préstamo, multa, remito de retorno y socio."""

    prestamo: PrestamoResponse
    devolucion: DevolucionResponse
    multa: MultaResponse | None
    remito_retorno: RemitoResumenResponse | None
    reserva_asignada: str | None
    socio: SocioEstadoResponse | None

    @classmethod
    def desde(cls, r: ResultadoDevolucion) -> "ResultadoDevolucionResponse":
        return cls(
            prestamo=PrestamoResponse.desde(r.prestamo),
            devolucion=DevolucionResponse.desde(r.devolucion),
            multa=MultaResponse.desde(r.multa) if r.multa else None,
            remito_retorno=(
                RemitoResumenResponse.desde(r.remito_retorno) if r.remito_retorno else None
            ),
            reserva_asignada=r.reserva_asignada.numero if r.reserva_asignada else None,
            socio=_socio(r),
        )


def _socio(r: ResultadoDevolucion) -> SocioEstadoResponse | None:
    if r.socio is None or r.socio.id is None:
        return None
    motivo = r.socio.motivo_inhabilitacion
    return SocioEstadoResponse(
        id=r.socio.id, estado=r.socio.estado.value, motivo=motivo.value if motivo else None
    )


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
        422: {"description": "Fecha futura o anterior a la entrega, u observaciones faltantes"},
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
        actor, prestamo_id, datos.estado_fisico, datos.observaciones, datos.fecha_hora
    )
    return ResultadoDevolucionResponse.desde(resultado)


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
    return PaginaMultasResponse.desde(servicio.listar_multas(actor, socio_id, estado, page, size))


@router.post(
    "/multas/{multa_id}/saldar",
    response_model=MultaResponse,
    summary="Marcar una multa como saldada",
    responses={
        401: _401,
        403: _403,
        404: {"description": "`MULTA_NO_ENCONTRADA`"},
        409: {"description": "Ya estaba saldada (`TRANSICION_INVALIDA`)"},
    },
)
def saldar_multa(multa_id: int, servicio: Servicio, actor: Personal) -> MultaResponse:
    """El cobro queda fuera del sistema; al saldarla se reevalúa la habilitación del socio."""
    return MultaResponse.desde(servicio.saldar_multa(actor, multa_id))
