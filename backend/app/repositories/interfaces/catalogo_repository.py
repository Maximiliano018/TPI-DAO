"""Puertos de acceso al catálogo: categorías, libros y ejemplares."""

from dataclasses import dataclass
from typing import Protocol

from app.models.ejemplar import Ejemplar, MovimientoEjemplar
from app.models.libro import CategoriaRef, DisponibilidadLibro, Libro, TipoMaterial
from app.models.states.ejemplar import EstadoEjemplarEnum


@dataclass(frozen=True)
class FiltroLibros:
    """Búsqueda de libros. ``texto`` (normalizado) busca en título, autores e ISBN."""

    texto: str | None = None
    categoria_id: int | None = None
    tipo_material: TipoMaterial | None = None


@dataclass(frozen=True)
class FiltroEjemplares:
    sede_id: int | None = None
    libro_id: int | None = None
    estado: EstadoEjemplarEnum | None = None
    codigo: str | None = None


class CategoriaRepository(Protocol):
    def obtener(self, categoria_id: int) -> CategoriaRef | None: ...

    def listar(self) -> list[CategoriaRef]: ...


class LibroRepository(Protocol):
    """Acceso a libros. Los autores se buscan por nombre normalizado o se crean."""

    def agregar(self, libro: Libro) -> None:
        """Persiste un libro nuevo (asigna ``id``).

        Raises:
            LibroDuplicado: ISBN o clave natural repetidos (restricciones únicas de la base).
        """
        ...

    def guardar(self, libro: Libro) -> None: ...

    def obtener(self, libro_id: int) -> Libro | None:
        """Libro con su categoría, autores, auditoría y cantidad de ejemplares."""
        ...

    def obtener_para_modificar(self, libro_id: int) -> Libro | None:
        """Como ``obtener`` con la fila bloqueada (``FOR UPDATE``)."""
        ...

    def buscar_duplicado(
        self, isbn: str | None, clave_natural: str | None, excluir_id: int | None = None
    ) -> Libro | None:
        """Libro con el mismo ISBN o, si no tiene ISBN, con la misma clave natural."""
        ...

    def listar(self, filtro: FiltroLibros, page: int, size: int) -> tuple[list[Libro], int]:
        """Página de libros por título, con ejemplares totales y disponibles en sedes activas."""
        ...

    def eliminar(self, libro_id: int) -> None: ...

    def disponibilidad(self, libro_id: int) -> DisponibilidadLibro:
        """Ejemplares del libro por sede propietaria **activa** y por estado (sin las bajas)."""
        ...


class EjemplarRepository(Protocol):
    """Acceso a ejemplares; guardar persiste también los movimientos pendientes."""

    def agregar(self, ejemplar: Ejemplar) -> None:
        """Persiste un ejemplar nuevo y su primer movimiento.

        Raises:
            EjemplarCodigoDuplicado: El código de inventario ya existe en la red.
        """
        ...

    def guardar(self, ejemplar: Ejemplar) -> None: ...

    def obtener(self, ejemplar_id: int) -> Ejemplar | None: ...

    def obtener_para_modificar(self, ejemplar_id: int) -> Ejemplar | None:
        """Ejemplar con la fila bloqueada (``FOR UPDATE``), para cambiar su estado."""
        ...

    def obtener_por_codigo(self, codigo: str) -> Ejemplar | None: ...

    def listar(
        self, filtro: FiltroEjemplares, page: int, size: int
    ) -> tuple[list[Ejemplar], int]: ...

    def historial(self, ejemplar_id: int) -> list[MovimientoEjemplar]:
        """Movimientos del ejemplar, del más antiguo al más reciente."""
        ...

    def contar_de_libro(self, libro_id: int) -> int:
        """Ejemplares del libro (incluidos los dados de baja)."""
        ...

    def alojados_en_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        """Ejemplares (no dados de baja) que están físicamente en la sede."""
        ...

    def propios_fuera_de_sede(self, sede_id: int, limite: int) -> tuple[list[Ejemplar], int]:
        """Ejemplares de la sede (no dados de baja) que están en otra sede o en tránsito."""
        ...
