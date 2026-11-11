"""El formato de error es único para errores de negocio, validación y rutas inexistentes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator

from app.controllers.manejo_errores import registrar_manejadores
from app.exceptions import SedeEnBaja, SedeNoEncontrada


class _Cuerpo(BaseModel):
    numero: int

    @field_validator("numero")
    @classmethod
    def _positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Debe ser positivo")
        return v


def _app() -> TestClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/baja")
    def baja():
        raise SedeEnBaja("La sede está en baja")

    @app.get("/no-esta")
    def no_esta():
        raise SedeNoEncontrada("No existe")

    @app.post("/validar")
    def validar(cuerpo: _Cuerpo):
        return cuerpo

    return TestClient(app, raise_server_exceptions=False)


def test_un_error_de_negocio_responde_409_con_codigo_estable():
    r = _app().get("/baja")

    assert r.status_code == 409
    assert r.json() == {
        "error": {"codigo": "SEDE_EN_BAJA", "mensaje": "La sede está en baja", "detalles": []}
    }


def test_una_entidad_inexistente_responde_404():
    assert _app().get("/no-esta").status_code == 404


def test_un_dato_invalido_responde_422_con_el_campo_y_el_problema():
    r = _app().post("/validar", json={"numero": -1})

    assert r.status_code == 422
    error = r.json()["error"]
    assert error["codigo"] == "VALIDACION"
    assert error["detalles"] == [{"campo": "numero", "problema": "Debe ser positivo"}]


def test_una_ruta_inexistente_usa_el_mismo_formato():
    r = _app().get("/nada")

    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "NOT_FOUND"
