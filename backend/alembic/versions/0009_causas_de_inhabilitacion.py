"""Socios: guardar todas las causas automáticas de inhabilitación

Hasta ``0008`` solo se guardaba la causa de mayor prioridad (``motivo_inhabilitacion``) y el
indicador administrativo: un socio con un préstamo vencido **y** una multa impaga volvía de la
base solo con la primera. Se agrega una columna por causa automática y se completa con los
préstamos vencidos y las multas pendientes reales de cada socio inhabilitado.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for columna in ("causa_prestamo_vencido", "causa_multa_impaga"):
        op.add_column(
            "socio",
            sa.Column(columna, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    op.execute(
        """
        UPDATE socio s SET
            causa_prestamo_vencido = s.motivo_inhabilitacion = 'PRESTAMO_VENCIDO' OR EXISTS (
                SELECT 1 FROM prestamo p WHERE p.socio_id = s.id AND p.estado = 'VENCIDO'
            ),
            causa_multa_impaga = s.motivo_inhabilitacion = 'MULTA_IMPAGA' OR EXISTS (
                SELECT 1 FROM multa m WHERE m.socio_id = s.id AND m.estado = 'PENDIENTE'
            )
        WHERE s.estado = 'INHABILITADO'
        """
    )
    # El motivo que se muestra es la causa de mayor prioridad entre las vigentes.
    op.execute(
        """
        UPDATE socio SET motivo_inhabilitacion = CASE
            WHEN inhabilitacion_administrativa THEN 'ADMINISTRATIVA'
            WHEN causa_prestamo_vencido THEN 'PRESTAMO_VENCIDO'
            ELSE 'MULTA_IMPAGA'
        END
        WHERE estado = 'INHABILITADO'
        """
    )
    op.create_check_constraint(
        op.f("ck_socio_causas_coherentes"),
        "socio",
        "(estado = 'INHABILITADO') = "
        "(inhabilitacion_administrativa OR causa_prestamo_vencido OR causa_multa_impaga)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_socio_causas_coherentes"), "socio", type_="check")
    op.drop_column("socio", "causa_multa_impaga")
    op.drop_column("socio", "causa_prestamo_vencido")
