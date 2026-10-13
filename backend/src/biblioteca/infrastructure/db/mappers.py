"""Mapeo imperativo: tablas de `tables.py` sobre las clases del dominio (ARCHITECTURE.md §5.4).

Las entidades no heredan del ORM; SQLAlchemy las instrumenta acá. Las columnas
`creado_en` y `actualizado_en` las maneja la base y no se exponen al dominio.

Para mapear una entidad nueva: agregar un `map_imperatively` en `configurar_mapeos`,
con los mismos nombres de atributo que las columnas.
"""

from sqlalchemy.orm import registry, relationship

from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.entities.usuario import Usuario
from biblioteca.infrastructure.db import tables as t

mapper_registry = registry(metadata=t.metadata)

_MARCAS_DE_TIEMPO = ["creado_en", "actualizado_en"]
_configurado = False


def configurar_mapeos() -> None:
    """Idempotente: se puede llamar desde la app, la CLI y los tests."""
    global _configurado
    if _configurado:
        return

    mapper_registry.map_imperatively(
        HorarioSede, t.horario_sede, exclude_properties=_MARCAS_DE_TIEMPO
    )
    mapper_registry.map_imperatively(
        Sede,
        t.sede,
        exclude_properties=_MARCAS_DE_TIEMPO,
        properties={
            "horarios": relationship(
                HorarioSede,
                cascade="all, delete-orphan",
                lazy="selectin",
                order_by=[t.horario_sede.c.dia_semana, t.horario_sede.c.hora_apertura],
            )
        },
    )
    mapper_registry.map_imperatively(Usuario, t.usuario, exclude_properties=_MARCAS_DE_TIEMPO)

    _configurado = True
