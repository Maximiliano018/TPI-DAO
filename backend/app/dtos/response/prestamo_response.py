"""Respuestas de préstamos, remitos y parámetros."""

from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.response.sede_response import UsuarioRefResponse
from app.models.incidencia import Incidencia
from app.models.paginacion import Pagina
from app.models.prestamo import MovimientoPrestamo, Prestamo
from app.models.remito import LineaRemito, MovimientoRemito, Remito
from app.repositories.interfaces.prestamo_repository import Parametro
from app.services.prestamo_service import DetallePrestamo
from app.services.remito_service import DetalleRemito


class PrestamoResponse(BaseModel):
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
    renovaciones: int
    registrado_por: UsuarioRefResponse | None

    @classmethod
    def desde(cls, p: Prestamo) -> "PrestamoResponse":
        assert p.id is not None
        return cls(
            id=p.id,
            numero=p.numero,
            tipo=p.tipo.value,
            estado=p.estado_nombre.value,
            socio_id=p.socio_id,
            socio=p.socio_nombre,
            numero_socio=p.numero_socio,
            ejemplar_id=p.ejemplar_id,
            codigo_ejemplar=p.codigo_ejemplar,
            libro_id=p.libro_id,
            libro=p.libro_titulo,
            sede_origen_id=p.sede_origen_id,
            sede_origen=p.sede_origen_nombre,
            sede_destino_id=p.sede_destino_id,
            sede_destino=p.sede_destino_nombre,
            fecha_solicitud=p.fecha_solicitud,
            fecha_inicio=p.fecha_inicio,
            fecha_vencimiento=p.fecha_vencimiento,
            fecha_devolucion=p.fecha_devolucion,
            renovaciones=p.renovaciones,
            registrado_por=UsuarioRefResponse.desde(p.registrado_por) if p.registrado_por else None,
        )


class MovimientoResponse(BaseModel):
    estado_anterior: str | None
    estado_nuevo: str
    fecha_hora: datetime
    usuario: UsuarioRefResponse | None
    observacion: str | None

    @classmethod
    def desde(cls, m: MovimientoPrestamo | MovimientoRemito) -> "MovimientoResponse":
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


class PrestamoDetalleResponse(PrestamoResponse):
    """Préstamo con su historial y los remitos de ida y vuelta (RF-PRE-15)."""

    historial: list[MovimientoResponse]
    remitos: list[RemitoResumenResponse]

    @classmethod
    def desde_detalle(cls, d: DetallePrestamo) -> "PrestamoDetalleResponse":
        return cls(
            **PrestamoResponse.desde(d.prestamo).model_dump(),
            historial=[MovimientoResponse.desde(m) for m in d.historial],
            remitos=[RemitoResumenResponse.desde(r) for r in d.remitos],
        )


class IncidenciaResponse(BaseModel):
    tipo: str
    ejemplar_id: int
    descripcion: str
    fecha: datetime

    @classmethod
    def desde(cls, i: Incidencia) -> "IncidenciaResponse":
        return cls(
            tipo=i.tipo.value, ejemplar_id=i.ejemplar_id, descripcion=i.descripcion, fecha=i.fecha
        )


class RemitoDetalleResponse(RemitoResponse):
    """Remito con sus movimientos (trazabilidad) e incidencias."""

    movimientos: list[MovimientoResponse]
    incidencias: list[IncidenciaResponse]

    @classmethod
    def desde_detalle(cls, d: DetalleRemito) -> "RemitoDetalleResponse":
        return cls(
            **RemitoResponse.desde(d.remito).model_dump(),
            movimientos=[MovimientoResponse.desde(m) for m in d.historial],
            incidencias=[IncidenciaResponse.desde(i) for i in d.incidencias],
        )


class PaginaPrestamosResponse(BaseModel):
    items: list[PrestamoResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Prestamo]) -> "PaginaPrestamosResponse":
        return cls(
            items=[PrestamoResponse.desde(p) for p in pagina.items],
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
