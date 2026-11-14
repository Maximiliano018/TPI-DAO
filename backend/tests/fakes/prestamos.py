"""Repositorios de préstamos, remitos y reservas en memoria (lo mínimo para los servicios que los
consultan de paso: verificadores de baja de sede y baja de socios).

Los casos de uso de préstamos, remitos y reservas se prueban contra PostgreSQL
(``tests/controllers``), porque dependen de bloqueos de fila y de varias tablas a la vez.
"""

from app.models.incidencia import Incidencia, TipoIncidencia
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


class IncidenciaRepositorioEnMemoria:
    def __init__(self) -> None:
        self.incidencias: list[Incidencia] = []

    def agregar(self, incidencia: Incidencia) -> None:
        incidencia.id = len(self.incidencias) + 1
        self.incidencias.append(incidencia)

    def guardar(self, incidencia: Incidencia) -> None:
        assert incidencia in self.incidencias

    def de_remito(self, remito_id: int) -> list[Incidencia]:
        return [i for i in self.incidencias if i.remito_id == remito_id]

    def extravio_pendiente(self, ejemplar_id: int) -> Incidencia | None:
        pendientes = [
            i
            for i in self.incidencias
            if i.ejemplar_id == ejemplar_id and i.tipo == TipoIncidencia.EXTRAVIO and not i.resuelta
        ]
        return pendientes[-1] if pendientes else None
