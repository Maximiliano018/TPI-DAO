"""Portadas de los libros de demostración (bajadas de Open Library, en ``frontend/public``).

El índice ``portadas_demo.json`` relaciona cada título del seed con su imagen
(``/portadas/<archivo>.jpg``), que el frontend sirve como archivo estático.
"""

import json
from functools import cache
from pathlib import Path

INDICE = Path(__file__).with_name("portadas_demo.json")


@cache
def _indice() -> dict[str, str]:
    if not INDICE.exists():
        return {}
    return json.loads(INDICE.read_text(encoding="utf-8"))


def portada_de(titulo: str) -> str | None:
    """La portada de un libro del seed, o ``None`` si no hay imagen."""
    return _indice().get(titulo)
