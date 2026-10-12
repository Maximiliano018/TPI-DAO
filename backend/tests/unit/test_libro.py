import pytest

from biblioteca.domain.entities.isbn import Isbn
from biblioteca.domain.entities.libro import Libro
from biblioteca.domain.errors import DatoInvalido, IsbnInvalido

ISBN_VALIDO = "9780306406157"


def test_isbn13_valido_con_guiones() -> None:
    assert Isbn.desde_texto("978-0-306-40615-7").valor == ISBN_VALIDO


def test_isbn10_se_convierte_a_isbn13() -> None:
    assert Isbn.desde_texto("0-306-40615-2").valor == ISBN_VALIDO


def test_isbn10_con_x_como_verificador() -> None:
    assert Isbn.desde_texto("080442957X").valor == "9780804429573"


@pytest.mark.parametrize("texto", ["9780306406158", "0306406153", "12345", "97803064061AB"])
def test_isbn_invalido(texto: str) -> None:
    with pytest.raises(IsbnInvalido):
        Isbn.desde_texto(texto)


def _libro(**cambios: object) -> Libro:
    datos: dict[str, object] = {
        "isbn": Isbn(ISBN_VALIDO),
        "titulo": "Ficciones",
        "autores": ["Jorge Luis Borges"],
    }
    datos.update(cambios)
    return Libro(**datos)  # type: ignore[arg-type]


def test_libro_limpia_espacios_y_autores_repetidos() -> None:
    libro = _libro(titulo="  El   Aleph ", autores=["Borges", " borges ", "", "Bioy Casares"])
    assert libro.titulo == "El Aleph"
    assert libro.autores == ["Borges", "Bioy Casares"]


def test_libro_sin_titulo() -> None:
    with pytest.raises(DatoInvalido, match="título"):
        _libro(titulo="   ")


def test_libro_sin_autores() -> None:
    with pytest.raises(DatoInvalido, match="autor"):
        _libro(autores=["", "  "])


def test_libro_con_anio_no_positivo() -> None:
    with pytest.raises(DatoInvalido, match="año"):
        _libro(anio_publicacion=0)
