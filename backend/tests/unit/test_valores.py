import pytest

from biblioteca.domain.errors import DatoInvalido
from biblioteca.domain.valores import Dni, texto_opcional, texto_requerido


class TestDni:
    def test_quita_puntos_y_espacios(self) -> None:
        assert Dni.desde_texto("30.111.222").valor == "30111222"

    @pytest.mark.parametrize("texto", ["123456", "123456789", "30A11222"])
    def test_rechaza_dni_invalidos(self, texto: str) -> None:
        with pytest.raises(DatoInvalido):
            Dni.desde_texto(texto)


def test_texto_requerido_normaliza_espacios() -> None:
    assert texto_requerido("  Sede   Central ", "nombre", 100) == "Sede Central"


def test_texto_requerido_rechaza_vacio_y_largo() -> None:
    with pytest.raises(DatoInvalido, match="obligatorio"):
        texto_requerido("   ", "nombre", 100)
    with pytest.raises(DatoInvalido, match="hasta 3"):
        texto_requerido("abcd", "nombre", 3)


def test_texto_opcional_vacio_es_none() -> None:
    assert texto_opcional("  ", "teléfono", 30) is None
