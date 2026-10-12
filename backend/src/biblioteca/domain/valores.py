"""Objetos valor del dominio: inmutables y válidos desde su creación.

El ISBN está en `entities/isbn.py`."""

import re
from dataclasses import dataclass
from typing import Self

from biblioteca.domain.errors import DatoInvalido


@dataclass(frozen=True, slots=True)
class Dni:
    """DNI argentino: 7 u 8 dígitos. Acepta puntos y espacios al ingresarlo."""

    valor: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"\d{7,8}", self.valor):
            raise DatoInvalido(f"El DNI debe tener 7 u 8 dígitos: {self.valor!r}")

    @classmethod
    def desde_texto(cls, texto: str) -> Self:
        return cls(re.sub(r"[\s.]", "", texto))

    def __str__(self) -> str:
        return self.valor


def texto_requerido(valor: str, campo: str, largo_maximo: int) -> str:
    """Normaliza un texto obligatorio: sin espacios sobrantes, no vacío y acotado."""
    limpio = " ".join(valor.split())
    if not limpio:
        raise DatoInvalido(f"El campo {campo} es obligatorio")
    if len(limpio) > largo_maximo:
        raise DatoInvalido(f"El campo {campo} admite hasta {largo_maximo} caracteres")
    return limpio


def texto_opcional(valor: str | None, campo: str, largo_maximo: int) -> str | None:
    """Como `texto_requerido`, pero un texto vacío se guarda como None."""
    if valor is None or not valor.strip():
        return None
    return texto_requerido(valor, campo, largo_maximo)
