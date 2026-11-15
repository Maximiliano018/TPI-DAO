"""Políticas de cálculo de multa (patrón Strategy).

La multa es una política intercambiable, sin tocar ``Devolucion`` ni el servicio que la usa:

* **Atraso** (``PoliticaMulta``): hoy un monto fijo por día de atraso, con tope opcional; mañana
  podría ser escalonada.
* **Daño o extravío** (``PoliticaMultaPorIncidencia``): hoy un monto fijo por cada caso; mañana
  podría depender del valor de reposición del libro.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class TipoMulta(StrEnum):
    """Por qué se cobra: atraso en la devolución, o daño o extravío del ejemplar."""

    ATRASO = "ATRASO"
    DANIO = "DANIO"
    EXTRAVIO = "EXTRAVIO"


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


class PoliticaMultaPorIncidencia(Protocol):
    """Calcula la multa por un ejemplar devuelto dañado o informado como extraviado."""

    def calcular(self, tipo: TipoMulta) -> Decimal: ...


class MontoFijoPorIncidencia:
    """Un monto fijo por daño y otro por extravío; 0 = no se cobra (RF-DEV-23)."""

    def __init__(self, danio: Decimal, extravio: Decimal) -> None:
        self._montos = {TipoMulta.DANIO: danio, TipoMulta.EXTRAVIO: extravio}

    def calcular(self, tipo: TipoMulta) -> Decimal:
        monto = self._montos.get(tipo)
        if monto is None:
            raise ValueError(f"La multa por {tipo.value} no es por daño ni por extravío.")
        return monto.quantize(Decimal("0.01"))
