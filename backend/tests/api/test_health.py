from fastapi.testclient import TestClient

from biblioteca.main import app

client = TestClient(app)


def test_health_responde_ok() -> None:
    respuesta = client.get("/api/v1/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base_de_datos": "ok"}
