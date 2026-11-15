"""Auditoría de los parámetros de negocio

- Tabla ``historial_parametro`` (solo inserción, con el disparador ``historial_solo_insercion``):
  cada cambio de un parámetro con su valor anterior, el nuevo, quién lo hizo y cuándo.
- Los parámetros existentes no reciben historial: sus valores vienen de las migraciones.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historial_parametro",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("clave", sa.String(length=40), nullable=False),
        sa.Column("valor_anterior", sa.String(length=40), nullable=False),
        sa.Column("valor_nuevo", sa.String(length=40), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "valor_anterior <> valor_nuevo", name=op.f("ck_historial_parametro_valor_distinto")
        ),
        sa.ForeignKeyConstraint(
            ["clave"], ["parametro.clave"], name=op.f("fk_historial_parametro_clave_parametro")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_historial_parametro_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historial_parametro")),
    )
    op.create_index(
        "ix_historial_parametro_clave_fecha_hora", "historial_parametro", ["clave", "fecha_hora"]
    )
    op.create_index("ix_historial_parametro_fecha_hora", "historial_parametro", ["fecha_hora"])
    op.execute(
        "CREATE TRIGGER trg_historial_parametro_solo_insercion "
        "BEFORE UPDATE OR DELETE ON historial_parametro "
        "FOR EACH ROW EXECUTE FUNCTION historial_solo_insercion()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_historial_parametro_solo_insercion ON historial_parametro")
    op.drop_index("ix_historial_parametro_fecha_hora", table_name="historial_parametro")
    op.drop_index("ix_historial_parametro_clave_fecha_hora", table_name="historial_parametro")
    op.drop_table("historial_parametro")
