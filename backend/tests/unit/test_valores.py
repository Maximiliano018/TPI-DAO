import pytest

from biblioteca.domain.errors import DatoInvalido
from biblioteca.domain.valores import Dni, Isbn, texto_opcional, texto_requerido


class TestIsbn:
    def test_acepta_isbn13_con_guiones(self) -> None:
        assert Isbn.desde_texto("978-0-306-40615-7").valor == "9780306406157"

    def test_convierte_isbn10_a_isbn13(self) -> None:
        assert Isbn.desde_texto("0-306-40615-2").valor == "9780306406157"

    def test_acepta_isbn10_con_x_como_verificador(self) -> None:
        assert Isbn.desde_texto("0-8044-2957-X").valor == "9780804429573"

    @pytest.mark.parametrize("texto", ["9780306406158", "0306406153", "123", "97803064061AB"])
    def test_rechaza_isbn_invalidos(self, texto: str) -> None:
        with pytest.raises(DatoInvalido):
            Isbn.desde_texto(texto)


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
