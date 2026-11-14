"""Respuestas de préstamos, remitos y parámetros.

El préstamo tiene un esquema por rol, como sedes y socios:

- **Socio** (``PrestamoPropioResponse``): su préstamo sin la identidad del personal. En el
  historial, el autor es «Vos», «Personal de la biblioteca» o «Sistema».
- **Personal** (``PrestamoPersonalResponse``): agrega quién lo registró y el usuario de cada
  movimiento.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.dtos.response.autoria import autor_visible
from app.dtos.response.devolucion_response import DevolucionResponse, MultaResponse
from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.incidencia import Incidencia
from app.models.paginacion import Pagina
from app.models.prestamo import MovimientoPrestamo, Prestamo
from app.models.remito import LineaRemito, MovimientoRemito, Remito
from app.models.states.remito import EstadoRemitoEnum
from app.models.usuario import Permiso, Usuario, UsuarioRef
from app.repositories.interfaces.prestamo_repository import Parametro
from app.services.prestamo_service import DetallePrestamo, PropuestaPrestamo
from app.services.remito_service import DetalleRemito


class PrestamoPropioResponse(BaseModel):
    """Lo que ve el socio de su préstamo.

    ``fecha_limite_retiro``: último día para retirarlo en la sede destino; si pasa sin retirarlo,
    se cancela solo.
    """

    id: int
    numero: str
    tipo: str
    estado: str
    socio_id: int
    socio: str | None
    numero_socio: str | None
    ejemplar_id: int
    codigo_ejemplar: str | None
    libro_id: int
    libro: str | None
    sede_origen_id: int
    sede_origen: str | None
    sede_destino_id: int
    sede_destino: str | None
    fecha_solicitud: datetime
    fecha_inicio: date | None
    fecha_vencimiento: date | None
    fecha_devolucion: datetime | None
    fecha_limite_retiro: date | None
    renovaciones: int


class PrestamoPersonalResponse(PrestamoPropioResponse):
    """Lo que ve el personal: agrega quién registró el préstamo."""

    registrado_por: UsuarioRefResponse | None


PrestamoResponse = PrestamoPersonalResponse | PrestamoPropioResponse


def _es_personal(lector: Usuario) -> bool:
    return lector.puede(Permiso.PRESTAMO_LEER)


def _campos(p: Prestamo) -> dict[str, Any]:
    assert p.id is not None
    return {
        "id": p.id,
        "numero": p.numero,
        "tipo": p.tipo.value,
        "estado": p.estado_nombre.value,
        "socio_id": p.socio_id,
        "socio": p.socio_nombre,
        "numero_socio": p.numero_socio,
        "ejemplar_id": p.ejemplar_id,
        "codigo_ejemplar": p.codigo_ejemplar,
        "libro_id": p.libro_id,
        "libro": p.libro_titulo,
        "sede_origen_id": p.sede_origen_id,
        "sede_origen": p.sede_origen_nombre,
        "sede_destino_id": p.sede_destino_id,
        "sede_destino": p.sede_destino_nombre,
        "fecha_solicitud": p.fecha_solicitud,
        "fecha_inicio": p.fecha_inicio,
        "fecha_vencimiento": p.fecha_vencimiento,
        "fecha_devolucion": p.fecha_devolucion,
        "fecha_limite_retiro": p.fecha_limite_retiro,
        "renovaciones": p.renovaciones,
    }


def _registrado_por(p: Prestamo) -> UsuarioRefResponse | None:
    return UsuarioRefResponse.desde(p.registrado_por) if p.registrado_por else None


def prestamo_a_response(p: Prestamo, lector: Usuario) -> PrestamoResponse:
    """Arma el esquema que corresponde al rol del lector."""
    if not _es_personal(lector):
        return PrestamoPropioResponse(**_campos(p))
    return PrestamoPersonalResponse(**_campos(p), registrado_por=_registrado_por(p))


class MovimientoPrestamoResponse(BaseModel):
    """Movimiento del historial del préstamo.

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
    def desde(cls, m: MovimientoPrestamo, lector: Usuario) -> "MovimientoPrestamoResponse":
        personal = _es_personal(lector)
        return cls(
            estado_anterior=m.estado_anterior.value if m.estado_anterior else None,
            estado_nuevo=m.estado_nuevo.value,
            fecha_hora=m.fecha_hora,
            autor=autor_visible(m.usuario, lector, personal=personal),
            usuario=UsuarioRefResponse.desde(m.usuario) if personal and m.usuario else None,
            observacion=m.observacion,
        )


