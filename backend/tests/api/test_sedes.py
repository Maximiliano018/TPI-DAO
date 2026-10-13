"""ABM de sedes: permisos, validaciones, horarios y baja. Base vacía y reloj fijo."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from tests import datos

URL = "/api/v1/sedes"

NUEVA_SEDE = {
    "codigo": "nor",
    "nombre": "Sede Norte",
    "direccion": "Av. Rafael Núñez 4500",
    "localidad": "Córdoba",
    "telefono": "351 555-0000",
}


def _crear(cliente: TestClient, headers: dict[str, str], **cambios: Any) -> dict[str, Any]:
    respuesta = cliente.post(URL, json=NUEVA_SEDE | cambios, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo: dict[str, Any] = respuesta.json()
    return cuerpo


class TestPermisos:
    def test_el_admin_crea_sedes(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        sede = _crear(cliente_limpio, admin)
        assert sede["codigo"] == "NOR"
        assert sede["activa"] is True
        assert sede["cantidad_ejemplares"] == 0
        assert sede["horarios"] == []

    def test_el_bibliotecario_no_crea_sedes(
        self, cliente_limpio: TestClient, bibliotecario: dict[str, str]
    ) -> None:
        respuesta = cliente_limpio.post(URL, json=NUEVA_SEDE, headers=bibliotecario)
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"

    def test_sin_sesion_no_se_modifican_sedes(self, cliente_limpio: TestClient) -> None:
        respuesta = cliente_limpio.post(URL, json=NUEVA_SEDE)
        assert respuesta.status_code == 401
        assert respuesta.json()["codigo"] == "NO_AUTENTICADO"

    def test_consultar_sedes_requiere_sesion(
        self, cliente_limpio: TestClient, bibliotecario: dict[str, str], sede_id: int
    ) -> None:
        assert cliente_limpio.get(URL).status_code == 401
        respuesta = cliente_limpio.get(URL, headers=bibliotecario)
        assert respuesta.status_code == 200
        assert [s["id"] for s in respuesta.json()] == [sede_id]


class TestAltaYModificacion:
    def test_codigo_duplicado(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        _crear(cliente_limpio, admin)
        respuesta = cliente_limpio.post(URL, json=NUEVA_SEDE | {"nombre": "Otra"}, headers=admin)
        assert respuesta.status_code == 409
        assert respuesta.json()["codigo"] == "DUPLICADO"

    def test_nombre_duplicado(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        _crear(cliente_limpio, admin)
        respuesta = cliente_limpio.post(
            URL, json=NUEVA_SEDE | {"codigo": "OTR", "nombre": "sede norte"}, headers=admin
        )
        assert respuesta.status_code == 409

    def test_error_de_formato_con_cuerpo_uniforme(
        self, cliente_limpio: TestClient, admin: dict[str, str]
    ) -> None:
        respuesta = cliente_limpio.post(URL, json={"codigo": "NOR"}, headers=admin)
        assert respuesta.status_code == 422
        cuerpo = respuesta.json()
        assert cuerpo["codigo"] == "DATOS_INVALIDOS"
        assert {e["campo"][-1] for e in cuerpo["detalle"]} >= {"nombre", "direccion", "localidad"}

    def test_regla_de_dominio_responde_422(
        self, cliente_limpio: TestClient, admin: dict[str, str]
    ) -> None:
        respuesta = cliente_limpio.post(URL, json=NUEVA_SEDE | {"codigo": "N0R"}, headers=admin)
        assert respuesta.status_code == 422
        assert respuesta.json()["codigo"] == "DATO_INVALIDO"

    def test_actualizar_datos(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        sede = _crear(cliente_limpio, admin)
        datos_nuevos = {k: v for k, v in NUEVA_SEDE.items() if k != "codigo"}
        respuesta = cliente_limpio.put(
            f"{URL}/{sede['id']}",
            json=datos_nuevos | {"nombre": "Sede Norte II", "telefono": ""},
            headers=admin,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["nombre"] == "Sede Norte II"
        assert respuesta.json()["telefono"] is None

    def test_sede_inexistente(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        respuesta = cliente_limpio.get(f"{URL}/999", headers=admin)
        assert respuesta.status_code == 404
        assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


class TestHorarios:
    def test_reemplaza_los_horarios(
        self, cliente_limpio: TestClient, admin: dict[str, str]
    ) -> None:
        sede = _crear(cliente_limpio, admin)
        franjas = [
            {"dia_semana": 1, "hora_apertura": "16:00", "hora_cierre": "20:00"},
            {"dia_semana": 1, "hora_apertura": "08:00", "hora_cierre": "12:00"},
        ]
        respuesta = cliente_limpio.put(f"{URL}/{sede['id']}/horarios", json=franjas, headers=admin)
        assert respuesta.status_code == 200
        assert [h["hora_apertura"] for h in respuesta.json()["horarios"]] == [
            "08:00:00",
            "16:00:00",
        ]

    def test_rechaza_franjas_superpuestas(
        self, cliente_limpio: TestClient, admin: dict[str, str]
    ) -> None:
        sede = _crear(cliente_limpio, admin)
        franjas = [
            {"dia_semana": 2, "hora_apertura": "08:00", "hora_cierre": "13:00"},
            {"dia_semana": 2, "hora_apertura": "12:00", "hora_cierre": "18:00"},
        ]
        respuesta = cliente_limpio.put(f"{URL}/{sede['id']}/horarios", json=franjas, headers=admin)
        assert respuesta.status_code == 422
        assert "martes" in respuesta.json()["mensaje"]


class TestBaja:
    def test_baja_y_reactivacion(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        sede = _crear(cliente_limpio, admin)

        baja = cliente_limpio.post(f"{URL}/{sede['id']}/baja", headers=admin)
        assert baja.status_code == 200
        assert baja.json()["activa"] is False
        assert baja.json()["fecha_baja"].startswith("2026-10-12T15:00")

        reactivada = cliente_limpio.post(f"{URL}/{sede['id']}/reactivar", headers=admin)
        assert reactivada.json()["activa"] is True
        assert reactivada.json()["fecha_baja"] is None

    def test_no_se_da_de_baja_con_prestamos_en_curso(
        self, cliente_limpio: TestClient, admin: dict[str, str], engine: Engine
    ) -> None:
        sede = _crear(cliente_limpio, admin)
        with engine.begin() as conn:
            libro_id = datos.libro(conn)
            datos.prestamo(
                conn,
                socio_id=datos.socio(conn),
                ejemplar_id=datos.ejemplar(conn, libro_id, sede["id"]),
                sede_origen_id=sede["id"],
                sede_destino_id=sede["id"],
                registrado_por=datos.usuario(conn, sede["id"]),
            )

        respuesta = cliente_limpio.post(f"{URL}/{sede['id']}/baja", headers=admin)
        assert respuesta.status_code == 409
        assert respuesta.json()["codigo"] == "SEDE_CON_ACTIVIDAD_ABIERTA"

    def test_dar_de_baja_dos_veces(self, cliente_limpio: TestClient, admin: dict[str, str]) -> None:
        sede = _crear(cliente_limpio, admin)
        cliente_limpio.post(f"{URL}/{sede['id']}/baja", headers=admin)
        respuesta = cliente_limpio.post(f"{URL}/{sede['id']}/baja", headers=admin)
        assert respuesta.status_code == 409
        assert respuesta.json()["codigo"] == "TRANSICION_INVALIDA"
