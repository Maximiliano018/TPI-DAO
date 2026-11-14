"""Catálogo: cambios en el historial del ejemplar y versión del libro

- ``movimiento_ejemplar.cambios``: además del estado de disponibilidad, cada movimiento guarda
  los cambios de estado físico, observaciones y sede (``[{campo, antes, despues}]``). Los
  movimientos anteriores quedan con la lista vacía.
- ``libro.version``: concurrencia optimista al modificar un libro.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar una columna con valor por defecto no dispara el disparador de solo inserción.
    op.add_column(
        "movimiento_ejemplar",
        sa.Column(
            "cambios",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "libro",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("libro", "version")
    op.drop_column("movimiento_ejemplar", "cambios")
