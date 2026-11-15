"""Pago de multas: mostrador y pago en línea simulado (dominio)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.exceptions import ErrorDeValidacion, TransicionInvalida
from app.models.pago import EstadoPago, MedioPago, Pago
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
BIBLIO = UsuarioRef(2, "Biblio")
SOCIA = UsuarioRef(7, "Sol Socia")


def en_linea() -> Pago:
    return Pago.en_linea(multa_id=14, monto=Decimal("1000.00"), actor=SOCIA, ahora=AHORA)


@pytest.mark.ca("CA-DEV-21")
def test_el_pago_de_mostrador_nace_aprobado_con_su_medio():
    pago = Pago.manual(
        multa_id=14,
        monto=Decimal("1000.00"),
        medio=MedioPago.DEBITO,
        comprobante="  Cupón   004512 ",
        actor=BIBLIO,
        ahora=AHORA,
    )

    assert (pago.estado, pago.medio, pago.comprobante, pago.acreditado_en) == (
        EstadoPago.APROBADO,
        MedioPago.DEBITO,
        "Cupón 004512",
        AHORA,
    )
    with pytest.raises(ErrorDeValidacion):
        Pago.manual(
            multa_id=14,
            monto=Decimal("1"),
            medio=MedioPago.EN_LINEA,
            comprobante=None,
            actor=BIBLIO,
            ahora=AHORA,
        )


@pytest.mark.ca("CA-DEV-23", "CA-DEV-24", "CA-DEV-25")
def test_el_pago_en_linea_se_aprueba_rechaza_o_cancela_solo_si_esta_pendiente():
    aprobado, rechazado, cancelado = en_linea(), en_linea(), en_linea()

    aprobado.aprobar(AHORA)
    rechazado.rechazar("Rechazado en el checkout simulado")
    cancelado.cancelar("Se cobró en el mostrador")

    assert (aprobado.estado, aprobado.acreditado_en) == (EstadoPago.APROBADO, AHORA)
    assert (rechazado.estado, rechazado.motivo) == (
        EstadoPago.RECHAZADO,
        "Rechazado en el checkout simulado",
    )
    assert cancelado.estado == EstadoPago.CANCELADO
    for pago in (aprobado, rechazado, cancelado):
        with pytest.raises(TransicionInvalida):
            pago.aprobar(AHORA)


# --- checkout simulado y comprobante ---------------------------------------------------------


@pytest.mark.ca("CA-DEV-23", "CA-DEV-24", "CA-DEV-28")
def test_el_checkout_simulado_aprueba_salvo_la_tarjeta_de_prueba_rechazada():
    from app.models.pago import FormaEnLinea

    con_tarjeta, rechazada, en_cuenta = en_linea(), en_linea(), en_linea()

    assert con_tarjeta.pagar_en_linea(FormaEnLinea.TARJETA_CREDITO, "3704", AHORA) is True
    assert rechazada.pagar_en_linea(FormaEnLinea.TARJETA_DEBITO, "0002", AHORA) is False
    assert en_cuenta.pagar_en_linea(FormaEnLinea.DINERO_EN_CUENTA, None, AHORA) is True

    assert (con_tarjeta.estado, con_tarjeta.tarjeta_ultimos4) == (EstadoPago.APROBADO, "3704")
    assert (rechazada.estado, rechazada.motivo) == (
        EstadoPago.RECHAZADO,
        "Tarjeta rechazada por el emisor (tarjeta de prueba)",
    )
    with pytest.raises(ErrorDeValidacion):
        en_linea().pagar_en_linea(FormaEnLinea.TARJETA_CREDITO, "37", AHORA)
    with pytest.raises(ErrorDeValidacion):
        en_linea().pagar_en_linea(FormaEnLinea.DINERO_EN_CUENTA, "3704", AHORA)


@pytest.mark.ca("CA-DEV-27")
def test_solo_un_pago_aprobado_tiene_numero_de_comprobante():
    pago = en_linea()
    pago.id = 7
    assert pago.numero_comprobante is None

    pago.aprobar(AHORA)

    assert pago.numero_comprobante == "PG-2026-000007"


def test_el_pdf_es_valido_y_admite_acentos():
    import re

    from app.utils.pdf import DocumentoPdf

    pdf = DocumentoPdf(titulo="Prueba")
    pdf.texto(56, 700, "Préstamo (año) \\ niño", 12, negrita=True)
    pdf.linea(56, 690, 539, 690)
    datos = pdf.a_bytes()

    assert datos.startswith(b"%PDF-1.4") and datos.rstrip().endswith(b"%%EOF")
    assert "(Préstamo \\(año\\) \\\\ niño)".encode("cp1252") in datos
    # Cada entrada de la tabla xref apunta al comienzo de su objeto.
    inicio = int(re.search(rb"startxref\n(\d+)", datos).group(1))
    entradas = re.findall(rb"(\d{10}) 00000 n", datos[inicio:])
    for numero, posicion in enumerate(entradas, start=1):
        assert datos[int(posicion) :].startswith(f"{numero} 0 obj".encode())


@pytest.mark.ca("CA-DEV-27")
def test_el_comprobante_tiene_los_datos_del_pago():
    from zoneinfo import ZoneInfo

    from app.models.pago import FormaEnLinea
    from app.services.comprobante_pago import comprobante_pdf, formatear_monto, nombre_de_archivo

    pago = en_linea()
    pago.id = 7
    pago.numero_prestamo, pago.libro_titulo, pago.dias_atraso = "P-2026-000118", "Rayuela", 5
    pago.socio_nombre, pago.numero_socio = "Lucía Socio", "00012"
    pago.pagar_en_linea(FormaEnLinea.TARJETA_CREDITO, "3704", AHORA)

    datos = comprobante_pdf(pago, ZoneInfo("America/Argentina/Cordoba"))

    for texto in (
        "PG-2026-000007",
        "20/11/2026 12:00",
        "Lucía Socio",
        "Multa del préstamo P-2026-000118 (5 día(s) de atraso)",
        "Tarjeta de crédito terminada en 3704",
        "$ 1.000,00",
        "no se realizó un cobro real",
    ):
        assert texto.replace("(", "\\(").replace(")", "\\)").encode("cp1252") in datos, texto
    assert nombre_de_archivo(pago) == "comprobante-PG-2026-000007.pdf"
    assert formatear_monto(Decimal("1234567.5")) == "$ 1.234.567,50"