class MovimientoResponse(BaseModel):
    """Movimiento del historial de un remito (solo lo ve el personal)."""

    estado_anterior: str | None
    estado_nuevo: str
    fecha_hora: datetime
    usuario: UsuarioRefResponse | None
    observacion: str | None

    @classmethod
    def desde(cls, m: MovimientoRemito) -> "MovimientoResponse":
        return cls(
            estado_anterior=m.estado_anterior.value if m.estado_anterior else None,
            estado_nuevo=m.estado_nuevo.value,
            fecha_hora=m.fecha_hora,
            usuario=UsuarioRefResponse.desde(m.usuario) if m.usuario else None,
            observacion=m.observacion,
        )


class LineaResponse(BaseModel):
    ejemplar_id: int
    codigo_ejemplar: str | None
    libro: str | None
    prestamo_id: int | None
    estado_fisico_salida: str
    estado_fisico_llegada: str | None
    resultado: str | None
    observacion: str | None

    @classmethod
    def desde(cls, linea: LineaRemito) -> "LineaResponse":
        return cls(
            ejemplar_id=linea.ejemplar_id,
            codigo_ejemplar=linea.codigo_ejemplar,
            libro=linea.libro_titulo,
            prestamo_id=linea.prestamo_id,
            estado_fisico_salida=linea.estado_fisico_salida.value,
            estado_fisico_llegada=(
                linea.estado_fisico_llegada.value if linea.estado_fisico_llegada else None
            ),
            resultado=linea.resultado.value if linea.resultado else None,
            observacion=linea.observacion,
        )


class RemitoResponse(BaseModel):
    id: int
    numero: str
    motivo: str
    estado: str
    sede_origen_id: int
    sede_origen: str | None
    sede_destino_id: int
    sede_destino: str | None
    fecha_generacion: datetime | None
    fecha_despacho: datetime | None
    fecha_recepcion: datetime | None
    observaciones: str | None
    lineas: list[LineaResponse]
    despachar_hasta: date | None
    atrasado: bool

    @classmethod
    def desde(cls, r: Remito) -> "RemitoResponse":
        assert r.id is not None
        return cls(
            id=r.id,
            numero=r.numero,
            motivo=r.motivo.value,
            estado=r.estado_nombre.value,
            sede_origen_id=r.sede_origen_id,
            sede_origen=r.sede_origen_nombre,
            sede_destino_id=r.sede_destino_id,
            sede_destino=r.sede_destino_nombre,
            fecha_generacion=r.fecha_generacion,
            fecha_despacho=r.fecha_despacho,
            fecha_recepcion=r.fecha_recepcion,
            observaciones=r.observaciones,
            lineas=[LineaResponse.desde(linea) for linea in r.lineas],
            despachar_hasta=r.despachar_hasta,
            atrasado=r.atrasado,
        )


class RemitoResumenResponse(BaseModel):
    """Remito asociado a un préstamo (lo que ve también el socio)."""

    id: int
    numero: str
    motivo: str
    estado: str
    fecha_despacho: datetime | None
    fecha_recepcion: datetime | None

    @classmethod
    def desde(cls, r: Remito) -> "RemitoResumenResponse":
        assert r.id is not None
        return cls(
            id=r.id,
            numero=r.numero,
            motivo=r.motivo.value,
            estado=r.estado_nombre.value,
            fecha_despacho=r.fecha_despacho,
            fecha_recepcion=r.fecha_recepcion,
        )


class _Detalle(BaseModel):
    """Lo que agrega la ficha: historial, remitos de ida y vuelta, devolución y multa."""

    historial: list[MovimientoPrestamoResponse]
    remitos: list[RemitoResumenResponse]
    devolucion: DevolucionResponse | None = None
    multa: MultaResponse | None = None


class PrestamoDetallePropioResponse(PrestamoPropioResponse, _Detalle):
    """Ficha que ve el socio."""


class PrestamoDetallePersonalResponse(PrestamoPersonalResponse, _Detalle):
    """Ficha que ve el personal."""


PrestamoDetalleResponse = PrestamoDetallePersonalResponse | PrestamoDetallePropioResponse


def detalle_a_response(d: DetallePrestamo, lector: Usuario) -> PrestamoDetalleResponse:
    detalle: dict[str, Any] = {
        "historial": [MovimientoPrestamoResponse.desde(m, lector) for m in d.historial],
        "remitos": [RemitoResumenResponse.desde(r) for r in d.remitos],
        "devolucion": DevolucionResponse.desde(d.devolucion) if d.devolucion else None,
        "multa": MultaResponse.desde(d.multa) if d.multa else None,
    }
    if not _es_personal(lector):
        return PrestamoDetallePropioResponse(**_campos(d.prestamo), **detalle)
    return PrestamoDetallePersonalResponse(
        **_campos(d.prestamo), registrado_por=_registrado_por(d.prestamo), **detalle
    )


