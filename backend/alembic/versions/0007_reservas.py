"""Reservas: cola de espera por libro

También permite préstamos sin usuario registrante: los genera el sistema al asignar una reserva
con el ejemplar en otra sede.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("prestamo", "registrado_por_id", existing_type=sa.BigInteger(), nullable=True)
    op.create_table(
        "reserva",
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("socio_id", sa.BigInteger(), nullable=False),
        sa.Column("libro_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_retiro_id", sa.BigInteger(), nullable=False),
        sa.Column("ejemplar_id", sa.BigInteger(), nullable=True),
        sa.Column("prestamo_id", sa.BigInteger(), nullable=True),
        sa.Column("estado", sa.String(length=25), nullable=False),
        sa.Column("fecha_reserva", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vencimiento_retiro", sa.Date(), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrada_por_id", sa.BigInteger(), nullable=True),
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
        sa.CheckConstraint(
            "estado IN ('PENDIENTE','DISPONIBLE_PARA_RETIRO','CUMPLIDA','CANCELADA','VENCIDA')",
            name=op.f("ck_reserva_estado_valido"),
        ),
        sa.CheckConstraint(
            "estado <> 'DISPONIBLE_PARA_RETIRO' OR "
            "(ejemplar_id IS NOT NULL AND vencimiento_retiro IS NOT NULL)",
            name=op.f("ck_reserva_disponible_con_ejemplar"),
        ),
        sa.ForeignKeyConstraint(["socio_id"], ["socio.id"], name=op.f("fk_reserva_socio_id_socio")),
        sa.ForeignKeyConstraint(["libro_id"], ["libro.id"], name=op.f("fk_reserva_libro_id_libro")),
        sa.ForeignKeyConstraint(
            ["sede_retiro_id"], ["sede.id"], name=op.f("fk_reserva_sede_retiro_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["ejemplar_id"], ["ejemplar.id"], name=op.f("fk_reserva_ejemplar_id_ejemplar")
        ),
        sa.ForeignKeyConstraint(
            ["prestamo_id"], ["prestamo.id"], name=op.f("fk_reserva_prestamo_id_prestamo")
        ),
        sa.ForeignKeyConstraint(
            ["registrada_por_id"], ["usuario.id"], name=op.f("fk_reserva_registrada_por_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reserva")),
        sa.UniqueConstraint("numero", name=op.f("uq_reserva_numero")),
    )
    op.create_index(
        "uq_reserva_activa",
        "reserva",
        ["socio_id", "libro_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('PENDIENTE','DISPONIBLE_PARA_RETIRO')"),
    )
    op.create_index(
        "ix_reserva_libro_id_estado_fecha_reserva",
        "reserva",
        ["libro_id", "estado", "fecha_reserva"],
    )
    op.execute("CREATE SEQUENCE reserva_numero_seq")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS reserva_numero_seq")
    op.drop_table("reserva")
    op.execute("DELETE FROM prestamo WHERE registrado_por_id IS NULL")
    op.alter_column("prestamo", "registrado_por_id", existing_type=sa.BigInteger(), nullable=False)
