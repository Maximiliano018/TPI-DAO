"""Verificación de impedimentos de baja de una sede (Strategy + Composite).

El dominio define el **puerto** ``VerificadorImpedimentoBaja``; cada módulo (usuarios,
ejemplares, préstamos, remitos, reservas) aporta su implementación. ``VerificadorBajaSede`` las
agrupa. Así ``SedeService`` no conoce a los demás módulos ni cambia cuando aparece uno nuevo.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

MAX_ELEMENTOS_POR_IMPEDIMENTO = 10


class TipoImpedimento(StrEnum):
    """Causas que bloquean la baja de una sede."""

    PRESTAMOS_EN_CURSO = "PRESTAMOS_EN_CURSO"
    REMITOS_ABIERTOS = "REMITOS_ABIERTOS"
    RESERVAS_PENDIENTES = "RESERVAS_PENDIENTES"
    EJEMPLARES_EN_SEDE = "EJEMPLARES_EN_SEDE"
    EJEMPLARES_PROPIOS_FUERA = "EJEMPLARES_PROPIOS_FUERA"
    BIBLIOTECARIOS_ASIGNADOS = "BIBLIOTECARIOS_ASIGNADOS"


ETIQUETAS: dict[TipoImpedimento, tuple[str, str]] = {
    TipoImpedimento.PRESTAMOS_EN_CURSO: ("préstamo en curso", "préstamos en curso"),
    TipoImpedimento.REMITOS_ABIERTOS: ("remito abierto", "remitos abiertos"),
    TipoImpedimento.RESERVAS_PENDIENTES: ("reserva pendiente", "reservas pendientes"),
    TipoImpedimento.EJEMPLARES_EN_SEDE: (
        "ejemplar alojado en la sede",
        "ejemplares alojados en la sede",
    ),
    TipoImpedimento.EJEMPLARES_PROPIOS_FUERA: (
        "ejemplar propio fuera de la sede",
        "ejemplares propios fuera de la sede",
    ),
    TipoImpedimento.BIBLIOTECARIOS_ASIGNADOS: (
        "bibliotecario asignado",
        "bibliotecarios asignados",
    ),
}


@dataclass(frozen=True)
class ElementoImpedimento:
    """Un elemento concreto que impide la baja (para poder encontrarlo)."""

    id: int
    referencia: str
    estado: str


@dataclass(frozen=True)
class Impedimento:
    """Resultado de un verificador: cuántos elementos bloquean y una muestra."""

    tipo: TipoImpedimento
    cantidad: int
    elementos: list[ElementoImpedimento] = field(default_factory=list)

    @property
    def hay_mas(self) -> bool:
        """Verdadero si hay más elementos que los de la muestra."""
        return self.cantidad > len(self.elementos)

    def etiqueta(self) -> str:
        """Texto con cantidad, por ejemplo ``2 préstamos en curso``."""
        singular, plural = ETIQUETAS[self.tipo]
        return f"{self.cantidad} {singular if self.cantidad == 1 else plural}"

    def como_dict(self) -> dict[str, object]:
        """Forma de ``detalles`` en la respuesta de la API."""
        return {
            "tipo": self.tipo.value,
            "cantidad": self.cantidad,
            "hay_mas": self.hay_mas,
            "elementos": [
                {"id": e.id, "referencia": e.referencia, "estado": e.estado} for e in self.elementos
            ],
        }


class VerificadorImpedimentoBaja(Protocol):
    """Puerto: una verificación de un tipo de actividad pendiente."""

    tipo: TipoImpedimento

    def verificar(self, sede_id: int) -> Impedimento | None:
        """Devuelve el impedimento, o ``None`` si no hay nada que bloquee."""
        ...


class VerificadorBajaSede:
    """Compuesto: aplica todos los verificadores registrados."""

    def __init__(self, verificadores: Sequence[VerificadorImpedimentoBaja]) -> None:
        self._verificadores = list(verificadores)

    @property
    def tipos_cubiertos(self) -> set[TipoImpedimento]:
        """Tipos de impedimento con un verificador registrado."""
        return {v.tipo for v in self._verificadores}

    def verificar(self, sede_id: int) -> list[Impedimento]:
        """Impedimentos de todos los verificadores (lista vacía si la sede se puede dar de baja)."""
        return [i for v in self._verificadores if (i := v.verificar(sede_id)) is not None]
