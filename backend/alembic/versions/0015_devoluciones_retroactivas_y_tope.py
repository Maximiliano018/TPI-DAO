"""Devoluciones: fecha retroactiva con motivo, tope de multa y coherencia de la multa

- ``devolucion.registrada_en``: cuándo se cargó (las existentes toman ``creado_en``).
- ``devolucion.motivo_fecha``: por qué la devolución tiene una fecha anterior a la de registro.
  Las existentes cargadas más de un día después de su fecha quedan con un motivo que lo aclara.
- ``devolucion.registrada_por_id`` pasa a ``NOT NULL`` (siempre la registra un bibliotecario).
- ``CHECK`` ``ck_devolucion_retroactiva_con_motivo``, ``ck_multa_atraso_positivo`` y
  ``ck_multa_monto_coherente`` (el total no supera días × monto por día).
- Parámetro ``multa_tope_por_prestamo`` (0 = sin tope).

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

MOTIVO_HISTORICO = "Registrada antes de que se exigiera el motivo de la fecha"


def upgrade() -> None:
    op.add_column(
        "devolucion", sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("devolucion", sa.Column("motivo_fecha", sa.String(length=300), nullable=True))
    op.execute("UPDATE devolucion SET registrada_en = creado_en")
    op.execute(
        sa.text(
            "UPDATE devolucion SET motivo_fecha = :motivo "
            "WHERE fecha_hora < registrada_en - interval '1 day'"
        ).bindparams(motivo=MOTIVO_HISTORICO)
    )
    op.alter_column("devolucion", "registrada_en", nullable=False)
    op.alter_column(
        "devolucion", "registrada_por_id", existing_type=sa.BigInteger(), nullable=False
    )
    op.create_check_constraint(
        op.f("ck_devolucion_retroactiva_con_motivo"),
        "devolucion",
        "motivo_fecha IS NOT NULL OR fecha_hora >= registrada_en - interval '1 day'",
    )
    op.create_check_constraint(op.f("ck_multa_atraso_positivo"), "multa", "dias_atraso > 0")
    op.create_check_constraint(
        op.f("ck_multa_monto_coherente"),
        "multa",
        "monto_por_dia >= 0 AND monto_total <= dias_atraso * monto_por_dia",
    )
    op.execute(
        "INSERT INTO parametro (clave, valor, descripcion) VALUES ('multa_tope_por_prestamo', "
        "'0.00', 'Tope de la multa de un préstamo en pesos (0 = sin tope)')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro WHERE clave = 'multa_tope_por_prestamo'")
    op.drop_constraint(op.f("ck_multa_monto_coherente"), "multa", type_="check")
    op.drop_constraint(op.f("ck_multa_atraso_positivo"), "multa", type_="check")
    op.drop_constraint(op.f("ck_devolucion_retroactiva_con_motivo"), "devolucion", type_="check")
    op.alter_column(
        "devolucion", "registrada_por_id", existing_type=sa.BigInteger(), nullable=True
    )
    op.drop_column("devolucion", "motivo_fecha")
    op.drop_column("devolucion", "registrada_en")
