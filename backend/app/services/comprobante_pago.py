"""Comprobante de pago de una multa en PDF (una página A4)."""

from datetime import tzinfo
from decimal import Decimal

from app.models.pago import FormaEnLinea, MedioPago, Pago
from app.utils.pdf import ALTO, ANCHO, DocumentoPdf

MEDIOS = {
    MedioPago.EFECTIVO: "Efectivo",
    MedioPago.DEBITO: "Tarjeta de débito",
    MedioPago.CREDITO: "Tarjeta de crédito",
    MedioPago.TRANSFERENCIA: "Transferencia",
    MedioPago.NO_REGISTRADO: "Sin dato",
}
FORMAS = {
    FormaEnLinea.TARJETA_CREDITO: "Tarjeta de crédito",
    FormaEnLinea.TARJETA_DEBITO: "Tarjeta de débito",
    FormaEnLinea.DINERO_EN_CUENTA: "Dinero en cuenta",
}
MARGEN = 56


def formatear_monto(monto: Decimal) -> str:
    """``$ 1.000,00`` (formato argentino)."""
    entero, decimales = f"{monto:,.2f}".split(".")
    return f"$ {entero.replace(',', '.')},{decimales}"


def medio_de_pago(pago: Pago) -> str:
    """Cómo se pagó, para mostrar: «En línea (simulado) · Tarjeta de crédito terminada en 3704»."""
    if pago.medio != MedioPago.EN_LINEA:
        return MEDIOS[pago.medio]
    forma = FORMAS[pago.forma_en_linea] if pago.forma_en_linea else "Sin dato"
    if pago.tarjeta_ultimos4:
        forma += f" terminada en {pago.tarjeta_ultimos4}"
    return f"En línea (simulado) · {forma}"


def nombre_de_archivo(pago: Pago) -> str:
    return f"comprobante-{pago.numero_comprobante}.pdf"


def comprobante_pdf(pago: Pago, zona: tzinfo) -> bytes:
    """Comprobante de un pago aprobado, con las fechas en la zona de negocio."""
    assert pago.numero_comprobante is not None and pago.acreditado_en is not None
    pdf = DocumentoPdf(titulo=f"Comprobante de pago {pago.numero_comprobante}")
    y = ALTO - 72
    pdf.texto(MARGEN, y, "Red de Bibliotecas Públicas", 10)
    pdf.texto(MARGEN, y - 26, "Comprobante de pago", 20, negrita=True)
    pdf.texto(ANCHO - 220, y - 26, pago.numero_comprobante, 14, negrita=True)
    pdf.linea(MARGEN, y - 42, ANCHO - MARGEN, y - 42)

    acreditado = pago.acreditado_en.astimezone(zona)
    concepto = f"Multa del préstamo {pago.numero_prestamo or pago.multa_id}"
    if pago.dias_atraso:
        concepto += f" ({pago.dias_atraso} día(s) de atraso)"
    filas = [
        ("Fecha y hora", acreditado.strftime("%d/%m/%Y %H:%M")),
        ("Socio", f"{pago.socio_nombre or ''} (n.º {pago.numero_socio or '-'})"),
        ("Concepto", concepto),
        ("Libro", pago.libro_titulo or "-"),
        ("Medio de pago", medio_de_pago(pago)),
    ]
    if pago.comprobante:
        filas.append(("Comprobante del cobro", pago.comprobante))
    if pago.medio != MedioPago.EN_LINEA and pago.registrado_por:
        filas.append(("Cobrado por", pago.registrado_por.nombre))

    y -= 80
    for etiqueta, valor in filas:
        pdf.texto(MARGEN, y, etiqueta, 10, negrita=True)
        pdf.texto(MARGEN + 150, y, valor, 11)
        y -= 24

    pdf.linea(MARGEN, y, ANCHO - MARGEN, y)
    pdf.texto(MARGEN, y - 30, "Total pagado", 13, negrita=True)
    pdf.texto(MARGEN + 150, y - 30, formatear_monto(pago.monto), 16, negrita=True)
    pdf.texto(MARGEN, y - 60, "Estado: aprobado. La multa quedó saldada.", 10)
    if pago.medio == MedioPago.EN_LINEA:
        pdf.texto(
            MARGEN, y - 78, "Pago simulado para la demostración: no se realizó un cobro real.", 9
        )
    pdf.texto(MARGEN, 48, "Sistema de Préstamos Interbibliotecarios", 8)
    return pdf.a_bytes()
