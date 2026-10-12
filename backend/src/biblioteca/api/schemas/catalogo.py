from datetime import date

from pydantic import BaseModel, Field

from biblioteca.domain.enums import CondicionFisica, EstadoEjemplar, MotivoBaja


class LibroIn(BaseModel):
    """Alta de libro. El ISBN puede venir con guiones y como ISBN-10."""

    isbn: str = Field(min_length=10, max_length=17)
    titulo: str = Field(min_length=1, max_length=255)
    autores: list[str] = Field(min_length=1)
    editorial: str | None = Field(default=None, max_length=150)
    anio_publicacion: int | None = None
    categoria_id: int | None = None


class CreadoOut(BaseModel):
    id: int


class CategoriaOut(BaseModel):
    id: int
    nombre: str


class LibroOut(BaseModel):
    id: int
    isbn: str
    titulo: str
    editorial: str | None
    anio_publicacion: int | None
    categoria: str | None
    autores: list[str]
    ejemplares: int
    disponibles: int


class EjemplarOut(BaseModel):
    id: int
    codigo_inventario: str
    libro_id: int
    titulo: str
    sede_id: int
    sede: str
    estado: EstadoEjemplar
    condicion_fisica: CondicionFisica
    prestable: bool
    fecha_alta: date
    motivo_baja: MotivoBaja | None


class DisponibilidadSedeOut(BaseModel):
    sede_id: int
    sede: str
    sede_activa: bool
    total: int
    disponibles: int
    prestados: int
    reservados: int
    en_transito: int
    en_revision: int
    consulta_en_sala: int


class DisponibilidadLibroOut(BaseModel):
    libro_id: int
    titulo: str
    isbn: str
    disponibles: int
    sedes: list[DisponibilidadSedeOut]
