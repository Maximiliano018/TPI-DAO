"""Respuesta del registro de una devolución (solo la ve el personal que la registra)."""

from pydantic import BaseModel

from app.dtos.response.devolucion_response import (
    DevolucionResponse,
    MultaResponse,
    devolucion_a_response,
    multa_a_response,
)
from app.dtos.response.prestamo_response import (
    PrestamoResponse,
    RemitoResumenResponse,
    prestamo_a_response,
)
from app.models.usuario import Usuario
from app.services.devolucion_service import ResultadoDevolucion


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
    def desde(cls, r: ResultadoDevolucion, actor: Usuario) -> "ResultadoDevolucionResponse":
        return cls(
            prestamo=prestamo_a_response(r.prestamo, actor),
            devolucion=devolucion_a_response(r.devolucion, actor),
            multa=multa_a_response(r.multa, actor) if r.multa else None,
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
