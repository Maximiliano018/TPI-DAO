"""Respuestas de la API del catálogo.

El libro tiene un esquema por rol, como sedes y socios: la auditoría (quién lo cargó y lo
modificó), la versión y si se puede eliminar solo existen en el esquema del administrador.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.dtos.response.sede_response import CambioResponse, UsuarioRefResponse
from app.models.ejemplar import Ejemplar, MovimientoEjemplar
from app.models.libro import CategoriaRef, DisponibilidadLibro, Libro
from app.models.paginacion import Pagina
from app.models.usuario import Permiso, Usuario
from app.services.catalogo_service import DetalleEjemplar


class CategoriaResponse(BaseModel):
    id: int
    nombre: str

    @classmethod
    def desde(cls, categoria: CategoriaRef) -> "CategoriaResponse":
        return cls(id=categoria.id, nombre=categoria.nombre)


class LibroPublicoResponse(BaseModel):
    """Libro con su categoría y sus ejemplares (vigentes y disponibles en sedes activas)."""

    id: int
    isbn: str | None
    titulo: str
    autores: list[str]
    editorial: str | None
    anio_edicion: int | None
    categoria: CategoriaResponse
    tipo_material: str
    ejemplares: int
    disponibles: int


class LibroAdminResponse(LibroPublicoResponse):
    """Lo que ve el administrador: agrega la auditoría, la versión y si se puede eliminar."""

    eliminable: bool
    version: int
    creado_en: datetime | None
    creado_por: UsuarioRefResponse | None
    actualizado_en: datetime | None
    actualizado_por: UsuarioRefResponse | None


LibroResponse = LibroAdminResponse | LibroPublicoResponse


def libro_a_response(libro: Libro, usuario: Usuario) -> LibroResponse:
    """Arma el esquema que corresponde al rol del usuario."""
    assert libro.id is not None
    datos = libro.datos
    campos: dict[str, Any] = {
        "id": libro.id,
        "isbn": datos.isbn.valor if datos.isbn else None,
        "titulo": datos.titulo,
        "autores": list(datos.autores),
        "editorial": datos.editorial,
        "anio_edicion": datos.anio_edicion,
        "categoria": CategoriaResponse.desde(datos.categoria),
        "tipo_material": datos.tipo_material.value,
        "ejemplares": libro.cantidad_ejemplares,
        "disponibles": libro.disponibles,
    }
    if not usuario.puede(Permiso.CATALOGO_ADMINISTRAR):
        return LibroPublicoResponse(**campos)
    return LibroAdminResponse(
        **campos,
        eliminable=libro.eliminable,
        version=libro.version,
        creado_en=libro.creado_en,
        creado_por=UsuarioRefResponse.desde(libro.creado_por) if libro.creado_por else None,
        actualizado_en=libro.actualizado_en,
        actualizado_por=(
            UsuarioRefResponse.desde(libro.actualizado_por) if libro.actualizado_por else None
        ),
    )


class PaginaLibrosResponse(BaseModel):
    items: list[LibroResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Libro], usuario: Usuario) -> "PaginaLibrosResponse":
        return cls(
            items=[libro_a_response(libro, usuario) for libro in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )


class TotalRedResponse(BaseModel):
    totales: int
    disponibles: int


class DisponibilidadSedeResponse(BaseModel):
    sede_id: int
    sede: str
    totales: int
    disponibles: int
    prestados: int
    reservados: int
    en_transito: int
    otros: int


class DisponibilidadResponse(BaseModel):
    """Disponibilidad de un libro por sede activa (los ejemplares dados de baja no cuentan)."""

    libro_id: int
    titulo: str
    total_red: TotalRedResponse
    por_sede: list[DisponibilidadSedeResponse]

    @classmethod
    def desde(cls, d: DisponibilidadLibro) -> "DisponibilidadResponse":
        return cls(
            libro_id=d.libro_id,
            titulo=d.titulo,
            total_red=TotalRedResponse(totales=d.totales, disponibles=d.disponibles),
            por_sede=[
                DisponibilidadSedeResponse(
                    sede_id=s.sede_id,
                    sede=s.sede,
                    totales=s.totales,
                    disponibles=s.disponibles,
                    prestados=s.prestados,
                    reservados=s.reservados,
                    en_transito=s.en_transito,
                    otros=s.otros,
                )
                for s in d.por_sede
            ],
        )


class EjemplarResponse(BaseModel):
    id: int
    codigo_inventario: str
    libro_id: int
    libro: str | None
    sede_propietaria_id: int
    sede_propietaria: str | None
    sede_actual_id: int
    sede_actual: str | None
    estado_fisico: str
    estado: str
    observaciones: str | None
    fecha_baja: datetime | None
    motivo_baja: str | None
    version: int

    @classmethod
    def desde(cls, e: Ejemplar) -> "EjemplarResponse":
        assert e.id is not None
        return cls(
            id=e.id,
            codigo_inventario=e.codigo_inventario,
            libro_id=e.libro_id,
            libro=e.libro_titulo,
            sede_propietaria_id=e.sede_propietaria_id,
            sede_propietaria=e.sede_propietaria_nombre,
            sede_actual_id=e.sede_actual_id,
            sede_actual=e.sede_actual_nombre,
            estado_fisico=e.estado_fisico.value,
            estado=e.estado_nombre.value,
            observaciones=e.observaciones,
            fecha_baja=e.fecha_baja,
            motivo_baja=e.motivo_baja,
            version=e.version,
        )


class MovimientoResponse(BaseModel):
    """Un movimiento del historial del ejemplar.

    ``tipo``: ``ALTA``, ``CAMBIO_DE_ESTADO``, ``TRASLADO`` (cambia la sede propietaria),
    ``CAMBIO_DE_UBICACION`` (cambia dónde está) o ``MODIFICACION`` (estado físico u
    observaciones). ``cambios`` trae los campos que cambiaron; las sedes, por nombre.
    """

    tipo: str
    estado_anterior: str | None
    estado_nuevo: str
    fecha_hora: datetime
    usuario: UsuarioRefResponse | None
    observacion: str | None
    cambios: list[CambioResponse]

    @classmethod
    def desde(cls, m: MovimientoEjemplar) -> "MovimientoResponse":
        return cls(
            tipo=m.tipo.value,
            estado_anterior=m.estado_anterior.value if m.estado_anterior else None,
            estado_nuevo=m.estado_nuevo.value,
            fecha_hora=m.fecha_hora,
            usuario=UsuarioRefResponse.desde(m.usuario) if m.usuario else None,
            observacion=m.observacion,
            cambios=[
                CambioResponse(campo=c.campo, antes=c.antes, despues=c.despues) for c in m.cambios
            ],
        )


class EjemplarDetalleResponse(EjemplarResponse):
    """Ejemplar con su historial: estados, estado físico y sedes (trazabilidad, RF-CAT-06)."""

    historial: list[MovimientoResponse]

    @classmethod
    def desde_detalle(cls, d: DetalleEjemplar) -> "EjemplarDetalleResponse":
        return cls(
            **EjemplarResponse.desde(d.ejemplar).model_dump(),
            historial=[MovimientoResponse.desde(m) for m in d.historial],
        )


class PaginaEjemplaresResponse(BaseModel):
    items: list[EjemplarResponse]
    total: int
    page: int
    size: int

    @classmethod
    def desde(cls, pagina: Pagina[Ejemplar]) -> "PaginaEjemplaresResponse":
        return cls(
            items=[EjemplarResponse.desde(e) for e in pagina.items],
            total=pagina.total,
            page=pagina.page,
            size=pagina.size,
        )
