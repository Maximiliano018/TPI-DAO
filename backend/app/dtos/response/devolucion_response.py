"""Respuestas de devoluciones y multas.

Como préstamos y reservas, tienen un esquema por rol:

- **Socio** (``DevolucionPropiaResponse``, ``MultaPropiaResponse``): sin la identidad del personal
  que registró la devolución o saldó la multa.
- **Personal** (``DevolucionPersonalResponse``, ``MultaPersonalResponse``): agrega quién fue.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.devolucion import Devolucion, Multa
from app.models.paginacion import Pagina
from app.models.usuario import Permiso, Usuario


class DevolucionPropiaResponse(BaseModel):
    """``registrada_en``: cuándo se cargó; ``motivo_fecha``: por qué la fecha es anterior."""

    id: int
    prestamo_id: int
    sede_id: int
    fecha_hora: datetime
    estado_fisico_recibido: str
    dias_atraso: int
    observaciones: str | None
    registrada_en: datetime | None
    motivo_fecha: str | None


class DevolucionPersonalResponse(DevolucionPropiaResponse):
    registrada_por: UsuarioRefResponse | None


DevolucionResponse = DevolucionPersonalResponse | DevolucionPropiaResponse


def devolucion_a_response(d: Devolucion, lector: Usuario) -> DevolucionResponse:
    assert d.id is not None
    campos: dict[str, Any] = {
        "id": d.id,
        "prestamo_id": d.prestamo_id,
        "sede_id": d.sede_id,
        "fecha_hora": d.fecha_hora,
        "estado_fisico_recibido": d.estado_recibido.value,
        "dias_atraso": d.dias_atraso,
        "observaciones": d.observaciones,
        "registrada_en": d.registrada_en,
        "motivo_fecha": d.motivo_fecha,
    }
    if not lector.puede(Permiso.PRESTAMO_LEER):
        return DevolucionPropiaResponse(**campos)
    registrada_por = UsuarioRefResponse.desde(d.registrada_por) if d.registrada_por else None
    return DevolucionPersonalResponse(**campos, registrada_por=registrada_por)


class MultaPropiaResponse(BaseModel):
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


class MultaPersonalResponse(MultaPropiaResponse):
    saldada_por: UsuarioRefResponse | None


MultaResponse = MultaPersonalResponse | MultaPropiaResponse


def multa_a_response(m: Multa, lector: Usuario) -> MultaResponse:
    assert m.id is not None
    campos: dict[str, Any] = {
        "id": m.id,
        "prestamo_id": m.prestamo_id,
        "numero_prestamo": m.numero_prestamo,
        "socio_id": m.socio_id,
        "socio": m.socio_nombre,
        "libro": m.libro_titulo,
        "dias_atraso": m.dias_atraso,
        "monto_por_dia": m.monto_por_dia,
        "monto_total": m.monto_total,
        "estado": m.estado.value,
        "fecha_generacion": m.fecha_generacion,
        "fecha_saldada": m.fecha_saldada,
    }
    if not lector.puede(Permiso.MULTA_LEER):
        return MultaPropiaResponse(**campos)
    saldada_por = UsuarioRefResponse.desde(m.saldada_por) if m.saldada_por else None
    return MultaPersonalResponse(**campos, saldada_por=saldada_por)


class PaginaMultasResponse(BaseModel):
    items: list[MultaResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Multa], lector: Usuario) -> "PaginaMultasResponse":
        return cls(
            items=[multa_a_response(m, lector) for m in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
