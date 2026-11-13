"""Repositorios de préstamos, remitos y reservas en memoria (lo mínimo para los servicios que los
consultan de paso: verificadores de baja de sede y baja de socios).

Los casos de uso de préstamos, remitos y reservas se prueban contra PostgreSQL
(``tests/controllers``), porque dependen de bloqueos de fila y de varias tablas a la vez.
"""

from app.models.parametros import Parametros
from app.models.prestamo import Prestamo
from app.models.remito import Remito
from app.models.reserva import Reserva


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


class ReservaRepositorioEnMemoria:
    def __init__(self) -> None:
        self.reservas: dict[int, Reserva] = {}

    def activas_de_sede(self, sede_id: int, limite: int) -> tuple[list[Reserva], int]:
        lista = [r for r in self.reservas.values() if r.esta_activa and r.sede_retiro_id == sede_id]
        return lista[:limite], len(lista)

    def activas_de_socio(self, socio_id: int) -> list[Reserva]:
        return [r for r in self.reservas.values() if r.esta_activa and r.socio_id == socio_id]

    def guardar(self, reserva: Reserva) -> None:
        assert reserva.id in self.reservas