class SedeRefResponse(BaseModel):
    id: int
    nombre: str


class PropuestaPrestamoResponse(BaseModel):
    """Qué préstamo se haría si el socio confirma ahora (no aparta nada).

    ``retiro_hasta`` solo en el local; en el interbibliotecario el plazo de retiro empieza
    cuando el ejemplar llega a la sede destino.
    """

    tipo: str
    libro_id: int
    libro: str
    sede_origen: SedeRefResponse
    sede_destino: SedeRefResponse
    plazo_dias: int
    retiro_hasta: date | None

    @classmethod
    def desde(cls, p: PropuestaPrestamo) -> "PropuestaPrestamoResponse":
        assert p.sede_origen.id is not None and p.sede_destino.id is not None
        return cls(
            tipo=p.tipo.value,
            libro_id=p.libro_id,
            libro=p.libro_titulo,
            sede_origen=SedeRefResponse(id=p.sede_origen.id, nombre=p.sede_origen.nombre),
            sede_destino=SedeRefResponse(id=p.sede_destino.id, nombre=p.sede_destino.nombre),
            plazo_dias=p.plazo_dias,
            retiro_hasta=p.retiro_hasta,
        )


class SedeResponsableResponse(BaseModel):
    id: int
    nombre: str | None


class IncidenciaResponse(BaseModel):
    """Incidencia de un remito.

    El responsable es la sede origen, que despachó el envío (``sede_responsable``); quién lo
    despachó es ``despachado_por``. ``usuario`` es quien la registró. Un extravío resuelto
    (el ejemplar apareció) trae ``resuelta_en`` y ``resolucion``.
    """

    id: int | None
    tipo: str
    origen: str
    ejemplar_id: int
    descripcion: str
    fecha: datetime
    usuario: UsuarioRefResponse | None
    sede_responsable: SedeResponsableResponse | None
    despachado_por: UsuarioRefResponse | None
    resuelta_en: datetime | None
    resolucion: str | None

    @classmethod
    def desde(cls, i: Incidencia, despachado_por: UsuarioRef | None = None) -> "IncidenciaResponse":
        return cls(
            id=i.id,
            tipo=i.tipo.value,
            origen=i.origen.value,
            ejemplar_id=i.ejemplar_id,
            descripcion=i.descripcion,
            fecha=i.fecha,
            usuario=UsuarioRefResponse.desde(i.usuario) if i.usuario else None,
            sede_responsable=(
                SedeResponsableResponse(id=i.sede_responsable_id, nombre=i.sede_responsable_nombre)
                if i.sede_responsable_id is not None
                else None
            ),
            despachado_por=UsuarioRefResponse.desde(despachado_por) if despachado_por else None,
            resuelta_en=i.resuelta_en,
            resolucion=i.resolucion,
        )


class RemitoDetalleResponse(RemitoResponse):
    """Remito con sus movimientos (trazabilidad) e incidencias."""

    movimientos: list[MovimientoResponse]
    incidencias: list[IncidenciaResponse]

    @classmethod
    def desde_detalle(cls, d: DetalleRemito) -> "RemitoDetalleResponse":
        despacho = next(
            (m for m in d.historial if m.estado_nuevo == EstadoRemitoEnum.DESPACHADO), None
        )
        despachado_por = despacho.usuario if despacho else None
        return cls(
            **RemitoResponse.desde(d.remito).model_dump(),
            movimientos=[MovimientoResponse.desde(m) for m in d.historial],
            incidencias=[IncidenciaResponse.desde(i, despachado_por) for i in d.incidencias],
        )


class PaginaPrestamosResponse(BaseModel):
    items: list[PrestamoResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Prestamo], lector: Usuario) -> "PaginaPrestamosResponse":
        return cls(
            items=[prestamo_a_response(p, lector) for p in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )


class PaginaRemitosResponse(BaseModel):
    items: list[RemitoResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Remito]) -> "PaginaRemitosResponse":
        return cls(
            items=[RemitoResponse.desde(r) for r in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )


class TareaResponse(BaseModel):
    tarea: str
    cambios: int


class ParametroResponse(BaseModel):
    clave: str
    valor: str
    descripcion: str

    @classmethod
    def desde(cls, p: Parametro) -> "ParametroResponse":
        return cls(clave=p.clave, valor=p.valor, descripcion=p.descripcion)
