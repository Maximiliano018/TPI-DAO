"""Préstamos: plazo de retiro y coherencia de fechas

- ``prestamo.fecha_limite_retiro``: último día para retirar el préstamo en la sede destino. Un
  préstamo local lo recibe al registrarse; uno interbibliotecario, al llegar a la sede destino.
  Vencido, la tarea diaria lo cancela y libera el ejemplar (o lo devuelve a su sede).
- Parámetro ``vigencia_retiro_prestamo_dias`` (3 días).
- ``CHECK``: un préstamo activo, vencido o devuelto tiene fecha de inicio y de vencimiento, y
  solo uno devuelto tiene fecha de devolución.

Los préstamos pendientes de retiro que ya existían reciben 3 días desde hoy, para que la tarea
no los cancele apenas se aplica la migración.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prestamo", sa.Column("fecha_limite_retiro", sa.Date(), nullable=True))
    op.execute(
        "INSERT INTO parametro (clave, valor, descripcion) VALUES ('vigencia_retiro_prestamo_dias',"
        " '3', 'Días para retirar un préstamo en la sede destino')"
    )
    # Locales sin entregar y entre sedes que ya llegaron a destino y esperan el retiro.
    op.execute(
        """
        UPDATE prestamo p SET fecha_limite_retiro = current_date + 3
        FROM ejemplar e
        WHERE e.id = p.ejemplar_id
          AND ((p.estado = 'SOLICITADO' AND p.tipo = 'LOCAL')
               OR (p.estado = 'EN_ENVIO' AND e.estado = 'APARTADO'
                   AND e.sede_actual_id = p.sede_destino_id))
        """
    )
    op.create_check_constraint(
        op.f("ck_prestamo_fechas_segun_estado"),
        "prestamo",
        "(estado IN ('ACTIVO','VENCIDO','DEVUELTO')) "
        "= (fecha_inicio IS NOT NULL AND fecha_vencimiento IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_prestamo_devolucion_con_fecha"),
        "prestamo",
        "(estado = 'DEVUELTO') = (fecha_devolucion IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_prestamo_devolucion_con_fecha"), "prestamo", type_="check")
    op.drop_constraint(op.f("ck_prestamo_fechas_segun_estado"), "prestamo", type_="check")
    op.execute("DELETE FROM parametro WHERE clave = 'vigencia_retiro_prestamo_dias'")
    op.drop_column("prestamo", "fecha_limite_retiro")
