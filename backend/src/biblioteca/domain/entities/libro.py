"""Libro: la obra del catálogo de la red (no la copia física, que es el Ejemplar)."""

from dataclasses import dataclass, field

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.errors import DatoInvalido


def normalizar_nombre(nombre: str) -> str:
    """Clave anti-duplicados de autores: sin mayúsculas, tildes ni espacios repetidos."""
    sin_tildes = nombre.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
    return " ".join(sin_tildes.split())


@dataclass
class Libro:
    isbn: Isbn
    titulo: str
    autores: list[str]
    editorial: str | None = None
    anio_publicacion: int | None = None
    categoria_id: int | None = None
    id: int | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        self.titulo = " ".join(self.titulo.split())
        if not self.titulo:
            raise DatoInvalido("El título es obligatorio")

        # Autores sin repetir (comparando nombres normalizados) y en el orden de autoría.
        vistos: set[str] = set()
        autores = []
        for nombre in (" ".join(a.split()) for a in self.autores):
            if nombre and normalizar_nombre(nombre) not in vistos:
                vistos.add(normalizar_nombre(nombre))
                autores.append(nombre)
        if not autores:
            raise DatoInvalido("Indicar al menos un autor")
        self.autores = autores

        self.editorial = " ".join(self.editorial.split()) if self.editorial else None
        if self.anio_publicacion is not None and self.anio_publicacion <= 0:
            raise DatoInvalido("El año de publicación debe ser positivo")
