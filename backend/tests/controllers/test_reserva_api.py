"""Reservas y la cola FIFO de punta a punta contra PostgreSQL."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.controllers.test_prestamo_api import HOY, _prestar, mundo  # noqa: F401
from tests.controllers.test_sede_api import _error

API = "/api/v1"


def _reservar(cliente, headers, m, socio=None, libro=0, sede="b"):
    cuerpo = {"libro_id": m["libros"][libro]["id"], "sede_retiro_id": m[sede]["id"]}
    if socio is not None:
        cuerpo["socio_id"] = socio["id"]
    return cliente.post(f"{API}/reservas", json=cuerpo, headers=headers)


@pytest.fixture
def ocupado(cliente, mundo):  # noqa: F811
    """El único ejemplar del libro 0 en la sede B queda apartado por un préstamo de Juan."""
    return _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][0]).json()


def _socio(cliente, m, documento, nombre):
    return cliente.post(
        f"{API}/socios",
        json={
            "tipo_documento": "DNI",
            "nro_documento": documento,
            "nombre": nombre,
            "apellido": "Lector",
            "email": f"{documento}@example.com",
        },
        headers=m["h_b"],
    ).json()


# --- reservar --------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-01")
def test_con_ejemplares_disponibles_en_la_sede_corresponde_un_prestamo(cliente, mundo):  # noqa: F811
    _error(_reservar(cliente, mundo["h_lucia"], mundo), 409, "HAY_EJEMPLARES_DISPONIBLES")


@pytest.mark.ca("CA-RES-13")
def test_el_socio_reserva_para_si_y_ve_su_posicion(cliente, mundo, ocupado):  # noqa: F811
    r = _reservar(cliente, mundo["h_lucia"], mundo)

    assert r.status_code == 201, r.json()
    reserva = r.json()
    assert (reserva["estado"], reserva["socio_id"], reserva["posicion_en_cola"]) == (
        "PENDIENTE",
        mundo["lucia"]["id"],
        1,
    )
    assert reserva["numero"].startswith(f"RS-{HOY.year}-")
    otro = _socio(cliente, mundo, "50111222", "Otro")
    _reservar(cliente, mundo["h_b"], mundo, socio=otro)
    propias = cliente.get(f"{API}/reservas", headers=mundo["h_lucia"]).json()["items"]
    assert [x["id"] for x in propias] == [reserva["id"]]
    _error(
        cliente.get(f"{API}/reservas/{reserva['id'] + 1}", headers=mundo["h_lucia"]),
        404,
        "RESERVA_NO_ENCONTRADA",
    )


@pytest.mark.ca("CA-RES-02", "CA-RES-03", "CA-RES-04", "CA-RES-05")
def test_reglas_al_reservar(cliente, mundo, ocupado):  # noqa: F811
    _reservar(cliente, mundo["h_lucia"], mundo)
    _error(_reservar(cliente, mundo["h_lucia"], mundo), 409, "RESERVA_DUPLICADA")
    for i in (1, 2):  # completa tres reservas activas con libros sin disponibles en C
        assert _reservar(cliente, mundo["h_lucia"], mundo, libro=i, sede="c").status_code == 201
    _error(_reservar(cliente, mundo["h_lucia"], mundo, libro=3, sede="c"), 409, "LIMITE_RESERVAS")

    cliente.post(
        f"{API}/socios/{mundo['juan']['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )
    _error(
        _reservar(cliente, mundo["h_b"], mundo, socio=mundo["juan"], libro=4, sede="c"),
        409,
        "SOCIO_INHABILITADO",
    )
    c = cliente.get(f"{API}/sedes/{mundo['c']['id']}", headers=mundo["h_admin"]).json()
    otro = _socio(cliente, mundo, "50111222", "Otro")
    reservas_c = cliente.get(
        f"{API}/reservas", params={"socio_id": mundo["lucia"]["id"]}, headers=mundo["h_admin"]
    ).json()["items"]
    for r in reservas_c:
        cliente.post(f"{API}/reservas/{r['id']}/cancelar", headers=mundo["h_lucia"])
    baja = cliente.post(
        f"{API}/sedes/{c['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": c["version"]},
        headers=mundo["h_admin"],
    )
    assert baja.status_code == 200, baja.json()
    _error(
        _reservar(cliente, mundo["h_b"], mundo, socio=otro, libro=4, sede="c"), 409, "SEDE_EN_BAJA"
    )


# --- cola ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-RES-06", "CA-RES-07", "CA-RES-08", "CA-RES-12")
def test_el_ejemplar_liberado_va_al_primero_elegible_de_la_cola(cliente, mundo, ocupado):  # noqa: F811
    inhabilitada = _socio(cliente, mundo, "50111111", "Primera")
    segunda = _socio(cliente, mundo, "50222222", "Segunda")
    tercera = _socio(cliente, mundo, "50333333", "Tercera")
    ids = [
        _reservar(cliente, mundo["h_b"], mundo, socio=s).json()["id"]
        for s in (inhabilitada, segunda, tercera)
    ]
    cliente.post(
        f"{API}/socios/{inhabilitada['id']}/inhabilitar",
        json={"motivo": "Daño reiterado"},
        headers=mundo["h_admin"],
    )

    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])

    estados = [cliente.get(f"{API}/reservas/{i}", headers=mundo["h_b"]).json() for i in ids]
    assert [e["estado"] for e in estados] == ["PENDIENTE", "DISPONIBLE_PARA_RETIRO", "PENDIENTE"]
    assert estados[1]["vencimiento_retiro"] == str(HOY + timedelta(days=3))
    assert estados[1]["codigo_ejemplar"] == "B-0"
    assert [estados[0]["posicion_en_cola"], estados[2]["posicion_en_cola"]] == [1, 2]
    ejemplar = cliente.get(
        f"{API}/ejemplares/{mundo['ej_b'][0]['id']}", headers=mundo["h_b"]
    ).json()
    assert ejemplar["estado"] == "RESERVADO"

    prestamo = cliente.post(f"{API}/reservas/{ids[1]}/retirar", headers=mundo["h_b"]).json()
    assert (prestamo["estado"], prestamo["socio_id"], prestamo["tipo"]) == (
        "ACTIVO",
        segunda["id"],
        "LOCAL",
    )
    assert prestamo["fecha_vencimiento"] == str(HOY + timedelta(days=14))
    cumplida = cliente.get(f"{API}/reservas/{ids[1]}", headers=mundo["h_b"]).json()
    assert (cumplida["estado"], cumplida["prestamo_id"]) == ("CUMPLIDA", prestamo["id"])
    _error(
        cliente.post(f"{API}/reservas/{ids[1]}/cancelar", headers=mundo["h_b"]),
        409,
        "TRANSICION_INVALIDA",
    )


@pytest.mark.ca("CA-RES-10")
def test_una_reserva_no_retirada_vence_y_pasa_a_la_siguiente(cliente, mundo, ocupado, sesion):  # noqa: F811
    primera = _reservar(cliente, mundo["h_lucia"], mundo).json()
    otro = _socio(cliente, mundo, "50111222", "Otro")
    segunda = _reservar(cliente, mundo["h_b"], mundo, socio=otro).json()
    cliente.post(f"{API}/prestamos/{ocupado['id']}/cancelar", json={}, headers=mundo["h_b"])
    sesion.execute(
        text("UPDATE reserva SET vencimiento_retiro = :f WHERE id = :id"),
        {"f": HOY - timedelta(days=1), "id": primera["id"]},
    )
    sesion.commit()

    r = cliente.post(f"{API}/admin/tareas/vencer-reservas", headers=mundo["h_admin"])

    assert r.json() == {"tarea": "vencer-reservas", "cambios": 1}
    estados = [
        cliente.get(f"{API}/reservas/{x['id']}", headers=mundo["h_b"]).json()["estado"]
        for x in (primera, segunda)
    ]
    assert estados == ["VENCIDA", "DISPONIBLE_PARA_RETIRO"]


@pytest.mark.ca("CA-RES-09")
def test_un_ejemplar_liberado_en_otra_sede_inicia_un_prestamo_entre_sedes(cliente, mundo):  # noqa: F811
    prestamo_a = _prestar(cliente, mundo["h_a"], mundo["juan"], mundo["ej_a"][4]).json()
    reserva = _reservar(cliente, mundo["h_lucia"], mundo, libro=4).json()

    cliente.post(f"{API}/prestamos/{prestamo_a['id']}/cancelar", json={}, headers=mundo["h_a"])

    cumplida = cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_lucia"]).json()
    assert cumplida["estado"] == "CUMPLIDA"
    nuevo = cliente.get(f"{API}/prestamos/{cumplida['prestamo_id']}", headers=mundo["h_b"]).json()
    assert (nuevo["tipo"], nuevo["estado"], nuevo["sede_origen_id"], nuevo["sede_destino_id"]) == (
        "INTERBIBLIOTECARIO",
        "SOLICITADO",
        mundo["a"]["id"],
        mundo["b"]["id"],
    )
    assert nuevo["socio_id"] == mundo["lucia"]["id"]


@pytest.mark.ca("CA-PRE-17", "CA-SED-19")
def test_las_reservas_impiden_renovar_y_dar_de_baja_la_sede(cliente, mundo, ocupado):  # noqa: F811
    cliente.post(f"{API}/prestamos/{ocupado['id']}/entregar", headers=mundo["h_b"])
    _reservar(cliente, mundo["h_lucia"], mundo, sede="c")

    _error(
        cliente.post(f"{API}/prestamos/{ocupado['id']}/renovar", headers=mundo["h_b"]),
        409,
        "RENOVACION_NO_PERMITIDA",
    )
    c = cliente.get(f"{API}/sedes/{mundo['c']['id']}", headers=mundo["h_admin"]).json()
    baja = cliente.post(
        f"{API}/sedes/{c['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": c["version"]},
        headers=mundo["h_admin"],
    )
    tipos = [d["tipo"] for d in _error(baja, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")["detalles"]]
    assert tipos == ["RESERVAS_PENDIENTES"]


def test_la_baja_del_socio_cancela_sus_reservas(cliente, mundo, ocupado):  # noqa: F811
    reserva = _reservar(cliente, mundo["h_lucia"], mundo).json()
    ficha = cliente.get(f"{API}/socios/{mundo['lucia']['id']}", headers=mundo["h_b"]).json()
    assert ficha["situacion"]["reservas_activas"] == 1

    cliente.post(
        f"{API}/socios/{mundo['lucia']['id']}/baja",
        json={"motivo": "Se mudó"},
        headers=mundo["h_admin"],
    )

    assert (
        cliente.get(f"{API}/reservas/{reserva['id']}", headers=mundo["h_b"]).json()["estado"]
        == "CANCELADA"
    )
