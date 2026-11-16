"""Datos de demostración: la red completa con 90 días de historia.

Uso: ``python -m app.db.seed``. Solo corre con ``ENTORNO=desarrollo`` o ``ENTORNO=test``, para
no cargar usuarios con contraseñas conocidas en un entorno real, y solo si la base todavía no
tiene sedes (idempotente: una segunda ejecución no hace nada).

Todo se carga con los casos de uso reales y un reloj que avanza desde hace 90 días hasta hoy
(ver ``app/db/seed_historia.py``): sedes, personal, parámetros, socios, catálogo, préstamos,
remitos, reservas, devoluciones, multas y pagos, con sus historiales y su auditoría. Sobre esa
historia, ``app/db/seed_volumen.py`` suma unos 120 libros más con sus ejemplares, 70 socios y
dos meses de movimiento diario, para que las pantallas y los reportes tengan muchos datos. Las
provincias, localidades y categorías vienen de las migraciones.

La contraseña de todos los usuarios de demostración es ``SEED_PASSWORD`` (de 10 a 128
caracteres, con al menos una letra y un número, como cualquier contraseña del sistema).
"""

import sys
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import SedeORM
from app.db.seed_historia import LIBROS, PERSONAL, SEDES, SOCIOS, Historia
from app.db.session import crear_fabrica_sesiones
from app.exceptions import ErrorDeValidacion
from app.models.usuario import validar_clave

__all__ = ["LIBROS", "PERSONAL", "SEDES", "SOCIOS", "cargar", "main"]

ENTORNOS_PERMITIDOS = {"desarrollo", "test"}


def cargar(
    sesion: Session,
    clave: str,
    volumen: bool = True,
    dias_de_movimiento: int = 59,
    avisar: Callable[[str], None] = lambda _texto: None,
) -> bool:
    """Carga la historia de demostración si la base no tiene sedes. Devuelve si cargó.

    ``volumen`` suma el catálogo amplio, más socios y ``dias_de_movimiento`` días de préstamos,
    envíos, devoluciones, reservas y multas (``seed_volumen``). Sin volumen queda solo la
    historia contada a mano, que es lo que usan las pruebas rápidas.
    """
    if sesion.scalar(select(func.count(SedeORM.id))):
        return False
    Historia(sesion, clave).contar(volumen, dias_de_movimiento, avisar)
    sesion.commit()
    return True


def main() -> int:
    settings = get_settings()
    if settings.entorno not in ENTORNOS_PERMITIDOS:
        print(f"El seed no corre con ENTORNO={settings.entorno!r}.", file=sys.stderr)
        return 1
    if not settings.seed_password:
        print("Defina SEED_PASSWORD en el entorno o en .env.", file=sys.stderr)
        return 1
    try:
        validar_clave(settings.seed_password)
    except ErrorDeValidacion as error:
        print(f"SEED_PASSWORD no es válida: {error}", file=sys.stderr)
        return 1
    print("Cargando los datos de demostración (puede tardar unos minutos)...")
    with crear_fabrica_sesiones()() as sesion:
        cargado = cargar(sesion, settings.seed_password, avisar=print)
    print("Datos de demostración cargados." if cargado else "La base ya tenía datos: sin cambios.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
