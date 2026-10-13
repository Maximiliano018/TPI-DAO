"""Sesión y roles sobre la base de demostración (usuarios con la contraseña documentada)."""

import pytest
from fastapi.testclient import TestClient

from biblioteca.infrastructure.db.seed_circulacion import CONTRASENA_DEMO
from tests.api.conftest import login

# Una consulta de cada router: ninguna responde sin sesión.
CONSULTAS = ["/sedes", "/socios", "/libros", "/prestamos", "/remitos", "/tablero"]


@pytest.mark.parametrize("ruta", CONSULTAS)
def test_las_consultas_exigen_sesion(cliente_escritura: TestClient, ruta: str) -> None:
    respuesta = cliente_escritura.get(f"/api/v1{ruta}", headers={"Authorization": ""})
    assert respuesta.status_code == 401


@pytest.mark.parametrize(
    ("username", "rol", "con_sede"),
    [
        ("admin", "ADMIN", False),
        ("bib.central", "BIBLIOTECARIO", True),
        ("log.central", "LOGISTICA", True),
    ],
)
def test_hay_un_usuario_de_demo_por_rol(
    cliente_escritura: TestClient, username: str, rol: str, con_sede: bool
) -> None:
    headers = login(cliente_escritura, username, CONTRASENA_DEMO)
    yo = cliente_escritura.get("/api/v1/auth/yo", headers=headers).json()
    assert yo["rol"] == rol
    assert (yo["sede_id"] is not None) == con_sede


def test_logistica_no_modifica_el_catalogo(cliente_escritura: TestClient) -> None:
    headers = login(cliente_escritura, "log.central", CONTRASENA_DEMO)
    respuesta = cliente_escritura.post(
        "/api/v1/libros",
        json={"isbn": "9780306406157", "titulo": "Libro", "autores": ["Autor"]},
        headers=headers,
    )
    assert respuesta.status_code == 403


def test_el_bibliotecario_consulta_pero_no_administra_sedes(
    cliente_escritura: TestClient,
) -> None:
    headers = login(cliente_escritura, "bib.norte", CONTRASENA_DEMO)
    assert cliente_escritura.get("/api/v1/sedes", headers=headers).status_code == 200
    assert cliente_escritura.post("/api/v1/sedes/1/baja", headers=headers).status_code == 403
