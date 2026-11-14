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
    SolicitudPrestamoRequest,
)
from app.dtos.response.prestamo_response import (
    PaginaPrestamosResponse,
    ParametroResponse,
    PrestamoDetalleResponse,
    PrestamoResponse,
    PropuestaPrestamoResponse,
    TareaResponse,
    detalle_a_response,
    prestamo_a_response,
)
from app.models.prestamo import TipoPrestamo
from app.models.states.prestamo import EstadoPrestamoEnum
from app.models.usuario import Permiso, Usuario
from app.services.parametro_service import ParametroService
from app.services.prestamo_service import PrestamoService

router = APIRouter(prefix="/api/v1", tags=["Préstamos"])

Servicio = Annotated[PrestamoService, Depends(get_prestamo_service)]
Bibliotecario = Annotated[Usuario, Depends(requiere(Permiso.PRESTAMO_REGISTRAR))]
SocioSolicitante = Annotated[Usuario, Depends(requiere(Permiso.PRESTAMO_SOLICITAR_PROPIO))]
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
    prestamo = servicio.registrar(actor, datos.socio_id, datos.ejemplar_id, datos.sede_destino_id)
    response.headers["Location"] = f"/api/v1/prestamos/{prestamo.id}"
    return prestamo_a_response(prestamo, actor)


_ERRORES_SOLICITUD = {
    401: _401,
    403: {"description": "Sin `PRESTAMO_SOLICITAR_PROPIO` o a nombre de otro socio (`FORBIDDEN`)"},
    404: {"description": "El libro o la sede no existen"},
    409: {
        "description": "`SOCIO_INHABILITADO`, `SOCIO_EN_BAJA`, `LIMITE_PRESTAMOS`, "
        "`LIBRO_REPETIDO`, `SEDE_EN_BAJA` o `SIN_EJEMPLARES_DISPONIBLES` (se ofrece reservar)"
    },
}


@router.get(
    "/prestamos/solicitudes/propuesta",
    response_model=PropuestaPrestamoResponse,
    summary="Propuesta de préstamo para el socio",
    responses=_ERRORES_SOLICITUD,
)
def proponer_prestamo(
    servicio: Servicio,
    actor: SocioSolicitante,
    libro_id: int,
    sede_destino_id: int | None = None,
    socio_id: int | None = None,
) -> PropuestaPrestamoResponse:
    """Qué préstamo se haría si el socio pide el libro ahora: tipo, sedes y plazos.

    No aparta nada. Sin `sede_destino_id`, se propone la sede de alta del socio. `socio_id`,
    si viene, tiene que ser el propio.
    """
    return PropuestaPrestamoResponse.desde(
        servicio.proponer(actor, libro_id, sede_destino_id, socio_id)
    )


@router.post(
    "/prestamos/solicitudes",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="El socio solicita un préstamo para sí",
    responses={
        **_ERRORES_SOLICITUD,
        409: {
            "description": _ERRORES_SOLICITUD[409]["description"]
            + " o `DISPONIBILIDAD_CAMBIADA` (la propuesta ya no vale)"
        },
    },
)
def solicitar_prestamo(
    datos: SolicitudPrestamoRequest, response: Response, servicio: Servicio, actor: SocioSolicitante
) -> PrestamoResponse:
    """Autogestión: el socio pide un libro y el sistema elige el tipo y el ejemplar.

    El socio es siempre el de la sesión. Local si hay disponibles en la sede destino (queda con
    plazo de retiro); si no, interbibliotecario desde la sede con más disponibles.
    """
    prestamo = servicio.solicitar(
        actor,
        datos.libro_id,
        datos.sede_destino_id,
        datos.socio_id,
        datos.sede_origen_esperada_id,
    )
    response.headers["Location"] = f"/api/v1/prestamos/{prestamo.id}"
    return prestamo_a_response(prestamo, actor)


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
    sede_origen_id: Annotated[
        int | None, Query(description="Solo los que salen de esta sede (envíos a armar)")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaPrestamosResponse:
    """El administrador ve todos; el bibliotecario, los de su sede; el socio, los propios."""
    return PaginaPrestamosResponse.desde(
        servicio.listar(actor, estado, tipo, socio_id, numero, page, size, sede_origen_id), actor
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
    """El socio ve sus préstamos sin la identidad del personal."""
    return detalle_a_response(servicio.detalle(actor, prestamo_id), actor)


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
    return prestamo_a_response(servicio.entregar(actor, prestamo_id), actor)


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
    return prestamo_a_response(servicio.renovar(actor, prestamo_id), actor)


@router.post(
    "/prestamos/{prestamo_id}/cancelar",
    response_model=PrestamoResponse,
    summary="Cancelar antes de la entrega",
    responses={401: _401, 403: _403, 404: _404, 409: _409_TRANSICION},
)
def cancelar_prestamo(
    prestamo_id: int, datos: CancelarRequest, servicio: Servicio, actor: Autenticado
) -> PrestamoResponse:
    """Libera el ejemplar; si ya había llegado a destino, genera el remito de retorno.

    El socio puede cancelar sus propios préstamos mientras están `SOLICITADO`.
    """
    return prestamo_a_response(servicio.cancelar(actor, prestamo_id, datos.motivo), actor)


@router.post(
    "/admin/tareas/vencer-retiros",
    response_model=TareaResponse,
    summary="Cancelar préstamos no retirados a tiempo",
    tags=["Administración"],
    responses={401: _401, 403: _403},
)
def vencer_retiros(
    servicio: Servicio, actor: Annotated[Usuario, Depends(requiere(Permiso.TAREAS_EJECUTAR))]
) -> TareaResponse:
    """Cancela los préstamos cuyo plazo de retiro pasó. También corre sola todos los días."""
    return TareaResponse(tarea="vencer-retiros", cambios=servicio.vencer_retiros(actor))


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
