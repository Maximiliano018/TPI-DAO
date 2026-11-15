"""Endpoints del pago de multas: en el mostrador o en línea (simulado)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.controllers.dependencies import get_pago_service, requiere, usuario_actual
from app.dtos.request.pago_request import PagoEnLineaRequest, SaldarMultaRequest
from app.dtos.response.devolucion_response import (
    MultaResponse,
    PagoResponse,
    multa_a_response,
    pago_a_response,
)
from app.models.usuario import Permiso, Usuario
from app.services.pago_service import PagoService

router = APIRouter(prefix="/api/v1", tags=["Pagos de multas"])

Servicio = Annotated[PagoService, Depends(get_pago_service)]
Socio = Annotated[Usuario, Depends(requiere(Permiso.MULTA_PAGAR_PROPIA))]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "Sin permiso (`FORBIDDEN`)"}
_YA_SALDADA = {"description": "Ya estaba saldada (`TRANSICION_INVALIDA`)"}


@router.post(
    "/multas/{multa_id}/saldar",
    response_model=MultaResponse,
    summary="Cobrar una multa en el mostrador",
    responses={
        401: _401,
        403: _403,
        404: {"description": "`MULTA_NO_ENCONTRADA`"},
        409: _YA_SALDADA,
        422: {"description": "Medio que no es de mostrador o comprobante muy largo"},
    },
)
def saldar_multa(
    multa_id: int,
    datos: SaldarMultaRequest,
    servicio: Servicio,
    actor: Annotated[Usuario, Depends(requiere(Permiso.MULTA_SALDAR))],
) -> MultaResponse:
    """Registra el pago con su medio (efectivo, débito, crédito o transferencia) y salda la
    multa; se reevalúa la habilitación del socio. Cancela el pago en línea en curso."""
    multa = servicio.saldar_en_mostrador(actor, multa_id, datos.medio, datos.comprobante)
    return multa_a_response(multa, actor)


@router.post(
    "/multas/{multa_id}/pagos",
    response_model=PagoResponse,
    status_code=201,
    summary="Iniciar el pago en línea (simulado) de una multa propia",
    responses={
        401: _401,
        403: _403,
        404: {"description": "No existe o es de otro socio (`MULTA_NO_ENCONTRADA`)"},
        409: _YA_SALDADA,
    },
)
def iniciar_pago(multa_id: int, servicio: Servicio, actor: Socio) -> PagoResponse:
    """Devuelve el pago pendiente que el socio completa en el checkout simulado. Si ya tenía uno
    en curso, devuelve ese."""
    return pago_a_response(servicio.iniciar_en_linea(actor, multa_id), actor)


@router.get(
    "/pagos/{pago_id}",
    response_model=PagoResponse,
    summary="Detalle de un pago",
    responses={401: _401, 404: {"description": "`PAGO_NO_ENCONTRADO`"}},
)
def obtener_pago(
    pago_id: int, servicio: Servicio, actor: Annotated[Usuario, Depends(usuario_actual)]
) -> PagoResponse:
    """El socio solo ve los pagos de sus multas."""
    return pago_a_response(servicio.detalle(actor, pago_id), actor)


@router.post(
    "/pagos/{pago_id}/pagar",
    response_model=PagoResponse,
    summary="Confirmar el pago en el checkout simulado",
    responses={
        401: _401,
        403: _403,
        404: {"description": "No existe o es de otro socio (`PAGO_NO_ENCONTRADO`)"},
        409: {"description": "El pago ya no está pendiente (`TRANSICION_INVALIDA`)"},
        422: {"description": "Tarjeta sin sus últimos 4 dígitos (`VALIDACION`)"},
    },
)
def pagar_en_linea(
    pago_id: int, datos: PagoEnLineaRequest, servicio: Servicio, actor: Socio
) -> PagoResponse:
    """Simulado: con tarjeta, la terminada en `0002` se rechaza y cualquier otra se aprueba; con
    dinero en cuenta se aprueba. Aprobado, la multa queda saldada."""
    pago = servicio.pagar_en_linea(actor, pago_id, datos.forma, datos.tarjeta_ultimos4)
    return pago_a_response(pago, actor)


@router.get(
    "/pagos/{pago_id}/comprobante",
    summary="Descargar el comprobante de pago (PDF)",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Comprobante en PDF"},
        401: _401,
        404: {"description": "`PAGO_NO_ENCONTRADO`"},
        409: {"description": "El pago no está aprobado (`TRANSICION_INVALIDA`)"},
    },
)
def descargar_comprobante(
    pago_id: int, servicio: Servicio, actor: Annotated[Usuario, Depends(usuario_actual)]
) -> Response:
    """El socio descarga los de sus pagos; el personal, cualquiera."""
    nombre, contenido = servicio.comprobante(actor, pago_id)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
