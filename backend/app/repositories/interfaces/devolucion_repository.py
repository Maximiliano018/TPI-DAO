"""Puertos de devoluciones y multas."""

from dataclasses import dataclass
from typing import Protocol

from app.models.devolucion import Devolucion, EstadoMulta, Multa


@dataclass(frozen=True)
class FiltroMultas:
    socio_id: int | None = None
    estado: EstadoMulta | None = None


class DevolucionRepository(Protocol):
    def agregar(self, devolucion: Devolucion) -> None: ...

    def de_prestamo(self, prestamo_id: int) -> Devolucion | None: ...


class MultaRepository(Protocol):
    def agregar(self, multa: Multa) -> None: ...

    def guardar(self, multa: Multa) -> None: ...

    def obtener(self, multa_id: int) -> Multa | None: ...

    def obtener_para_modificar(self, multa_id: int) -> Multa | None: ...

    def de_prestamo(self, prestamo_id: int) -> Multa | None: ...

    def listar(self, filtro: FiltroMultas, page: int, size: int) -> tuple[list[Multa], int]: ...
