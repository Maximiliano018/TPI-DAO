"""Multas por daño y por extravío del ejemplar

- ``multa.tipo``: ``ATRASO``, ``DANIO`` o ``EXTRAVIO`` (las existentes son de atraso).
- ``dias_atraso`` y ``monto_por_dia`` pasan a ser opcionales: solo los tiene la de atraso
  (``ck_multa_atraso_segun_tipo``).
- Un préstamo tiene a lo sumo una multa de cada tipo: ``uq_multa_prestamo_id`` pasa a
  ``uq_multa_prestamo_id_tipo``.
- Parámetros ``multa_por_danio`` y ``multa_por_extravio`` (0 = no se cobra).

El downgrade borra las multas por daño o extravío (y sus pagos): el esquema anterior no las
puede guardar.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

PARAMETROS = (
    ("multa_por_danio", "Multa por devolver el ejemplar dañado, en pesos (0 = no se cobra)"),
    ("multa_por_extravio", "Multa por el extravío del ejemplar, en pesos (0 = no se cobra)"),
)


def upgrade() -> None:
    op.add_column(
        "multa",
        sa.Column("tipo", sa.String(length=10), nullable=False, server_default="ATRASO"),
    )
    op.alter_column("multa", "tipo", server_default=None)
    op.alter_column("multa", "dias_atraso", existing_type=sa.Integer(), nullable=True)
    op.alter_column("multa", "monto_por_dia", existing_type=sa.Numeric(10, 2), nullable=True)
    op.drop_constraint(op.f("uq_multa_prestamo_id"), "multa", type_="unique")
    op.create_unique_constraint(op.f("uq_multa_prestamo_id_tipo"), "multa", ["prestamo_id", "tipo"])
    op.drop_constraint(op.f("ck_multa_atraso_positivo"), "multa", type_="check")
    op.drop_constraint(op.f("ck_multa_monto_coherente"), "multa", type_="check")
    op.create_check_constraint(
        op.f("ck_multa_tipo_valido"), "multa", "tipo IN ('ATRASO','DANIO','EXTRAVIO')"
    )
    op.create_check_constraint(
        op.f("ck_multa_atraso_segun_tipo"),
        "multa",
        "(tipo = 'ATRASO') = (dias_atraso IS NOT NULL AND monto_por_dia IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_multa_atraso_positivo"), "multa", "dias_atraso IS NULL OR dias_atraso > 0"
    )
    op.create_check_constraint(
        op.f("ck_multa_monto_coherente"),
        "multa",
        "dias_atraso IS NULL "
        "OR (monto_por_dia >= 0 AND monto_total <= dias_atraso * monto_por_dia)",
    )
    for clave, descripcion in PARAMETROS:
        op.execute(
            sa.text(
                "INSERT INTO parametro (clave, valor, descripcion) VALUES (:c, '0.00', :d)"
            ).bindparams(c=clave, d=descripcion)
        )


def downgrade() -> None:
    op.execute("DELETE FROM parametro WHERE clave IN ('multa_por_danio', 'multa_por_extravio')")
    op.execute(
        "DELETE FROM pago WHERE multa_id IN (SELECT id FROM multa WHERE tipo <> 'ATRASO')"
    )
    op.execute("DELETE FROM multa WHERE tipo <> 'ATRASO'")
    op.drop_constraint(op.f("ck_multa_monto_coherente"), "multa", type_="check")
    op.drop_constraint(op.f("ck_multa_atraso_positivo"), "multa", type_="check")
    op.drop_constraint(op.f("ck_multa_atraso_segun_tipo"), "multa", type_="check")
    op.drop_constraint(op.f("ck_multa_tipo_valido"), "multa", type_="check")
    op.create_check_constraint(op.f("ck_multa_atraso_positivo"), "multa", "dias_atraso > 0")
    op.create_check_constraint(
        op.f("ck_multa_monto_coherente"),
        "multa",
        "monto_por_dia >= 0 AND monto_total <= dias_atraso * monto_por_dia",
    )
    op.drop_constraint(op.f("uq_multa_prestamo_id_tipo"), "multa", type_="unique")
    op.create_unique_constraint(op.f("uq_multa_prestamo_id"), "multa", ["prestamo_id"])
    op.alter_column("multa", "monto_por_dia", existing_type=sa.Numeric(10, 2), nullable=False)
    op.alter_column("multa", "dias_atraso", existing_type=sa.Integer(), nullable=False)
    op.drop_column("multa", "tipo")
