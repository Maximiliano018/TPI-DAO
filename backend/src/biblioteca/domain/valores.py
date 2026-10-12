"""Objetos valor del dominio: inmutables y válidos desde su creación."""

import re
from dataclasses import dataclass
from typing import Self

from biblioteca.domain.errors import DatoInvalido


def digito_verificador_isbn13(primeros_12: str) -> str:
    """Dígito verificador de un ISBN-13 (pesos alternados 1 y 3)."""
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(primeros_12))
    return str((10 - suma % 10) % 10)


def _isbn10_valido(isbn: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", isbn):
        return False
    suma = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(isbn))
    return suma % 11 == 0


@dataclass(frozen=True, slots=True)
class Isbn:
    """ISBN normalizado a 13 dígitos. Acepta ISBN-10 y ISBN-13, con o sin guiones."""

    valor: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"\d{13}", self.valor):
            raise DatoInvalido(f"El ISBN debe tener 13 dígitos: {self.valor!r}")
        if self.valor[-1] != digito_verificador_isbn13(self.valor[:12]):
            raise DatoInvalido(f"El dígito verificador del ISBN {self.valor} no es válido")

    @classmethod
    def desde_texto(cls, texto: str) -> Self:
        limpio = re.sub(r"[\s-]", "", texto).upper()
        if len(limpio) == 10:
            if not _isbn10_valido(limpio):
                raise DatoInvalido(f"El ISBN-10 {texto!r} no es válido")
            base = "978" + limpio[:9]
            return cls(base + digito_verificador_isbn13(base))
        return cls(limpio)

    def __str__(self) -> str:
        return self.valor


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
