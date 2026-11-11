"""Catálogos geográficos: btree_gist, provincia y localidad

Revision ID: 0001
Revises: 0000
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = "0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "provincia",
        sa.Column("nombre", sa.String(length=60), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provincia")),
        sa.UniqueConstraint("nombre", name=op.f("uq_provincia_nombre")),
    )
    op.create_table(
        "localidad",
        sa.Column("provincia_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("departamento", sa.String(length=60), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["provincia_id"], ["provincia.id"], name=op.f("fk_localidad_provincia_id_provincia")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_localidad")),
        sa.UniqueConstraint(
            "provincia_id",
            "nombre",
            "departamento",
            name=op.f("uq_localidad_provincia_id_nombre_departamento"),
        ),
    )


def downgrade() -> None:
    op.drop_table("localidad")
    op.drop_table("provincia")
