"""Router de sedes. Ejemplo de referencia de un router delgado: valida la forma de la
entrada, exige el rol, llama al servicio y convierte la entidad en DTO."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from biblioteca.api.deps import Actor, Admin, get_sede_service
from biblioteca.api.schemas.comunes import PaginaSalida, ParametrosPagina, paginacion
from biblioteca.api.schemas.sedes import (
    DatosSedeEntrada,
    FranjaHorariaEntrada,
    SedeCrear,
    SedeSalida,
)
from biblioteca.application.services.sede_service import SedeService
from biblioteca.domain.entities.sede import Sede

router = APIRouter(prefix="/sedes", tags=["sedes"])

Servicio = Annotated[SedeService, Depends(get_sede_service)]


def _salida(sede: Sede) -> SedeSalida:
    return SedeSalida.model_validate(sede)


@router.get("")
def listar_sedes(
    _actor: Actor,
    servicio: Servicio,
    pagina: Annotated[ParametrosPagina, Depends(paginacion)],
    solo_activas: bool = False,
) -> PaginaSalida[SedeSalida]:
    resultado = servicio.listar(solo_activas=solo_activas, limite=pagina.limite, desde=pagina.desde)
    return PaginaSalida(
        items=[_salida(s) for s in resultado.items],
        total=resultado.total,
        limite=resultado.limite,
        desde=resultado.desde,
    )


@router.get("/{sede_id}")
def obtener_sede(sede_id: int, _actor: Actor, servicio: Servicio) -> SedeSalida:
    return _salida(servicio.obtener(sede_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_sede(entrada: SedeCrear, actor: Admin, servicio: Servicio) -> SedeSalida:
    return _salida(servicio.crear(actor, entrada.codigo, entrada.a_datos()))


@router.put("/{sede_id}")
def actualizar_sede(
    sede_id: int, entrada: DatosSedeEntrada, actor: Admin, servicio: Servicio
) -> SedeSalida:
    return _salida(servicio.actualizar(actor, sede_id, entrada.a_datos()))


@router.put("/{sede_id}/horarios")
def definir_horarios(
    sede_id: int, franjas: list[FranjaHorariaEntrada], actor: Admin, servicio: Servicio
) -> SedeSalida:
    """Reemplaza todos los horarios de la sede."""
    return _salida(servicio.definir_horarios(actor, sede_id, [f.a_franja() for f in franjas]))


@router.post("/{sede_id}/baja")
def dar_de_baja_sede(sede_id: int, actor: Admin, servicio: Servicio) -> SedeSalida:
    """Falla con 409 si la sede tiene préstamos, envíos o reservas en curso."""
    return _salida(servicio.dar_de_baja(actor, sede_id))


@router.post("/{sede_id}/reactivar")
def reactivar_sede(sede_id: int, actor: Admin, servicio: Servicio) -> SedeSalida:
    return _salida(servicio.reactivar(actor, sede_id))
