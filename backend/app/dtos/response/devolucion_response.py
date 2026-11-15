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
from app.models.pago import Pago
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


class PagoPropioResponse(BaseModel):
    """Un pago de la multa.

    ``motivo``: por qué se rechazó o se canceló. ``numero_comprobante``: el del comprobante en
    PDF (``GET /pagos/{id}/comprobante``), solo si está aprobado. ``forma_en_linea`` y
    ``tarjeta_ultimos4``: cómo pagó el socio en línea.
    """

    id: int
    multa_id: int
    medio: str
    estado: str
    monto: Decimal
    fecha: datetime
    acreditado_en: datetime | None
    motivo: str | None
    forma_en_linea: str | None
    tarjeta_ultimos4: str | None
    numero_comprobante: str | None
    numero_prestamo: str | None
    libro: str | None
    dias_atraso: int | None


class PagoPersonalResponse(PagoPropioResponse):
    """El personal ve además quién lo registró y el comprobante."""

    registrado_por: UsuarioRefResponse | None
    comprobante: str | None


PagoResponse = PagoPersonalResponse | PagoPropioResponse


def pago_a_response(p: Pago, lector: Usuario) -> PagoResponse:
    assert p.id is not None
    campos: dict[str, Any] = {
        "id": p.id,
        "multa_id": p.multa_id,
        "medio": p.medio.value,
        "estado": p.estado.value,
        "monto": p.monto,
        "fecha": p.fecha,
        "acreditado_en": p.acreditado_en,
        "motivo": p.motivo,
        "forma_en_linea": p.forma_en_linea.value if p.forma_en_linea else None,
        "tarjeta_ultimos4": p.tarjeta_ultimos4,
        "numero_comprobante": p.numero_comprobante,
        "numero_prestamo": p.numero_prestamo,
        "libro": p.libro_titulo,
        "dias_atraso": p.dias_atraso,
    }
    if not lector.puede(Permiso.MULTA_LEER):
        return PagoPropioResponse(**campos)
    return PagoPersonalResponse(
        **campos,
        registrado_por=UsuarioRefResponse.desde(p.registrado_por) if p.registrado_por else None,
        comprobante=p.comprobante,
    )


class MultaPropiaResponse(BaseModel):
    """``pago``: el que la saldó; ``pago_en_curso``: el pago en línea iniciado y sin resultado."""

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
    pago: PagoResponse | None = None
    pago_en_curso: PagoResponse | None = None


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
        "pago": pago_a_response(m.pago_aprobado, lector) if m.pago_aprobado else None,
        "pago_en_curso": pago_a_response(m.pago_pendiente, lector) if m.pago_pendiente else None,
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
