"""Reserva: estados (State), vencimiento del retiro e historial."""

from datetime import UTC, date, datetime

import pytest

from app.exceptions import TransicionInvalida
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum as R
from app.models.states.reserva import estado_reserva
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
HOY = date(2026, 11, 10)
LUCIA = UsuarioRef(12, "Lucía Socio")
BETO = UsuarioRef(3, "Beto B")


def reserva(estado: R = R.PENDIENTE, **over) -> Reserva:
    valores = {
        "id": 9,
        "numero": "RS-2026-000009",
        "socio_id": 45,
        "libro_id": 12,
        "sede_retiro_id": 2,
        "fecha_reserva": AHORA,
        "estado": estado_reserva(estado),
    }
    valores.update(over)
    return Reserva(**valores)


def _historial(r: Reserva) -> list[tuple]:
    return [
        (m.estado_anterior, m.estado_nuevo, m.usuario, m.observacion)
        for m in r.movimientos_pendientes
    ]


@pytest.mark.ca("CA-RES-07")
def test_asignar_deja_la_reserva_disponible_por_la_vigencia():
    r = reserva()

    r.asignar(301, HOY, 3, AHORA, "B-0")

    assert r.estado_nombre == R.DISPONIBLE_PARA_RETIRO
    assert (r.ejemplar_id, r.vencimiento_retiro) == (301, date(2026, 11, 13))


@pytest.mark.ca("CA-RES-10")
def test_vence_recien_despues_del_ultimo_dia_de_retiro():
    r = reserva(R.DISPONIBLE_PARA_RETIRO, ejemplar_id=301, vencimiento_retiro=date(2026, 11, 13))

    assert r.vencer(date(2026, 11, 13), AHORA) is False
    assert r.vencer(date(2026, 11, 14), AHORA) is True
    assert r.estado_nombre == R.VENCIDA


@pytest.mark.ca("CA-RES-11")
@pytest.mark.parametrize("final", [R.CUMPLIDA, R.CANCELADA, R.VENCIDA])
def test_una_reserva_cerrada_no_se_cancela_ni_se_asigna(final):
    r = reserva(final)

    with pytest.raises(TransicionInvalida):
        r.cancelar(AHORA, LUCIA, None)
    with pytest.raises(TransicionInvalida):
        r.asignar(301, HOY, 3, AHORA, "B-0")
    assert r.movimientos_pendientes == []


def test_retirar_solo_si_esta_disponible_para_retiro():
    pendiente = reserva()
    disponible = reserva(R.DISPONIBLE_PARA_RETIRO, ejemplar_id=301, vencimiento_retiro=HOY)

    with pytest.raises(TransicionInvalida):
        pendiente.cumplir(118, BETO, AHORA, "P-2026-000118")
    disponible.cumplir(118, BETO, AHORA, "P-2026-000118")
    assert (disponible.estado_nombre, disponible.prestamo_id) == (R.CUMPLIDA, 118)


def test_un_ejemplar_de_otra_sede_cumple_la_reserva_con_un_prestamo():
    r = reserva()

    r.convertir_en_prestamo(301, 118, AHORA, "P-2026-000118")

    assert (r.estado_nombre, r.ejemplar_id, r.prestamo_id) == (R.CUMPLIDA, 301, 118)
    assert not r.esta_activa


@pytest.mark.ca("CA-RES-19")
def test_cada_cambio_de_estado_queda_en_el_historial_con_su_autor():
    r = Reserva.registrar(
        numero="RS-2026-000009",
        socio_id=45,
        libro_id=12,
        sede_retiro_id=2,
        actor=LUCIA,
        ahora=AHORA,
    )
    r.id = 9
    r.asignar(301, HOY, 3, AHORA, "B-0")
    r.cumplir(118, BETO, AHORA, "P-2026-000118")

    assert r.registrada_por == LUCIA
    assert _historial(r) == [
        (None, R.PENDIENTE, LUCIA, "Reserva registrada"),
        (
            R.PENDIENTE,
            R.DISPONIBLE_PARA_RETIRO,
            None,
            "Ejemplar B-0 asignado: retirar hasta el 13/11/2026",
        ),
        (R.DISPONIBLE_PARA_RETIRO, R.CUMPLIDA, BETO, "Retirada: préstamo P-2026-000118"),
    ]


@pytest.mark.ca("CA-RES-16")
def test_lo_automatico_lo_hace_el_sistema():
    vencida = reserva(R.DISPONIBLE_PARA_RETIRO, ejemplar_id=301, vencimiento_retiro=HOY)
    entre_sedes = reserva()

    vencida.vencer(date(2026, 11, 11), AHORA)
    entre_sedes.convertir_en_prestamo(301, 118, AHORA, "P-2026-000118")

    assert [m.usuario for m in vencida.movimientos_pendientes] == [None]
    assert [m.usuario for m in entre_sedes.movimientos_pendientes] == [None]


def test_cancelar_guarda_quien_y_por_que():
    r = reserva()

    r.cancelar(AHORA, LUCIA, "Ya lo conseguí")
    otra = reserva()
    otra.cancelar(AHORA, LUCIA, None)

    assert _historial(r) == [(R.PENDIENTE, R.CANCELADA, LUCIA, "Ya lo conseguí")]
    assert _historial(otra)[0][3] == "Cancelada"
    assert r.fecha_cierre == AHORA
