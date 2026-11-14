"""Endpoints de remitos: envíos entre sedes con trazabilidad."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.dependencies import get_remito_service, requiere
from app.dtos.request.prestamo_request import (
    MotivoTextoRequest,
    RecepcionRequest,
    RemitoCrearRequest,
)
from app.dtos.response.prestamo_response import (
    PaginaRemitosResponse,
    RemitoDetalleResponse,
    RemitoResponse,
)
from app.models.remito import MotivoRemito
from app.models.states.remito import EstadoRemitoEnum
from app.models.usuario import Permiso, Usuario
from app.services.remito_service import RemitoService

router = APIRouter(prefix="/api/v1/remitos", tags=["Remitos"])

Servicio = Annotated[RemitoService, Depends(get_remito_service)]
Operador = Annotated[Usuario, Depends(requiere(Permiso.REMITO_OPERAR))]
Lector = Annotated[Usuario, Depends(requiere(Permiso.REMITO_LEER))]

_401 = {"description": "No autenticado (`TOKEN_INVALIDO`)"}
_403 = {"description": "No es la sede que corresponde (`FORBIDDEN`)"}
_404 = {"description": "El remito no existe (`REMITO_NO_ENCONTRADO`)"}
_409 = {"description": "Salto o retroceso en el ciclo de vida (`TRANSICION_INVALIDA`)"}


@router.post(
    "",
    response_model=RemitoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar un remito",
    responses={
        401: _401,
        403: _403,
        404: {"description": "Préstamo, ejemplar o sede inexistentes"},
        409: {
            "description": "`SEDE_EN_BAJA`, `EJEMPLAR_EN_OTRO_REMITO` o `EJEMPLAR_NO_DISPONIBLE`"
        },
        422: {"description": "`EJEMPLAR_FUERA_DE_SEDE_ORIGEN` o `REMITO_INVALIDO`"},
    },
)
def generar_remito(
    datos: RemitoCrearRequest, response: Response, servicio: Servicio, actor: Operador
) -> RemitoResponse:
    """Desde la sede del bibliotecario: envío de préstamos o traslado de ejemplares."""
    remito = servicio.generar(
        actor, datos.sede_destino_id, datos.motivo, datos.a_lineas(), datos.observaciones
    )
    response.headers["Location"] = f"/api/v1/remitos/{remito.id}"
    return RemitoResponse.desde(remito)


@router.get(
    "",
    response_model=PaginaRemitosResponse,
    summary="Listado de remitos",
    responses={401: _401, 403: _403},
)
def listar_remitos(
    servicio: Servicio,
    actor: Lector,
    estado: EstadoRemitoEnum | None = None,
    motivo: MotivoRemito | None = None,
    sede_id: int | None = None,
    numero: Annotated[str | None, Query(max_length=20)] = None,
    abiertos: bool = False,
    atrasados: Annotated[
        bool, Query(description="Solo los que pasaron el plazo de despacho sin salir")
    ] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaRemitosResponse:
    """El bibliotecario ve los de su sede (como origen o destino).

    Cada remito trae `despachar_hasta` y `atrasado` (plazo de despacho, parámetro
    `despacho_maximo_dias`)."""
    return PaginaRemitosResponse.desde(
        servicio.listar(actor, estado, motivo, sede_id, numero, abiertos, page, size, atrasados)
    )


@router.get(
    "/{remito_id}",
    response_model=RemitoDetalleResponse,
    summary="Detalle y trazabilidad de un remito",
    responses={401: _401, 403: _403, 404: _404},
)
def obtener_remito(remito_id: int, servicio: Servicio, actor: Lector) -> RemitoDetalleResponse:
    """Detalle por ejemplar, un movimiento por cada transición e incidencias."""
    return RemitoDetalleResponse.desde_detalle(servicio.detalle(actor, remito_id))


def _accion(nombre: str, resumen: str, descripcion: str) -> dict[str, object]:
    return {
        "path": f"/{{remito_id}}/{nombre}",
        "response_model": RemitoResponse,
        "summary": resumen,
        "description": descripcion,
        "responses": {401: _401, 403: _403, 404: _404, 409: _409},
    }


@router.post(**_accion("empaquetar", "Empaquetar", "Solo la sede origen, desde `GENERADO`."))
def empaquetar(remito_id: int, servicio: Servicio, actor: Operador) -> RemitoResponse:
    return RemitoResponse.desde(servicio.empaquetar(actor, remito_id))


@router.post(
    **_accion(
        "despachar",
        "Despachar",
        "Solo la sede origen, desde `EMPAQUETADO`; los ejemplares quedan `EN_TRANSITO`.",
    )
)
def despachar(remito_id: int, servicio: Servicio, actor: Operador) -> RemitoResponse:
    return RemitoResponse.desde(servicio.despachar(actor, remito_id))


@router.post(
    **_accion("en-transito", "Marcar en tránsito", "Solo la sede origen, desde `DESPACHADO`.")
)
def pasar_a_transito(remito_id: int, servicio: Servicio, actor: Operador) -> RemitoResponse:
    return RemitoResponse.desde(servicio.pasar_a_transito(actor, remito_id))


@router.post(
    "/{remito_id}/recibir",
    response_model=RemitoDetalleResponse,
    summary="Recibir y verificar",
    responses={
        401: _401,
        403: _403,
        404: _404,
        409: _409,
        422: {"description": "Faltan líneas o una incidencia sin observación (`REMITO_INVALIDO`)"},
    },
)
def recibir(
    remito_id: int, datos: RecepcionRequest, servicio: Servicio, actor: Operador
) -> RemitoDetalleResponse:
    """Solo la sede destino. El estado final sigue a la peor línea (dañado o destruido)."""
    return RemitoDetalleResponse.desde_detalle(
        servicio.recibir(actor, remito_id, datos.a_recepcion())
    )


@router.post(
    "/{remito_id}/anular",
    response_model=RemitoResponse,
    summary="Anular antes del despacho",
    responses={401: _401, 403: _403, 404: _404, 409: _409, 422: {}},
)
def anular(
    remito_id: int, datos: MotivoTextoRequest, servicio: Servicio, actor: Operador
) -> RemitoResponse:
    """Libera los ejemplares y cancela los préstamos del envío."""
    return RemitoResponse.desde(servicio.anular(actor, remito_id, datos.motivo))


@router.post(
    "/{remito_id}/extraviado",
    response_model=RemitoResponse,
    summary="Marcar como extraviado",
    responses={
        401: _401,
        403: _403,
        404: _404,
        409: {"description": "`TRANSICION_INVALIDA` o `PLAZO_DE_TRANSITO_VIGENTE`"},
        422: {},
    },
)
def marcar_extraviado(
    remito_id: int,
    datos: MotivoTextoRequest,
    servicio: Servicio,
    actor: Annotated[Usuario, Depends(requiere(Permiso.REMITO_EXTRAVIO))],
) -> RemitoResponse:
    """Si pasó el plazo máximo de tránsito: ejemplares de baja con incidencia."""
    return RemitoResponse.desde(servicio.marcar_extraviado(actor, remito_id, datos.motivo))
