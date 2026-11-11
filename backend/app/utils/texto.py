"""Normalización de texto para comparar sin distinguir mayúsculas, tildes ni puntuación."""

import re
import unicodedata

_ABREVIATURAS = {
    "av": "avenida",
    "avda": "avenida",
    "bv": "boulevard",
    "blvd": "boulevard",
    "gral": "general",
    "cnel": "coronel",
    "dr": "doctor",
    "pje": "pasaje",
    "sgto": "sargento",
    "tte": "teniente",
    "pres": "presidente",
    "ing": "ingeniero",
    "hnos": "hermanos",
    "s/n": "sn",
}


def quitar_tildes(texto: str) -> str:
    """Quita tildes y diéresis (la ``ñ`` se conserva como ``n`` para comparar)."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin puntuación y con espacios simples."""
    sin_tildes = quitar_tildes(texto).lower().strip()
    sin_puntuacion = re.sub(r"[^\w\s/]", " ", sin_tildes)
    return re.sub(r"\s+", " ", sin_puntuacion).strip()


def normalizar_calle(calle: str) -> str:
    """Normaliza una calle y unifica sus abreviaturas habituales (``Av.`` = ``Avenida``)."""
    palabras = normalizar(calle).split(" ")
    return " ".join(_ABREVIATURAS.get(p, p) for p in palabras)


def normalizar_numero(numero: str) -> str:
    """Normaliza un número de puerta: sin ceros a la izquierda y ``S/N`` unificado."""
    limpio = normalizar(numero).replace(" ", "")
    if limpio in ("sn", "s/n"):
        return "sn"
    return re.sub(r"^0+(?=\d)", "", limpio)
