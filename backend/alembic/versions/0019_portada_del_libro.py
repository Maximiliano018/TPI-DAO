"""Portada del libro

- Columna ``libro.portada_url``: enlace a la imagen de tapa (opcional). Puede ser una dirección web
  o una de las portadas que sirve el frontend (``/portadas/...``).

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("libro", sa.Column("portada_url", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("libro", "portada_url")
