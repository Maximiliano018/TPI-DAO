"""Alta y baja de libros (proceso obligatorio 3: administrar el catálogo)."""

from typing import Any

from fastapi.testclient import TestClient

API = "/api/v1"


def _nuevo(**cambios: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "isbn": "978-0-306-40615-7",
        "titulo": "El Aleph",
        "autores": ["Jorge Luis Borges"],
        "editorial": "Losada",
        "anio_publicacion": 1949,
    }
    datos.update(cambios)
    return datos


def test_alta_de_libro(cliente_escritura: TestClient) -> None:
    respuesta = cliente_escritura.post(f"{API}/libros", json=_nuevo())
    assert respuesta.status_code == 201

    libros = cliente_escritura.get(f"{API}/libros", params={"buscar": "borges"}).json()
    aleph = next(li for li in libros if li["titulo"] == "El Aleph")
    assert aleph["id"] == respuesta.json()["id"]
    assert aleph["isbn"] == "9780306406157"
    assert aleph["ejemplares"] == 0
    # Reutiliza el autor que ya existía (Ficciones): la búsqueda trae los dos libros.
    assert {li["titulo"] for li in libros} == {"Ficciones", "El Aleph"}


def test_alta_con_isbn10_lo_guarda_como_isbn13(cliente_escritura: TestClient) -> None:
    cliente_escritura.post(f"{API}/libros", json=_nuevo(isbn="0-306-40615-2"))
    libros = cliente_escritura.get(f"{API}/libros", params={"buscar": "9780306406157"}).json()
    assert [li["titulo"] for li in libros] == ["El Aleph"]


def test_alta_con_isbn_repetido(cliente_escritura: TestClient) -> None:
    cliente_escritura.post(f"{API}/libros", json=_nuevo())
    respuesta = cliente_escritura.post(f"{API}/libros", json=_nuevo(titulo="Otro título"))
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "DUPLICADO"


def test_alta_con_isbn_invalido(cliente_escritura: TestClient) -> None:
    respuesta = cliente_escritura.post(f"{API}/libros", json=_nuevo(isbn="9780306406158"))
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "ISBN_INVALIDO"


def test_alta_sin_autores(cliente_escritura: TestClient) -> None:
    respuesta = cliente_escritura.post(f"{API}/libros", json=_nuevo(autores=[]))
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"


def test_alta_con_categoria_inexistente(cliente_escritura: TestClient) -> None:
    respuesta = cliente_escritura.post(f"{API}/libros", json=_nuevo(categoria_id=999))
    assert respuesta.status_code == 404


def test_eliminar_libro_sin_historial(cliente_escritura: TestClient) -> None:
    libro_id = cliente_escritura.post(f"{API}/libros", json=_nuevo()).json()["id"]

    assert cliente_escritura.delete(f"{API}/libros/{libro_id}").status_code == 204
    assert cliente_escritura.delete(f"{API}/libros/{libro_id}").status_code == 404


def test_no_se_elimina_un_libro_con_ejemplares(cliente_escritura: TestClient) -> None:
    ficciones = cliente_escritura.get(f"{API}/libros", params={"buscar": "Ficciones"}).json()[0]

    respuesta = cliente_escritura.delete(f"{API}/libros/{ficciones['id']}")
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "LIBRO_CON_HISTORIAL"


def test_categorias(cliente_escritura: TestClient) -> None:
    categorias = cliente_escritura.get(f"{API}/categorias").json()
    assert "Historia" in [c["nombre"] for c in categorias]
