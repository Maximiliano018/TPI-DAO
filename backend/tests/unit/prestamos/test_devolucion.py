"""Devolución y multa: validaciones, días de atraso y política de cálculo (Strategy)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.exceptions import ErrorDeValidacion, TransicionInvalida
from app.models.devolucion import Devolucion, EstadoMulta, EstadoRecibido
from app.models.policies.multa import MultaFijaPorDia
from app.models.prestamo import Prestamo
from app.models.states.prestamo import EstadoPrestamoEnum as P
from app.models.usuario import UsuarioRef
from tests.unit.prestamos.test_prestamo import prestamo

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
HOY = date(2026, 11, 20)
BIBLIO = UsuarioRef(2, "Biblio")
POLITICA = MultaFijaPorDia(Decimal("200.00"))


def activo(vence: date, estado: P = P.ACTIVO) -> Prestamo:
    return prestamo(estado, fecha_inicio=vence - timedelta(days=14), fecha_vencimiento=vence)


def devolver(p: Prestamo, fecha: date = HOY, estado=EstadoRecibido.BUENO, obs=None, politica=None):
    return Devolucion.registrar(
        prestamo=p,
        fecha_hora=AHORA,
        fecha=fecha,
        hoy=HOY,
        estado_recibido=estado,
        observaciones=obs,
        politica=politica or POLITICA,
        actor=BIBLIO,
    )


# --- política de multa (Strategy) ------------------------------------------------------------


@pytest.mark.ca("CA-DEV-06", "CA-DEV-07")
def test_la_multa_es_dias_de_atraso_por_el_monto_vigente():
    assert POLITICA.calcular(0) == Decimal("0.00")
    assert POLITICA.calcular(1) == Decimal("200.00")
    assert POLITICA.calcular(5) == Decimal("1000.00")
    # Cambio del monto en la configuración: la política nueva usa el monto vigente.
    assert MultaFijaPorDia(Decimal("350")).calcular(5) == Decimal("1750.00")


def test_la_multa_respeta_el_tope_configurado():
    assert MultaFijaPorDia(Decimal("200"), tope=Decimal("1500")).calcular(30) == Decimal("1500.00")


# --- devolución ------------------------------------------------------------------------------


@pytest.mark.ca("CA-DEV-05")
def test_devolver_el_dia_del_vencimiento_no_genera_multa():
    devolucion, multa = devolver(activo(vence=HOY))

    assert (devolucion.dias_atraso, multa) == (0, None)
    assert devolucion.sede_id == 1


@pytest.mark.ca("CA-DEV-06")
def test_devolver_cinco_dias_tarde_genera_una_multa_pendiente():
    devolucion, multa = devolver(activo(vence=HOY - timedelta(days=5), estado=P.VENCIDO))

    assert devolucion.dias_atraso == 5
    assert multa is not None
    assert (multa.monto_por_dia, multa.monto_total, multa.estado) == (
        Decimal("200.00"),
        Decimal("1000.00"),
        EstadoMulta.PENDIENTE,
    )
    assert (multa.socio_id, multa.prestamo_id) == (45, 1)


@pytest.mark.ca("CA-DEV-07")
def test_la_multa_usa_el_monto_de_la_politica_vigente():
    p = activo(vence=HOY - timedelta(days=2))
    _, multa = devolver(p, politica=MultaFijaPorDia(Decimal(300)))

    assert multa is not None and multa.monto_total == Decimal("600.00")


@pytest.mark.ca("CA-DEV-02")
@pytest.mark.parametrize("estado", [P.DEVUELTO, P.CANCELADO, P.SOLICITADO, P.EN_ENVIO])
def test_solo_se_devuelve_un_prestamo_activo_o_vencido(estado):
    with pytest.raises(TransicionInvalida):
        devolver(activo(vence=HOY, estado=estado))


@pytest.mark.ca("CA-DEV-04")
def test_la_fecha_no_puede_ser_futura_ni_anterior_a_la_entrega():
    p = activo(vence=HOY)
    with pytest.raises(ErrorDeValidacion) as futura:
        devolver(p, fecha=HOY + timedelta(days=1))
    assert futura.value.detalles[0]["campo"] == "fecha_hora"
    with pytest.raises(ErrorDeValidacion):
        devolver(p, fecha=HOY - timedelta(days=15))


@pytest.mark.parametrize("estado", [EstadoRecibido.DANADO, EstadoRecibido.EXTRAVIADO])
def test_un_dano_o_extravio_exige_observaciones(estado):
    with pytest.raises(ErrorDeValidacion) as error:
        devolver(activo(vence=HOY), estado=estado, obs="   ")
    assert error.value.detalles[0]["campo"] == "observaciones"

    devolucion, _ = devolver(activo(vence=HOY), estado=estado, obs="  Tapa  rota ")
    assert devolucion.observaciones == "Tapa rota"


# --- multa -----------------------------------------------------------------------------------


@pytest.mark.ca("CA-DEV-10")
def test_saldar_una_multa_registra_quien_y_cuando_y_no_se_salda_dos_veces():
    _, multa = devolver(activo(vence=HOY - timedelta(days=1)))
    assert multa is not None

    multa.saldar(BIBLIO, AHORA)

    assert (multa.estado, multa.fecha_saldada, multa.saldada_por) == (
        EstadoMulta.SALDADA,
        AHORA,
        BIBLIO,
    )
    with pytest.raises(TransicionInvalida):
        multa.saldar(BIBLIO, AHORA)
