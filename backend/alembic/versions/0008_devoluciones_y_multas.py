"""Devoluciones y multas

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _auditoria() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "devolucion",
        sa.Column("prestamo_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado_fisico_recibido", sa.String(length=15), nullable=False),
        sa.Column("dias_atraso", sa.Integer(), nullable=False),
        sa.Column("observaciones", sa.String(length=300), nullable=True),
        sa.Column("registrada_por_id", sa.BigInteger(), nullable=True),
        *_auditoria(),
        sa.CheckConstraint(
            "estado_fisico_recibido IN ('BUENO','REGULAR','DANADO','EXTRAVIADO')",
            name=op.f("ck_devolucion_estado_valido"),
        ),
        sa.CheckConstraint("dias_atraso >= 0", name=op.f("ck_devolucion_atraso_no_negativo")),
        sa.ForeignKeyConstraint(
            ["prestamo_id"], ["prestamo.id"], name=op.f("fk_devolucion_prestamo_id_prestamo")
        ),
        sa.ForeignKeyConstraint(["sede_id"], ["sede.id"], name=op.f("fk_devolucion_sede_id_sede")),
        sa.ForeignKeyConstraint(
            ["registrada_por_id"],
            ["usuario.id"],
            name=op.f("fk_devolucion_registrada_por_id_usuario"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devolucion")),
        sa.UniqueConstraint("prestamo_id", name=op.f("uq_devolucion_prestamo_id")),
    )
    op.create_table(
        "multa",
        sa.Column("prestamo_id", sa.BigInteger(), nullable=False),
        sa.Column("socio_id", sa.BigInteger(), nullable=False),
        sa.Column("dias_atraso", sa.Integer(), nullable=False),
        sa.Column("monto_por_dia", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("monto_total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("fecha_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_saldada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saldada_por_id", sa.BigInteger(), nullable=True),
        *_auditoria(),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE','SALDADA')", name=op.f("ck_multa_estado_valido")
        ),
        sa.CheckConstraint("monto_total >= 0", name=op.f("ck_multa_monto_no_negativo")),
        sa.CheckConstraint(
            "(estado = 'SALDADA') = (fecha_saldada IS NOT NULL)",
            name=op.f("ck_multa_saldada_con_fecha"),
        ),
        sa.ForeignKeyConstraint(
            ["prestamo_id"], ["prestamo.id"], name=op.f("fk_multa_prestamo_id_prestamo")
        ),
        sa.ForeignKeyConstraint(["socio_id"], ["socio.id"], name=op.f("fk_multa_socio_id_socio")),
        sa.ForeignKeyConstraint(
            ["saldada_por_id"], ["usuario.id"], name=op.f("fk_multa_saldada_por_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_multa")),
        sa.UniqueConstraint("prestamo_id", name=op.f("uq_multa_prestamo_id")),
    )
    op.create_index("ix_multa_socio_id_estado", "multa", ["socio_id", "estado"])


def downgrade() -> None:
    op.drop_table("multa")
    op.drop_table("devolucion")
