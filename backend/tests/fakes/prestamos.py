"""Repositorios de préstamos y remitos en memoria (para la composición de verificadores).

Los casos de uso de préstamos y remitos se prueban contra PostgreSQL (``tests/controllers``),
porque dependen de bloqueos de fila y de varias tablas a la vez.
"""

from app.models.parametros import Parametros
from app.models.prestamo import Prestamo
from app.models.remito import Remito


class ParametroRepositorioEnMemoria:
    def __init__(self, parametros: Parametros | None = None) -> None:
        self.parametros = parametros or Parametros()

    def vigentes(self) -> Parametros:
        return self.parametros


class PrestamoRepositorioEnMemoria:
    def __init__(self) -> None:
        self.prestamos: dict[int, Prestamo] = {}

    def en_curso_de_sede(self, sede_id: int, limite: int) -> tuple[list[Prestamo], int]:
        lista = [p for p in self.prestamos.values() if p.esta_abierto and p.interviene(sede_id)]
        return lista[:limite], len(lista)


class RemitoRepositorioEnMemoria:
    def __init__(self) -> None:
        self.remitos: dict[int, Remito] = {}

    def abiertos_de_sede(self, sede_id: int, limite: int) -> tuple[list[Remito], int]:
        lista = [
            r
            for r in self.remitos.values()
            if r.esta_abierto and sede_id in (r.sede_origen_id, r.sede_destino_id)
        ]
        return lista[:limite], len(lista)
