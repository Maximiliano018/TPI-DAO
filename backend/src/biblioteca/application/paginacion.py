from dataclasses import dataclass

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200


@dataclass(frozen=True, slots=True)
class Pagina[T]:
    """Resultado de un listado paginado con `limite` y `desde` (offset)."""

    items: list[T]
    total: int
    limite: int
    desde: int
