"""Elección de la sede origen de un préstamo solicitado por libro (RF-PRE-16).

Cuando el socio pide un libro (y no un ejemplar), el sistema decide el tipo de préstamo:

1. Si la sede destino tiene ejemplares disponibles, el préstamo es **local**.
2. Si no, es **interbibliotecario** desde la sede activa con **más** ejemplares disponibles; con
   empate, la de **menor id** (un criterio estable y fácil de explicar).
3. Si ninguna sede activa tiene disponibles, no hay préstamo posible (se ofrece reservar).

Es una función pura: recibe los conteos y no consulta la base, así se prueba aislada.
"""

from collections.abc import Mapping


def elegir_sede_origen(disponibles_por_sede: Mapping[int, int], sede_destino_id: int) -> int | None:
    """Sede de donde sale el ejemplar, o ``None`` si no hay disponibles en la red.

    Args:
        disponibles_por_sede: Ejemplares disponibles del libro por sede activa.
        sede_destino_id: Sede donde el socio retira y devuelve.
    """
    con_disponibles = {sede: n for sede, n in disponibles_por_sede.items() if n > 0}
    if not con_disponibles:
        return None
    if sede_destino_id in con_disponibles:
        return sede_destino_id
    return min(con_disponibles, key=lambda sede: (-con_disponibles[sede], sede))
