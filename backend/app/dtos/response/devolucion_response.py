"""Respuestas de devoluciones y multas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.devolucion import Devolucion, Multa
from app.models.paginacion import Pagina


class DevolucionResponse(BaseModel):
    id: int
    prestamo_id: int
    sede_id: int
    fecha_hora: datetime
    estado_fisico_recibido: str
    dias_atraso: int
    observaciones: str | None
    registrada_por: UsuarioRefResponse | None

    @classmethod
    def desde(cls, d: Devolucion) -> "DevolucionResponse":
        assert d.id is not None
        return cls(
            id=d.id,
            prestamo_id=d.prestamo_id,
            sede_id=d.sede_id,
            fecha_hora=d.fecha_hora,
            estado_fisico_recibido=d.estado_recibido.value,
            dias_atraso=d.dias_atraso,
            observaciones=d.observaciones,
            registrada_por=UsuarioRefResponse.desde(d.registrada_por) if d.registrada_por else None,
        )


class MultaResponse(BaseModel):
    id: int
    prestamo_id: int
    numero_prestamo: str | None
    socio_id: int
    socio: str | None
    libro: str | None
    dias_atraso: int
    monto_por_dia: Decimal
    monto_total: Decimal
    estado: str
    fecha_generacion: datetime
    fecha_saldada: datetime | None
    saldada_por: UsuarioRefResponse | None

    @classmethod
    def desde(cls, m: Multa) -> "MultaResponse":
        assert m.id is not None
        return cls(
            id=m.id,
            prestamo_id=m.prestamo_id,
            numero_prestamo=m.numero_prestamo,
            socio_id=m.socio_id,
            socio=m.socio_nombre,
            libro=m.libro_titulo,
            dias_atraso=m.dias_atraso,
            monto_por_dia=m.monto_por_dia,
            monto_total=m.monto_total,
            estado=m.estado.value,
            fecha_generacion=m.fecha_generacion,
            fecha_saldada=m.fecha_saldada,
            saldada_por=UsuarioRefResponse.desde(m.saldada_por) if m.saldada_por else None,
        )


class PaginaMultasResponse(BaseModel):
    items: list[MultaResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Multa]) -> "PaginaMultasResponse":
        return cls(
            items=[MultaResponse.desde(m) for m in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
