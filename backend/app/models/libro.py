"""Entidad de dominio ``Libro``: la obra del catálogo común de la red.

Libro y ejemplar son clases distintas: el libro es la obra (con ISBN, autores, editorial); el
ejemplar es la copia física con sede y estados propios (ver ``models/ejemplar.py``).
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.exceptions import ConflictoDeVersion
from app.models.usuario import UsuarioRef
from app.models.valores import error_de_campo
from app.utils.texto import normalizar

TITULO_MAX = 200
AUTOR_MAX = 100
MAX_AUTORES = 10
EDITORIAL_MAX = 100
ANIO_MINIMO = 1450  # imprenta de Gutenberg


class TipoMaterial(StrEnum):
    """Libros y otros materiales de consulta que presta la red."""

    LIBRO = "LIBRO"
    REVISTA = "REVISTA"
    OBRA_DE_REFERENCIA = "OBRA_DE_REFERENCIA"
    OTRO = "OTRO"


@dataclass(frozen=True)
class Isbn:
    """ISBN-10 o ISBN-13 con dígito verificador válido; se guarda sin guiones ni espacios."""

    valor: str

    @classmethod
    def crear(cls, texto: str) -> "Isbn":
        """Quita guiones y espacios y valida el dígito verificador.

        Raises:
            ErrorDeValidacion: Largo o dígito verificador inválidos.
        """
        valor = re.sub(r"[\s-]", "", texto or "").upper()
        if not (_isbn13_valido(valor) or _isbn10_valido(valor)):
            raise error_de_campo(
                "isbn", "El ISBN no es válido: revise los 10 o 13 dígitos y el verificador."
            )
        return cls(valor)


def _isbn13_valido(valor: str) -> bool:
    if not re.fullmatch(r"\d{13}", valor):
        return False
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(valor))
    return suma % 10 == 0


def _isbn10_valido(valor: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", valor):
        return False
    digitos = [10 if c == "X" else int(c) for c in valor]
    return sum(d * (10 - i) for i, d in enumerate(digitos)) % 11 == 0


@dataclass(frozen=True)
class CategoriaRef:
    """Categoría del catálogo cerrado (para búsquedas)."""

    id: int
    nombre: str


@dataclass(frozen=True)
class DatosLibro:
    """Datos de un libro ya validados (ver ``DatosLibro.crear``)."""

    isbn: Isbn | None
    titulo: str
    autores: tuple[str, ...]
    editorial: str | None
    anio_edicion: int | None
    categoria: CategoriaRef
    tipo_material: TipoMaterial

    @classmethod
    def crear(
        cls,
        *,
        isbn: str | None,
        titulo: str,
        autores: list[str],
        editorial: str | None,
        anio_edicion: int | None,
        categoria: CategoriaRef,
        tipo_material: TipoMaterial,
        anio_actual: int,
    ) -> "DatosLibro":
        """Valida los datos de la obra.

        Raises:
            ErrorDeValidacion: ISBN inválido, falta el título o un autor, o un dato fuera de rango.
        """
        isbn_ok = Isbn.crear(isbn) if isbn and isbn.strip() else None
        titulo_ok = " ".join((titulo or "").split())
        if not titulo_ok or len(titulo_ok) > TITULO_MAX:
            raise error_de_campo("titulo", "El título es obligatorio (hasta 200 caracteres).")
        autores_ok = tuple(a for a in (" ".join((x or "").split()) for x in autores) if a)
        if not autores_ok:
            raise error_de_campo("autores", "Indique al menos un autor.")
        if len(autores_ok) > MAX_AUTORES or any(len(a) > AUTOR_MAX for a in autores_ok):
            raise error_de_campo("autores", "Hasta 10 autores de 100 caracteres cada uno.")
        if len({normalizar(a) for a in autores_ok}) != len(autores_ok):
            raise error_de_campo("autores", "Hay autores repetidos.")
        editorial_ok = " ".join((editorial or "").split()) or None
        if editorial_ok and len(editorial_ok) > EDITORIAL_MAX:
            raise error_de_campo("editorial", "La editorial no puede superar los 100 caracteres.")
        if anio_edicion is not None and not ANIO_MINIMO <= anio_edicion <= anio_actual + 1:
            raise error_de_campo(
                "anio_edicion", f"El año de edición debe estar entre {ANIO_MINIMO} y el actual."
            )
        return cls(
            isbn_ok, titulo_ok, autores_ok, editorial_ok, anio_edicion, categoria, tipo_material
        )

    @property
    def clave_natural(self) -> str | None:
        """Identidad de un libro sin ISBN: título, primer autor, editorial y año normalizados.

        Con ISBN no hace falta: el ISBN ya identifica la edición.
        """
        if self.isbn is not None:
            return None
        partes = [self.titulo, self.autores[0], self.editorial or "", str(self.anio_edicion or "")]
        return "|".join(normalizar(p) for p in partes)


@dataclass
class Libro:
    """Obra del catálogo común a toda la red.

    Conteos (los completa el repositorio):

    - ``cantidad_ejemplares``: ejemplares vigentes (sin los dados de baja).
    - ``disponibles``: ejemplares ``Disponible`` en sedes activas.
    - ``ejemplares_registrados``: todos, incluidos los dados de baja (son historial y por eso
      impiden eliminar el libro, RF-CAT-08).
    """

    id: int | None
    datos: DatosLibro
    creado_en: datetime | None = None
    creado_por: UsuarioRef | None = None
    actualizado_en: datetime | None = None
    actualizado_por: UsuarioRef | None = None
    cantidad_ejemplares: int = 0
    disponibles: int = 0
    ejemplares_registrados: int = 0
    version: int = 1

    @classmethod
    def crear(cls, datos: DatosLibro, *, actor: UsuarioRef, ahora: datetime) -> "Libro":
        return cls(
            id=None,
            datos=datos,
            creado_en=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )

    def validar_version(self, version: int) -> None:
        """Concurrencia optimista: rechaza si otra persona lo modificó antes."""
        if version != self.version:
            raise ConflictoDeVersion(
                "Otra persona modificó el libro. Recargue para ver los cambios.",
                [{"campo": "version", "problema": "desactualizada"}],
            )

    def modificar(self, datos: DatosLibro, *, actor: UsuarioRef, ahora: datetime) -> bool:
        """Reemplaza los datos de la obra. Devuelve ``True`` si algo cambió."""
        if datos == self.datos:
            return False
        self.datos = datos
        self.actualizado_en = ahora
        self.actualizado_por = actor
        self.version += 1
        return True

    @property
    def titulo(self) -> str:
        return self.datos.titulo

    @property
    def eliminable(self) -> bool:
        """Solo se elimina un libro cargado por error, sin ningún ejemplar (RF-CAT-08)."""
        return self.ejemplares_registrados == 0


@dataclass(frozen=True)
class DisponibilidadSede:
    """Ejemplares de un libro en una sede activa, por estado (RF-CAT-09)."""

    sede_id: int
    sede: str
    totales: int
    disponibles: int
    prestados: int
    reservados: int
    en_transito: int
    otros: int  # apartados para un movimiento o en revisión


@dataclass(frozen=True)
class DisponibilidadLibro:
    """Disponibilidad de un libro en toda la red y por sede."""

    libro_id: int
    titulo: str
    por_sede: list[DisponibilidadSede]

    @property
    def totales(self) -> int:
        return sum(s.totales for s in self.por_sede)

    @property
    def disponibles(self) -> int:
        return sum(s.disponibles for s in self.por_sede)
