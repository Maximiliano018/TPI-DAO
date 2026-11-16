"""Portada del libro

- Columna ``libro.portada_url``: enlace a la imagen de tapa (opcional). Puede ser una dirección web
  o una de las portadas que sirve el frontend (``/portadas/...``).
- ``ck_libro_portada_url_valida``: la base rechaza cualquier otro valor (por ejemplo
  ``javascript:``), igual que el dominio.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

# Mismo patrón que ``app.models.libro.PORTADA_PATRON``.
PORTADA_VALIDA = "portada_url IS NULL OR portada_url ~ '^(https?://|/portadas/)[^[:space:]]+$'"


def upgrade() -> None:
    op.add_column("libro", sa.Column("portada_url", sa.String(length=300), nullable=True))
    op.create_check_constraint(op.f("ck_libro_portada_url_valida"), "libro", PORTADA_VALIDA)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_libro_portada_url_valida"), "libro", type_="check")
    op.drop_column("libro", "portada_url")
