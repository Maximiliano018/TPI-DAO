"""Pagos de multas: en el mostrador (con medio de pago) o en línea (simulado)

- Tabla ``pago``: medio, estado, monto, comprobante, motivo (de un rechazo o una cancelación),
  quién lo registró y cuándo se acreditó; del pago en línea, la forma elegida y, con tarjeta,
  solo sus últimos 4 dígitos.
- Índices únicos parciales: a lo sumo un pago ``APROBADO`` y uno ``PENDIENTE`` por multa.
- Las multas ya saldadas reciben su pago aprobado con medio ``NO_REGISTRADO`` (no se sabía).

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

MEDIOS = "'EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA','EN_LINEA','NO_REGISTRADO'"
ESTADOS = "'PENDIENTE','APROBADO','RECHAZADO','CANCELADO'"


def upgrade() -> None:
    op.create_table(
        "pago",
        sa.Column("multa_id", sa.BigInteger(), nullable=False),
        sa.Column("medio", sa.String(length=15), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("comprobante", sa.String(length=100), nullable=True),
        sa.Column("motivo", sa.String(length=120), nullable=True),
        sa.Column("forma_en_linea", sa.String(length=20), nullable=True),
        sa.Column("tarjeta_ultimos4", sa.String(length=4), nullable=True),
        sa.Column("registrado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acreditado_en", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(f"medio IN ({MEDIOS})", name=op.f("ck_pago_medio_valido")),
        sa.CheckConstraint(f"estado IN ({ESTADOS})", name=op.f("ck_pago_estado_valido")),
        sa.CheckConstraint("monto > 0", name=op.f("ck_pago_monto_positivo")),
        sa.CheckConstraint(
            "medio = 'EN_LINEA' OR (estado = 'APROBADO' "
            "AND (registrado_por_id IS NOT NULL OR medio = 'NO_REGISTRADO'))",
            name=op.f("ck_pago_mostrador_aprobado"),
        ),
        sa.CheckConstraint(
            "(estado = 'APROBADO') = (acreditado_en IS NOT NULL)",
            name=op.f("ck_pago_acreditado_segun_estado"),
        ),
        sa.CheckConstraint(
            "forma_en_linea IS NULL OR (medio = 'EN_LINEA' AND forma_en_linea IN "
            "('TARJETA_CREDITO','TARJETA_DEBITO','DINERO_EN_CUENTA'))",
            name=op.f("ck_pago_forma_en_linea_valida"),
        ),
        sa.CheckConstraint(
            "(tarjeta_ultimos4 IS NOT NULL) = "
            "(forma_en_linea IN ('TARJETA_CREDITO','TARJETA_DEBITO')) "
            "AND (tarjeta_ultimos4 IS NULL OR tarjeta_ultimos4 ~ '^[0-9]{4}$')",
            name=op.f("ck_pago_tarjeta_segun_forma"),
        ),
        sa.ForeignKeyConstraint(["multa_id"], ["multa.id"], name=op.f("fk_pago_multa_id_multa")),
        sa.ForeignKeyConstraint(
            ["registrado_por_id"], ["usuario.id"], name=op.f("fk_pago_registrado_por_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pago")),
    )
    op.create_index(
        "uq_pago_aprobado_por_multa",
        "pago",
        ["multa_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'APROBADO'"),
    )
    op.create_index(
        "uq_pago_pendiente_por_multa",
        "pago",
        ["multa_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'PENDIENTE'"),
    )
    op.execute(
        """
        INSERT INTO pago (multa_id, medio, estado, monto, registrado_por_id, fecha, acreditado_en)
        SELECT id, 'NO_REGISTRADO', 'APROBADO', monto_total, saldada_por_id, fecha_saldada,
               fecha_saldada
        FROM multa
        WHERE estado = 'SALDADA' AND monto_total > 0
        """
    )


def downgrade() -> None:
    op.drop_index("uq_pago_pendiente_por_multa", table_name="pago")
    op.drop_index("uq_pago_aprobado_por_multa", table_name="pago")
    op.drop_table("pago")
