"""Respuestas de reservas.

La reserva tiene un esquema por rol, como préstamos:

- **Socio** (``ReservaPropiaResponse``): su reserva. En el historial, el autor es «Vos»,
  «Personal de la biblioteca» o «Sistema».
- **Personal** (``ReservaPersonalResponse``): agrega quién la registró y el usuario de cada
  movimiento.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.dtos.response.autoria import autor_visible
from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.paginacion import Pagina
from app.models.reserva import MovimientoReserva, Reserva
from app.models.usuario import Permiso, Usuario
from app.services.reserva_service import DetalleReserva


def _es_personal(lector: Usuario) -> bool:
    return lector.puede(Permiso.RESERVA_LEER)


class ReservaPropiaResponse(BaseModel):
    """Lo que ve el socio de su reserva (y la base de lo que ve el personal)."""

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
    fecha_cierre: datetime | None


class ReservaPersonalResponse(ReservaPropiaResponse):
    """Lo que ve el personal: agrega quién registró la reserva."""

    registrada_por: UsuarioRefResponse | None


ReservaResponse = ReservaPersonalResponse | ReservaPropiaResponse


def _campos(r: Reserva) -> dict[str, Any]:
    assert r.id is not None
    return {
        "id": r.id,
        "numero": r.numero,
        "estado": r.estado_nombre.value,
        "socio_id": r.socio_id,
        "socio": r.socio_nombre,
        "numero_socio": r.numero_socio,
        "libro_id": r.libro_id,
        "libro": r.libro_titulo,
        "sede_retiro_id": r.sede_retiro_id,
        "sede_retiro": r.sede_retiro_nombre,
        "fecha_reserva": r.fecha_reserva,
        "posicion_en_cola": r.posicion_en_cola,
        "ejemplar_id": r.ejemplar_id,
        "codigo_ejemplar": r.codigo_ejemplar,
        "vencimiento_retiro": r.vencimiento_retiro,
        "prestamo_id": r.prestamo_id,
        "fecha_cierre": r.fecha_cierre,
    }


def _registrada_por(r: Reserva) -> UsuarioRefResponse | None:
    return UsuarioRefResponse.desde(r.registrada_por) if r.registrada_por else None


def reserva_a_response(r: Reserva, lector: Usuario) -> ReservaResponse:
    """Arma el esquema que corresponde al rol del lector."""
    if not _es_personal(lector):
        return ReservaPropiaResponse(**_campos(r))
    return ReservaPersonalResponse(**_campos(r), registrada_por=_registrada_por(r))


class MovimientoReservaResponse(BaseModel):
    """Movimiento del historial de la reserva.

    ``autor`` es el nombre para mostrar. El personal ve quién fue (``usuario``); el socio ve
    «Vos», «Personal de la biblioteca» o «Sistema», y ``usuario`` llega siempre nulo.
    """

    estado_anterior: str | None
    estado_nuevo: str
    fecha_hora: datetime
    autor: str
    usuario: UsuarioRefResponse | None
    observacion: str | None

    @classmethod
    def desde(cls, m: MovimientoReserva, lector: Usuario) -> "MovimientoReservaResponse":
        personal = _es_personal(lector)
        return cls(
            estado_anterior=m.estado_anterior.value if m.estado_anterior else None,
            estado_nuevo=m.estado_nuevo.value,
            fecha_hora=m.fecha_hora,
            autor=autor_visible(m.usuario, lector, personal=personal),
            usuario=UsuarioRefResponse.desde(m.usuario) if personal and m.usuario else None,
            observacion=m.observacion,
        )


class _Detalle(BaseModel):
    historial: list[MovimientoReservaResponse]


class ReservaDetallePropiaResponse(ReservaPropiaResponse, _Detalle):
    """Ficha que ve el socio."""


class ReservaDetallePersonalResponse(ReservaPersonalResponse, _Detalle):
    """Ficha que ve el personal."""


ReservaDetalleResponse = ReservaDetallePersonalResponse | ReservaDetallePropiaResponse


def detalle_a_response(d: DetalleReserva, lector: Usuario) -> ReservaDetalleResponse:
    historial = [MovimientoReservaResponse.desde(m, lector) for m in d.historial]
    if not _es_personal(lector):
        return ReservaDetallePropiaResponse(**_campos(d.reserva), historial=historial)
    return ReservaDetallePersonalResponse(
        **_campos(d.reserva), registrada_por=_registrada_por(d.reserva), historial=historial
    )


class PaginaReservasResponse(BaseModel):
    items: list[ReservaResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Reserva], lector: Usuario) -> "PaginaReservasResponse":
        return cls(
            items=[reserva_a_response(r, lector) for r in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
