"""Cuerpos de entrada de la API del catálogo. El formato de cada dato lo valida el dominio."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.ejemplar import EstadoFisico
from app.models.libro import TipoMaterial
from app.services.catalogo_service import DatosEjemplarNuevo, DatosLibroNuevo


class LibroRequest(BaseModel):
    """Alta de un libro (la obra)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn": "9780132350884",
                "titulo": "Clean Code",
                "autores": ["Robert C. Martin"],
                "editorial": "Prentice Hall",
                "anio_edicion": 2008,
                "categoria_id": 8,
                "tipo_material": "LIBRO",
            }
        }
    )

    isbn: str | None = Field(default=None, max_length=30)
    titulo: str = Field(max_length=400)
    autores: list[str] = Field(max_length=20)
    editorial: str | None = Field(default=None, max_length=200)
    anio_edicion: int | None = None
    categoria_id: int
    tipo_material: TipoMaterial = TipoMaterial.LIBRO

    def a_datos(self) -> DatosLibroNuevo:
        return DatosLibroNuevo(
            isbn=self.isbn,
            titulo=self.titulo,
            autores=self.autores,
            editorial=self.editorial,
            anio_edicion=self.anio_edicion,
            categoria_id=self.categoria_id,
            tipo_material=self.tipo_material,
        )


class LibroModificarRequest(LibroRequest):
    """Modificación de un libro; ``version`` evita pisar cambios de otra persona."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn": "9780132350884",
                "titulo": "Clean Code",
                "autores": ["Robert C. Martin"],
                "editorial": "Prentice Hall",
                "anio_edicion": 2008,
                "categoria_id": 8,
                "tipo_material": "LIBRO",
                "version": 1,
            }
        }
    )

    version: int


class EjemplarCrearRequest(BaseModel):
    """Alta de un ejemplar. La sede es la del bibliotecario; el administrador la indica."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"libro_id": 12, "codigo_inventario": "CEN-000123", "estado_fisico": "BUENO"}
        }
    )

    libro_id: int
    codigo_inventario: str = Field(max_length=60)
    estado_fisico: EstadoFisico = EstadoFisico.BUENO
    observaciones: str | None = Field(default=None, max_length=600)
    sede_id: int | None = None

    def a_datos(self) -> DatosEjemplarNuevo:
        return DatosEjemplarNuevo(
            libro_id=self.libro_id,
            codigo_inventario=self.codigo_inventario,
            estado_fisico=self.estado_fisico,
            observaciones=self.observaciones,
            sede_id=self.sede_id,
        )


class EjemplarModificarRequest(BaseModel):
    """Estado físico y observaciones; ``version`` evita pisar cambios de otra persona."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"estado_fisico": "REGULAR", "observaciones": None, "version": 1}
        }
    )

    estado_fisico: EstadoFisico
    observaciones: str | None = Field(default=None, max_length=600)
    version: int


class EjemplarBajaRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"motivo": "Hojas arrancadas, irrecuperable", "version": 3}}
    )

    motivo: str = Field(max_length=500)
    version: int


class VersionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"version": 4}})

    version: int
