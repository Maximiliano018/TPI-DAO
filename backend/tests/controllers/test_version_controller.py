from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_version_informa_estado_ok():
    respuesta = client.get("/api/version")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"servicio": "backend", "estado": "ok", "version": "0.1.0"}
