from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from biblioteca.api.deps import get_db
from biblioteca.main import app


def test_health_responde_ok(engine: Engine) -> None:
    # Se usa la base temporal del test: los tests nunca tocan la base local de desarrollo.
    def db_de_prueba() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = db_de_prueba
    try:
        respuesta = TestClient(app).get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base_de_datos": "ok"}
