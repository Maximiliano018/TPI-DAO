import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_informa_estado_ok_y_la_version_de_pyproject():
    with PYPROJECT.open("rb") as archivo:
        version_esperada = tomllib.load(archivo)["project"]["version"]

    respuesta = client.get("/api/version")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "servicio": "backend",
        "estado": "ok",
        "version": version_esperada,
    }
