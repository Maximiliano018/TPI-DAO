"""Parámetros de negocio: plazos, límites y montos configurables.

No son constantes del código ni variables de entorno: son filas de la tabla ``parametro`` que el
administrador puede cambiar sin redesplegar (ver ``docs/negocio/00-contexto-y-actores.md``).
"""

from dataclasses import dataclass, fields
from decimal import Decimal

from app.models.valores import error_de_campo


@dataclass(frozen=True)
class Parametros:
    """Valores vigentes. Los nombres coinciden con la clave de cada fila de ``parametro``."""

    plazo_prestamo_local_dias: int = 14
    plazo_prestamo_inter_dias: int = 21
    renovaciones_maximas: int = 1
    prestamos_maximos_por_socio: int = 3
    reservas_maximas_por_socio: int = 3
    vigencia_retiro_reserva_dias: int = 3
    multa_por_dia: Decimal = Decimal("200.00")
    transito_maximo_dias: int = 7

    @classmethod
    def claves(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    @classmethod
    def desde_textos(cls, valores: dict[str, str]) -> "Parametros":
        """Construye los parámetros a partir de los textos guardados (con los valores por
        defecto para las claves que falten)."""
        convertidos: dict[str, object] = {}
        for campo in fields(cls):
            if campo.name in valores:
                convertidos[campo.name] = convertir(campo.name, valores[campo.name])
        return cls(**convertidos)  # type: ignore[arg-type]


def convertir(clave: str, texto: str) -> int | Decimal:
    """Convierte y valida el valor de un parámetro.

    Raises:
        ErrorDeValidacion: Clave desconocida o valor no numérico, negativo o fuera de rango.
    """
    if clave not in Parametros.claves():
        raise error_de_campo("clave", f"No existe el parámetro {clave}.")
    try:
        valor: int | Decimal = (
            Decimal(texto).quantize(Decimal("0.01")) if clave == "multa_por_dia" else int(texto)
        )
    except (ArithmeticError, ValueError) as error:
        raise error_de_campo("valor", "El valor debe ser un número.") from error
    minimo = 0 if clave in ("renovaciones_maximas", "multa_por_dia") else 1
    if not minimo <= valor <= 365 * 10:
        raise error_de_campo("valor", f"El valor debe estar entre {minimo} y 3650.")
    return valor
