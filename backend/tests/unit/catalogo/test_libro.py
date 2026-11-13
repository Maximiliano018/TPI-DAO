"""Reglas del libro: ISBN, datos obligatorios y clave natural para detectar duplicados."""

import pytest

from app.exceptions import ErrorDeValidacion
from app.models.libro import CategoriaRef, DatosLibro, Isbn, TipoMaterial

CATEGORIA = CategoriaRef(1, "Literatura argentina")


def datos(**over) -> DatosLibro:
    valores = {
        "isbn": "978-950-07-0578-3",
        "titulo": "Rayuela",
        "autores": ["Julio Cortázar"],
        "editorial": "Sudamericana",
        "anio_edicion": 1963,
        "categoria": CATEGORIA,
        "tipo_material": TipoMaterial.LIBRO,
        "anio_actual": 2026,
    }
    valores.update(over)
    return DatosLibro.crear(**valores)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("978-0-13-235088-4", "9780132350884"),
        ("0132350882", "0132350882"),
        ("0-8044-2957-x", "080442957X"),
    ],
)
def test_el_isbn_valido_se_guarda_sin_guiones(texto, esperado):
    assert Isbn.crear(texto).valor == esperado


@pytest.mark.parametrize("texto", ["9780132350885", "013235088", "abc", "0132350883"])
def test_un_isbn_con_verificador_o_largo_invalido_se_rechaza(texto):
    with pytest.raises(ErrorDeValidacion) as error:
        Isbn.crear(texto)
    assert error.value.detalles[0]["campo"] == "isbn"


def test_los_datos_se_normalizan_y_sin_isbn_hay_clave_natural():
    con_isbn = datos(titulo="  Rayuela ", autores=[" Julio  Cortázar", ""])
    sin_isbn = datos(isbn=None, titulo="Rayuela", editorial="Sudamericana")

    assert con_isbn.titulo == "Rayuela" and con_isbn.autores == ("Julio Cortázar",)
    assert con_isbn.clave_natural is None
    assert sin_isbn.clave_natural == "rayuela|julio cortazar|sudamericana|1963"
    assert datos(isbn=None, titulo="RAYUELA", autores=["julio cortazar"]).clave_natural == (
        sin_isbn.clave_natural
    )


@pytest.mark.parametrize(
    ("over", "campo"),
    [
        ({"titulo": " "}, "titulo"),
        ({"autores": []}, "autores"),
        ({"autores": ["", " "]}, "autores"),
        ({"autores": ["Ana", "ana"]}, "autores"),
        ({"anio_edicion": 1400}, "anio_edicion"),
        ({"anio_edicion": 2028}, "anio_edicion"),
        ({"editorial": "x" * 101}, "editorial"),
    ],
)
def test_datos_faltantes_o_fuera_de_rango_se_rechazan(over, campo):
    with pytest.raises(ErrorDeValidacion) as error:
        datos(**over)
    assert error.value.detalles[0]["campo"] == campo
