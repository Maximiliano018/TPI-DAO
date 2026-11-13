"""Reserva: estados (State) y vencimiento del retiro."""

from datetime import UTC, date, datetime

import pytest

from app.exceptions import TransicionInvalida
from app.models.reserva import Reserva
from app.models.states.reserva import EstadoReservaEnum as R
from app.models.states.reserva import estado_reserva

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
HOY = date(2026, 11, 10)


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


@pytest.mark.ca("CA-RES-07")
def test_asignar_deja_la_reserva_disponible_por_la_vigencia():
    r = reserva()

    r.asignar(301, HOY, 3)

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
        r.cancelar(AHORA)
    with pytest.raises(TransicionInvalida):
        r.asignar(301, HOY, 3)


def test_retirar_solo_si_esta_disponible_para_retiro():
    pendiente = reserva()
    disponible = reserva(R.DISPONIBLE_PARA_RETIRO, ejemplar_id=301, vencimiento_retiro=HOY)

    with pytest.raises(TransicionInvalida):
        pendiente.cumplir(118, AHORA)
    disponible.cumplir(118, AHORA)
    assert (disponible.estado_nombre, disponible.prestamo_id) == (R.CUMPLIDA, 118)


def test_un_ejemplar_de_otra_sede_cumple_la_reserva_con_un_prestamo():
    r = reserva()

    r.convertir_en_prestamo(301, 118, AHORA)

    assert (r.estado_nombre, r.ejemplar_id, r.prestamo_id) == (R.CUMPLIDA, 301, 118)
    assert not r.esta_activa
