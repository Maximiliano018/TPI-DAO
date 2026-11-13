"""Políticas de cálculo de multa (patrón Strategy).

La multa es una política intercambiable: hoy un monto fijo por día de atraso (con tope opcional);
mañana podría ser escalonada, sin tocar ``Devolucion`` ni el servicio que la usa.
"""

from decimal import Decimal
from typing import Protocol


class PoliticaMulta(Protocol):
    """Calcula el monto de la multa a partir de los días de atraso."""

    @property
    def monto_por_dia(self) -> Decimal: ...

    def calcular(self, dias_atraso: int) -> Decimal: ...


class MultaFijaPorDia:
    """``días × monto por día``; si hay ``tope``, no lo supera (CU-DEV-02, A2)."""

    def __init__(self, monto_por_dia: Decimal, tope: Decimal | None = None) -> None:
        self._monto_por_dia = monto_por_dia
        self._tope = tope

    @property
    def monto_por_dia(self) -> Decimal:
        return self._monto_por_dia

    def calcular(self, dias_atraso: int) -> Decimal:
        total = self._monto_por_dia * max(dias_atraso, 0)
        if self._tope is not None:
            total = min(total, self._tope)
        return total.quantize(Decimal("0.01"))
