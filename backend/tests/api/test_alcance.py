"""Permisos por rol y datos por sede, sobre la base de demostración (ARCHITECTURE.md §6.1).

El ADMIN ve toda la red; BIBLIOTECARIO y LOGISTICA ven solo lo que involucra a su sede.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from biblioteca.infrastructure.db.seed_circulacion import CONTRASENA_DEMO
from tests.api.conftest import login

API = "/api/v1"
Pedir = Callable[[str, str], Any]


@pytest.fixture
def pedir(cliente_escritura: TestClient) -> Pedir:
    """GET con la sesión del usuario indicado; devuelve el JSON (falla si no es 200)."""
    sesiones: dict[str, dict[str, str]] = {}

    def get(usuario: str, ruta: str) -> Any:
        if usuario not in sesiones:
            sesiones[usuario] = login(cliente_escritura, usuario, CONTRASENA_DEMO)
        respuesta = cliente_escritura.get(f"{API}{ruta}", headers=sesiones[usuario])
        assert respuesta.status_code == 200, (usuario, ruta, respuesta.text)
        return respuesta.json()

    return get


@pytest.fixture
def sedes(pedir: Pedir) -> dict[str, int]:
    return {s["codigo"]: s["id"] for s in pedir("admin", "/sedes")}


# ------------------------------------------------------------------------- Roles


@pytest.mark.parametrize(
    "ruta",
    [
        "/prestamos",
        "/reservas",
        "/devoluciones",
        "/socios",
        "/reportes/libros-mas-solicitados",
        "/reportes/vencidos-y-multas",
    ],
)
def test_logistica_no_accede_a_circulacion_ni_socios(
    cliente_escritura: TestClient, ruta: str
) -> None:
    headers = login(cliente_escritura, "log.central", CONTRASENA_DEMO)
    respuesta = cliente_escritura.get(f"{API}{ruta}", headers=headers)
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ACCESO_DENEGADO"


@pytest.mark.parametrize(
    "ruta",
    ["/tablero", "/remitos", "/sedes", "/libros", "/disponibilidad", "/reportes/envios-exitosos"],
)
def test_logistica_accede_a_lo_logistico_y_al_catalogo(pedir: Pedir, ruta: str) -> None:
    pedir("log.central", ruta)


# ----------------------------------------------------------------- Datos por sede


def _involucra(fila: dict[str, Any], sede_id: int) -> bool:
    return sede_id in (fila["sede_origen_id"], fila["sede_destino_id"])


def test_el_bibliotecario_ve_solo_los_prestamos_de_su_sede(
    pedir: Pedir, sedes: dict[str, int]
) -> None:
    todos = pedir("admin", "/prestamos")
    de_central = pedir("bib.central", "/prestamos")

    assert de_central, "la demo debería tener préstamos de la Sede Central"
    assert all(_involucra(p, sedes["CEN"]) for p in de_central)
    assert {p["id"] for p in de_central} == {p["id"] for p in todos if _involucra(p, sedes["CEN"])}
    assert len(de_central) < len(todos)


def test_cada_bibliotecario_ve_las_reservas_de_su_sede(pedir: Pedir, sedes: dict[str, int]) -> None:
    for usuario, codigo in [("bib.central", "CEN"), ("bib.norte", "NOR"), ("bib.sur", "SUR")]:
        assert all(r["sede_id"] == sedes[codigo] for r in pedir(usuario, "/reservas"))


def test_logistica_ve_solo_los_envios_de_su_sede(pedir: Pedir, sedes: dict[str, int]) -> None:
    remitos = pedir("log.central", "/remitos")
    assert remitos
    assert all(_involucra(r, sedes["CEN"]) for r in remitos)


def test_la_trazabilidad_de_un_remito_ajeno_no_existe_para_otra_sede(
    cliente_escritura: TestClient, pedir: Pedir, sedes: dict[str, int]
) -> None:
    ajeno = next(r for r in pedir("admin", "/remitos") if not _involucra(r, sedes["SUR"]))
    headers = login(cliente_escritura, "bib.sur", CONTRASENA_DEMO)

    respuesta = cliente_escritura.get(f"{API}/remitos/{ajeno['id']}/movimientos", headers=headers)

    assert respuesta.status_code == 404
    assert pedir("admin", f"/remitos/{ajeno['id']}/movimientos")


def test_el_tablero_se_calcula_por_sede(pedir: Pedir) -> None:
    red = pedir("admin", "/tablero")
    por_sede = [pedir(u, "/tablero") for u in ("bib.central", "bib.norte", "bib.sur")]

    for clave in ("reservas_pendientes", "reservas_asignadas"):
        # Cada reserva tiene una sola sede de retiro: las sedes suman el total de la red.
        assert sum(t[clave] for t in por_sede) == red[clave]
    for t in por_sede:
        assert t["prestamos_activos"] <= red["prestamos_activos"]
        assert t["remitos_en_transito"] <= red["remitos_en_transito"]


def test_los_reportes_se_calculan_por_sede(pedir: Pedir, sedes: dict[str, int]) -> None:
    rutas = pedir("bib.norte", "/reportes/movimiento-entre-sedes")["rutas"]
    assert rutas
    assert all(_involucra(r, sedes["NOR"]) for r in rutas)

    vencidos_red = pedir("admin", "/reportes/vencidos-y-multas")["vencidos"]
    vencidos_sur = pedir("bib.sur", "/reportes/vencidos-y-multas")["vencidos"]
    assert len(vencidos_sur) <= len(vencidos_red)


def test_el_catalogo_y_los_socios_son_de_toda_la_red(pedir: Pedir) -> None:
    assert len(pedir("bib.sur", "/libros")) == len(pedir("admin", "/libros"))
    assert len(pedir("bib.sur", "/socios")) == len(pedir("admin", "/socios"))
