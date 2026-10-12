from sqlalchemy import select
from sqlalchemy.orm import Session

from biblioteca.domain.errors import NoEncontrado
from biblioteca.infrastructure.db.tables import parametro


def parametro_entero(db: Session, clave: str) -> int:
    """Valor de un parámetro del sistema (ARCHITECTURE.md §5.5)."""
    valor = db.execute(select(parametro.c.valor).where(parametro.c.clave == clave)).scalar()
    if valor is None:
        raise NoEncontrado(f"Falta el parámetro del sistema '{clave}'")
    return int(valor)
