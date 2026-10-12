"""Endpoints de consulta contra la base de demostración.

Los valores esperados salen de la historia de `seed_circulacion.py`.
"""

from typing import Any

from fastapi.testclient import TestClient

API = "/api/v1"
MULTA_POR_DIA = 50_000  # centavos (parámetro inicial)


def _get(cliente: TestClient, ruta: str, **params: Any) -> Any:
    respuesta = cliente.get(f"{API}{ruta}", params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _por(items: list[dict[str, Any]], campo: str) -> dict[Any, dict[str, Any]]:
    return {item[campo]: item for item in items}


def test_sedes_con_horarios_y_ejemplares_sin_bajas(cliente: TestClient) -> None:
    sedes = _por(_get(cliente, "/sedes"), "codigo")

    assert set(sedes) == {"CEN", "NOR", "SUR"}
    assert sedes["CEN"]["cantidad_ejemplares"] == 6
    assert sedes["NOR"]["cantidad_ejemplares"] == 4  # uno extraviado
    assert sedes["SUR"]["cantidad_ejemplares"] == 3  # uno destruido
    assert all(s["horarios"] for s in sedes.values())


def test_socios_con_prestamos_abiertos_y_deuda(cliente: TestClient) -> None:
    socios = _por(_get(cliente, "/socios"), "dni")

    assert len(socios) == 5
    assert socios["30111222"]["prestamos_abiertos"] == 2  # Ana
    assert socios["31222333"]["multas_pendientes"] == 6 * MULTA_POR_DIA  # Bruno
    assert socios["34555666"]["habilitado"] is False  # Elena


def test_buscar_socio_por_dni(cliente: TestClient) -> None:
    socios = _get(cliente, "/socios", buscar="30111222")
    assert [s["apellido"] for s in socios] == ["Pérez"]


def test_libros_con_autores_y_disponibles(cliente: TestClient) -> None:
    libros = _por(_get(cliente, "/libros"), "titulo")

    assert len(libros) == 8
    assert libros["Ficciones"]["autores"] == ["Jorge Luis Borges"]
    assert libros["Ficciones"]["ejemplares"] == 2  # sin el dado de baja
    assert libros["Ficciones"]["disponibles"] == 0
    assert libros["Martín Fierro"]["disponibles"] == 2


def test_buscar_libro_por_autor(cliente: TestClient) -> None:
    libros = _get(cliente, "/libros", buscar="borges")
    assert [li["titulo"] for li in libros] == ["Ficciones"]


def test_ejemplares_filtrados_por_estado(cliente: TestClient) -> None:
    bajas = _get(cliente, "/ejemplares", estado="BAJA")
    assert {e["motivo_baja"] for e in bajas} == {"EXTRAVIO", "DESTRUCCION"}


def test_disponibilidad_por_sede(cliente: TestClient) -> None:
    libros = _por(_get(cliente, "/disponibilidad"), "titulo")

    assert libros["Martín Fierro"]["disponibles"] == 2
    diccionario = libros["Diccionario de la lengua española"]
    assert diccionario["disponibles"] == 0
    assert diccionario["sedes"][0]["consulta_en_sala"] == 1


def test_prestamos_abiertos_con_condiciones_derivadas(cliente: TestClient) -> None:
    prestamos = _get(cliente, "/prestamos", abiertos=True)

    assert len(prestamos) == 7
    vencidos = [p for p in prestamos if p["vencido"]]
    assert [(p["titulo"], p["dias_atraso"]) for p in vencidos] == [("Rayuela", 6)]
    listos = [p for p in prestamos if p["estado"] == "LISTO_PARA_RETIRO"]
    assert [p["tipo"] for p in listos] == ["INTERSEDES"]


def test_remitos_con_un_demorado(cliente: TestClient) -> None:
    remitos = _get(cliente, "/remitos")

    assert len(remitos) == 15
    demorados = [r for r in remitos if r["demorado"]]
    assert [(r["sede_origen"], r["sede_destino"]) for r in demorados] == [
        ("Sede Norte", "Sede Central")
    ]


def test_trazabilidad_de_un_remito(cliente: TestClient) -> None:
    recibidos = _get(cliente, "/remitos", estado="RECIBIDO")
    movimientos = _get(cliente, f"/remitos/{recibidos[0]['id']}/movimientos")

    assert [m["estado_nuevo"] for m in movimientos] == [
        "GENERADO",
        "EMPAQUETADO",
        "EN_TRANSITO",
        "RECIBIDO",
    ]
    assert movimientos[0]["estado_anterior"] is None
    assert all(m["usuario"] for m in movimientos)


def test_trazabilidad_de_remito_inexistente(cliente: TestClient) -> None:
    respuesta = cliente.get(f"{API}/remitos/9999/movimientos")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def test_cola_de_reservas(cliente: TestClient) -> None:
    pendientes = _get(cliente, "/reservas", estado="PENDIENTE")
    assert [(r["titulo"], r["posicion_cola"]) for r in pendientes] == [
        ("Rayuela", 1),
        ("Rayuela", 2),
    ]


def test_devoluciones_con_multa(cliente: TestClient) -> None:
    devoluciones = _get(cliente, "/devoluciones")

    assert len(devoluciones) == 5
    con_multa = {d["socio"]: d for d in devoluciones if d["multa_monto"]}
    assert con_multa["Gómez, Bruno"]["multa_estado"] == "PENDIENTE"
    assert con_multa["Pérez, Ana"]["multa_estado"] == "SALDADA"


def test_tablero(cliente: TestClient) -> None:
    tablero = _get(cliente, "/tablero")

    assert tablero["prestamos_activos"] == 3
    assert tablero["prestamos_vencidos"] == 1
    assert tablero["prestamos_en_envio"] == 3
    assert tablero["listos_para_retiro"] == 1
    assert tablero["remitos_en_transito"] == 2
    assert tablero["remitos_demorados"] == 1
    assert tablero["reservas_pendientes"] == 2
    assert tablero["reservas_asignadas"] == 1
    assert tablero["multas_pendientes_monto"] == 6 * MULTA_POR_DIA
    assert [v["dias_restantes"] for v in tablero["proximos_vencimientos"]] == [-6, 2]
    assert len(tablero["ultimos_movimientos"]) == 8


def test_r1_movimiento_entre_sedes(cliente: TestClient) -> None:
    reporte = _get(cliente, "/reportes/movimiento-entre-sedes")
    rutas = {(r["sede_origen"], r["sede_destino"]): r for r in reporte["rutas"]}

    assert reporte["envios_totales"] == 15
    norte_central = rutas[("Sede Norte", "Sede Central")]
    assert (norte_central["envios"], norte_central["recibidos"]) == (3, 2)
    assert norte_central["dias_promedio_transito"] == 1.5


def test_r1_filtra_por_periodo(cliente: TestClient) -> None:
    reporte = _get(
        cliente, "/reportes/movimiento-entre-sedes", desde="2000-01-01", hasta="2000-12-31"
    )
    assert reporte == {"envios_totales": 0, "dias_promedio_transito": None, "rutas": []}


def test_r2_envios_exitosos(cliente: TestClient) -> None:
    reporte = _get(cliente, "/reportes/envios-exitosos")

    assert (reporte["total"], reporte["exitosos"]) == (11, 7)
    assert reporte["tasa_exito"] == 63.6
    assert reporte["incidencias"] == {"danados": 2, "destruidos": 1, "extraviados": 1}


def test_r3_libros_mas_solicitados(cliente: TestClient) -> None:
    ranking = _get(cliente, "/reportes/libros-mas-solicitados")
    assert (ranking[0]["titulo"], ranking[0]["solicitudes"]) == ("Ficciones", 3)


def test_r4_vencidos_y_multas(cliente: TestClient) -> None:
    reporte = _get(cliente, "/reportes/vencidos-y-multas")

    assert [(v["socio"], v["dias_atraso"]) for v in reporte["vencidos"]] == [("Díaz, Carla", 6)]
    assert reporte["total_pendiente"] == 6 * MULTA_POR_DIA
    assert reporte["total_saldado"] == 4 * MULTA_POR_DIA
