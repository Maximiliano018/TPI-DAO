"""Parámetros de negocio: plazos, límites y montos configurables.

No son constantes del código ni variables de entorno: son filas de la tabla ``parametro`` que el
administrador puede cambiar sin redesplegar (ver ``docs/negocio/00-contexto-y-actores.md``).
"""

from dataclasses import dataclass, fields
from decimal import Decimal

from app.models.policies.multa import MultaFijaPorDia
from app.models.valores import error_de_campo

# Parámetros en pesos: admiten centavos y montos mayores que los plazos.
MONTOS = frozenset({"multa_por_dia", "multa_tope_por_prestamo"})
MONTO_MAXIMO = Decimal("1000000")


@dataclass(frozen=True)
class Parametros:
    """Valores vigentes. Los nombres coinciden con la clave de cada fila de ``parametro``."""

    plazo_prestamo_local_dias: int = 14
    plazo_prestamo_inter_dias: int = 21
    renovaciones_maximas: int = 1
    prestamos_maximos_por_socio: int = 3
    reservas_maximas_por_socio: int = 3
    vigencia_retiro_reserva_dias: int = 3
    vigencia_retiro_prestamo_dias: int = 3
    multa_por_dia: Decimal = Decimal("200.00")
    # Tope de la multa de un préstamo; 0 = sin tope (CU-DEV-02, A2).
    multa_tope_por_prestamo: Decimal = Decimal("0.00")
    transito_maximo_dias: int = 7
    despacho_maximo_dias: int = 3

    def politica_multa(self) -> MultaFijaPorDia:
        """Strategy de cálculo vigente: monto por día con el tope configurado (si hay)."""
        tope = self.multa_tope_por_prestamo or None
        return MultaFijaPorDia(self.multa_por_dia, tope)

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
            Decimal(texto).quantize(Decimal("0.01")) if clave in MONTOS else int(texto)
        )
    except (ArithmeticError, ValueError) as error:
        raise error_de_campo("valor", "El valor debe ser un número.") from error
    if clave in MONTOS:
        if not 0 <= valor <= MONTO_MAXIMO:
            raise error_de_campo("valor", f"El monto debe estar entre 0 y {MONTO_MAXIMO}.")
        return valor
    minimo = 0 if clave == "renovaciones_maximas" else 1
    if not minimo <= valor <= 365 * 10:
        raise error_de_campo("valor", f"El valor debe estar entre {minimo} y 3650.")
    return valor
