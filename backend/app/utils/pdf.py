"""Generador mínimo de PDF de una página (texto y líneas), sin dependencias externas.

Alcanza para comprobantes: usa las fuentes estándar de PDF (Helvetica y Helvetica-Bold, que todo
lector trae) con codificación WinAnsi, así que admite los acentos y la «ñ» del español. Las
coordenadas son en puntos desde la esquina inferior izquierda de una hoja A4 (595 × 842).
"""

from dataclasses import dataclass, field

ANCHO, ALTO = 595, 842


def _texto_pdf(texto: str) -> bytes:
    """Cadena literal de PDF: se escapan ``\\``, ``(`` y ``)`` y se codifica en WinAnsi."""
    escapado = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return b"(" + escapado.encode("cp1252", errors="replace") + b")"


@dataclass
class DocumentoPdf:
    """Una página A4 a la que se le agregan textos y líneas; ``a_bytes`` arma el archivo."""

    titulo: str = "Documento"
    _operaciones: list[bytes] = field(default_factory=list)

    def texto(
        self, x: float, y: float, contenido: str, tamano: float = 11, negrita: bool = False
    ) -> None:
        fuente = b"/F2" if negrita else b"/F1"
        self._operaciones.append(
            b"BT "
            + fuente
            + f" {tamano:g} Tf {x:g} {y:g} Td ".encode()
            + _texto_pdf(contenido)
            + b" Tj ET"
        )

    def linea(self, x1: float, y1: float, x2: float, y2: float, grosor: float = 0.8) -> None:
        self._operaciones.append(f"{grosor:g} w {x1:g} {y1:g} m {x2:g} {y2:g} l S".encode())

    def a_bytes(self) -> bytes:
        contenido = b"\n".join(self._operaciones)
        objetos = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ANCHO} {ALTO}] ".encode()
            + b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>",
            f"<< /Length {len(contenido)} >>\nstream\n".encode() + contenido + b"\nendstream",
            b"<< /Title " + _texto_pdf(self.titulo) + b" /Producer (TPI-DAO) >>",
        ]
        salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        posiciones = []
        for numero, cuerpo in enumerate(objetos, start=1):
            posiciones.append(len(salida))
            salida += f"{numero} 0 obj\n".encode() + cuerpo + b"\nendobj\n"
        inicio_xref = len(salida)
        salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
        for posicion in posiciones:
            salida += f"{posicion:010d} 00000 n \n".encode()
        salida += (
            f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R /Info {len(objetos)} 0 R >>\n"
            f"startxref\n{inicio_xref}\n%%EOF\n"
        ).encode()
        return bytes(salida)
