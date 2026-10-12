"""ISBN como objeto valor (ARCHITECTURE.md §4.3, Catálogo)."""

from dataclasses import dataclass

from biblioteca.domain.errors import IsbnInvalido


def digito_verificador_isbn13(primeros_12: str) -> str:
    """Pesos alternados 1 y 3; el dígito completa la suma a un múltiplo de 10."""
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(primeros_12))
    return str((10 - suma % 10) % 10)


def _isbn10_valido(isbn: str) -> bool:
    """Pesos 10 a 1; el último dígito puede ser X (= 10). La suma es múltiplo de 11."""
    if not (isbn[:9].isdigit() and (isbn[9].isdigit() or isbn[9] == "X")):
        return False
    valores = [int(d) for d in isbn[:9]] + [10 if isbn[9] == "X" else int(isbn[9])]
    return sum(v * peso for v, peso in zip(valores, range(10, 0, -1), strict=True)) % 11 == 0


@dataclass(frozen=True)
class Isbn:
    """ISBN-13 válido. Se crea con `Isbn.desde_texto`, que acepta guiones y espacios."""

    valor: str

    @classmethod
    def desde_texto(cls, texto: str) -> "Isbn":
        limpio = texto.replace("-", "").replace(" ", "").strip().upper()

        if len(limpio) == 10:
            if not _isbn10_valido(limpio):
                raise IsbnInvalido(f"El ISBN-10 {texto} no es válido")
            base = "978" + limpio[:9]
            return cls(base + digito_verificador_isbn13(base))

        if len(limpio) == 13 and limpio.isdigit():
            if digito_verificador_isbn13(limpio[:12]) != limpio[12]:
                raise IsbnInvalido(f"El dígito verificador del ISBN {texto} no es correcto")
            return cls(limpio)

        raise IsbnInvalido(f"'{texto}' no es un ISBN: debe tener 10 o 13 dígitos")

    def __str__(self) -> str:
        return self.valor
