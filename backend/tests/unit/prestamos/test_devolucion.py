"""Devolución y multa: validaciones, días de atraso y política de cálculo (Strategy)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.exceptions import ErrorDeValidacion, TransicionInvalida
from app.models.devolucion import Devolucion, EstadoMulta, EstadoRecibido
from app.models.parametros import Parametros, convertir
from app.models.policies.multa import MontoFijoPorIncidencia, MultaFijaPorDia, TipoMulta
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


def registrar(
    p: Prestamo,
    fecha: date = HOY,
    estado=EstadoRecibido.BUENO,
    obs=None,
    politica=None,
    incidencia=None,
):
    """Devolución y todas sus multas."""
    return Devolucion.registrar(
        prestamo=p,
        fecha_hora=AHORA,
        fecha=fecha,
        hoy=HOY,
        estado_recibido=estado,
        observaciones=obs,
        politica=politica or POLITICA,
        actor=BIBLIO,
        politica_incidencia=incidencia,
    )


def devolver(p: Prestamo, fecha: date = HOY, estado=EstadoRecibido.BUENO, obs=None, politica=None):
    """Devolución y su multa por atraso (o ``None``)."""
    devolucion, multas = registrar(p, fecha, estado, obs, politica)
    atraso = [m for m in multas if m.tipo == TipoMulta.ATRASO]
    return devolucion, atraso[0] if atraso else None


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


# --- fecha retroactiva y tope ------------------------------------------------------------------


@pytest.mark.ca("CA-DEV-17")
def test_una_fecha_anterior_a_hoy_exige_motivo():
    p = activo(HOY - timedelta(days=5))

    with pytest.raises(ErrorDeValidacion) as error:
        devolver(p, fecha=HOY - timedelta(days=5))
    assert error.value.detalles[0]["campo"] == "motivo_fecha"

    d, multas = Devolucion.registrar(
        prestamo=p,
        fecha_hora=AHORA - timedelta(days=5),
        fecha=HOY - timedelta(days=5),
        hoy=HOY,
        estado_recibido=EstadoRecibido.BUENO,
        observaciones=None,
        politica=POLITICA,
        actor=BIBLIO,
        ahora=AHORA,
        motivo_fecha="  Lo dejó   en el buzón ",
    )
    assert (d.motivo_fecha, d.registrada_en, multas) == ("Lo dejó en el buzón", AHORA, [])
    assert d.texto_del_historial(HOY - timedelta(days=5), HOY) == (
        "Devuelto el 15/11/2026 (registrado el 20/11/2026): Lo dejó en el buzón"
    )


def test_hoy_no_pide_motivo_y_el_historial_dice_devuelto():
    d, _ = devolver(activo(HOY))

    assert (d.motivo_fecha, d.es_retroactiva) == (None, False)
    assert d.texto_del_historial(HOY, HOY) == "Devuelto"


@pytest.mark.ca("CA-DEV-18")
def test_la_politica_vigente_aplica_el_tope_y_cero_es_sin_tope():

    con_tope = Parametros(multa_tope_por_prestamo=Decimal("500.00")).politica_multa()
    sin_tope = Parametros().politica_multa()

    assert con_tope.calcular(5) == Decimal("500.00")
    assert sin_tope.calcular(5) == Decimal("1000.00")
    assert convertir("multa_tope_por_prestamo", "25000") == Decimal("25000.00")
    with pytest.raises(ErrorDeValidacion):
        convertir("multa_tope_por_prestamo", "-1")


# --- multas por daño y extravío (RF-DEV-23) ---------------------------------------------------

INCIDENCIA = MontoFijoPorIncidencia(Decimal("3000"), Decimal("15000"))


@pytest.mark.ca("CA-DEV-29")
def test_devolver_danado_genera_la_multa_por_danio_sin_dias():
    _, multas = registrar(
        activo(vence=HOY), estado=EstadoRecibido.DANADO, obs="Roto", incidencia=INCIDENCIA
    )

    (multa,) = multas
    assert (multa.tipo, multa.monto_total, multa.dias_atraso, multa.monto_por_dia) == (
        TipoMulta.DANIO,
        Decimal("3000.00"),
        None,
        None,
    )
    assert (multa.concepto, multa.estado, multa.socio_id) == (
        "Daño del ejemplar",
        EstadoMulta.PENDIENTE,
        45,
    )


@pytest.mark.ca("CA-DEV-30", "CA-DEV-32")
def test_un_extravio_tardio_genera_la_de_atraso_con_tope_y_la_de_extravio_entera():
    p = activo(vence=HOY - timedelta(days=5), estado=P.VENCIDO)
    con_tope = MultaFijaPorDia(Decimal("200"), Decimal("500"))

    _, multas = registrar(
        p,
        estado=EstadoRecibido.EXTRAVIADO,
        obs="Lo perdió",
        politica=con_tope,
        incidencia=INCIDENCIA,
    )

    assert [(m.tipo, m.monto_total) for m in multas] == [
        (TipoMulta.ATRASO, Decimal("500.00")),
        (TipoMulta.EXTRAVIO, Decimal("15000.00")),
    ]
    assert multas[0].concepto == "Atraso de 5 días"


@pytest.mark.ca("CA-DEV-31")
@pytest.mark.parametrize(
    ("estado", "incidencia"),
    [
        (EstadoRecibido.DANADO, MontoFijoPorIncidencia(Decimal("0"), Decimal("15000"))),
        (EstadoRecibido.DANADO, None),
        (EstadoRecibido.REGULAR, INCIDENCIA),
        (EstadoRecibido.BUENO, INCIDENCIA),
    ],
)
def test_sin_monto_o_sin_dano_no_hay_multa_por_incidencia(estado, incidencia):
    _, multas = registrar(activo(vence=HOY), estado=estado, obs="Algo", incidencia=incidencia)

    assert multas == []


def test_la_politica_por_incidencia_no_calcula_atrasos():
    with pytest.raises(ValueError, match="ATRASO"):
        INCIDENCIA.calcular(TipoMulta.ATRASO)


def test_los_montos_por_danio_y_extravio_son_parametros_en_pesos():
    politica = Parametros(
        multa_por_danio=Decimal("2500"), multa_por_extravio=Decimal("9000")
    ).politica_multa_por_incidencia()

    assert (politica.calcular(TipoMulta.DANIO), politica.calcular(TipoMulta.EXTRAVIO)) == (
        Decimal("2500.00"),
        Decimal("9000.00"),
    )
    assert convertir("multa_por_extravio", "12000.5") == Decimal("12000.50")
    with pytest.raises(ErrorDeValidacion):
        convertir("multa_por_danio", "-1")
