"""Políticas de plazo de préstamo (patrón Strategy).

El plazo depende del tipo de préstamo: 14 días el local y 21 el interbibliotecario, contados desde
la **entrega** al socio. Cada política es intercambiable: el préstamo solo conoce la interfaz
``PoliticaPlazo``, así que sumar otra (por ejemplo, un plazo por categoría de libro) no lo cambia.
"""

from datetime import date, timedelta
from typing import Protocol


class PoliticaPlazo(Protocol):
    """Calcula la fecha de vencimiento a partir de una fecha de inicio."""

    dias: int  # duración del plazo, para informarla antes de pedir el préstamo

    def vencimiento(self, inicio: date) -> date:
        """Último día válido para devolver (el día de vencimiento todavía está en término)."""
        ...


class PlazoEnDias:
    """Plazo de una cantidad fija de días corridos."""

    def __init__(self, dias: int) -> None:
        self.dias = dias

    def vencimiento(self, inicio: date) -> date:
        return inicio + timedelta(days=self.dias)


class PlazoLocal(PlazoEnDias):
    """Préstamo retirado en la misma sede del ejemplar (parámetro ``plazo_prestamo_local_dias``)."""


class PlazoInterbibliotecario(PlazoEnDias):
    """Préstamo entre sedes (``plazo_prestamo_inter_dias``), desde la entrega en destino."""
