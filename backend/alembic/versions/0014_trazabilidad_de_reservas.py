"""Reservas: historial de estados y datos coherentes con el estado

- ``movimiento_reserva``: historial de solo inserción de cada reserva (estado anterior y nuevo,
  fecha, autor y observación), como el de préstamos y remitos. Las reservas existentes reciben
  su alta en ``fecha_reserva`` y, si ya no están pendientes, un movimiento con su estado actual.
- ``CHECK`` ``ck_reserva_datos_segun_estado`` (reemplaza a ``ck_reserva_disponible_con_ejemplar``):
  una pendiente no tiene ejemplar ni cierre, una disponible tiene ejemplar y vencimiento, una
  cumplida tiene préstamo, y toda reserva cerrada tiene fecha de cierre.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

DATOS_SEGUN_ESTADO = (
    "(estado = 'PENDIENTE' AND ejemplar_id IS NULL AND vencimiento_retiro IS NULL "
    "AND prestamo_id IS NULL AND fecha_cierre IS NULL) "
    "OR (estado = 'DISPONIBLE_PARA_RETIRO' AND ejemplar_id IS NOT NULL "
    "AND vencimiento_retiro IS NOT NULL AND prestamo_id IS NULL AND fecha_cierre IS NULL) "
    "OR (estado = 'CUMPLIDA' AND ejemplar_id IS NOT NULL AND prestamo_id IS NOT NULL "
    "AND fecha_cierre IS NOT NULL) "
    "OR (estado = 'VENCIDA' AND ejemplar_id IS NOT NULL AND vencimiento_retiro IS NOT NULL "
    "AND prestamo_id IS NULL AND fecha_cierre IS NOT NULL) "
    "OR (estado = 'CANCELADA' AND prestamo_id IS NULL AND fecha_cierre IS NOT NULL)"
)
DISPONIBLE_CON_EJEMPLAR = (
    "estado <> 'DISPONIBLE_PARA_RETIRO' OR "
    "(ejemplar_id IS NOT NULL AND vencimiento_retiro IS NOT NULL)"
)


def upgrade() -> None:
    op.create_table(
        "movimiento_reserva",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reserva_id", sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=25), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=25), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["reserva.id"], name=op.f("fk_movimiento_reserva_reserva_id_reserva")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_movimiento_reserva_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimiento_reserva")),
    )
    op.create_index(
        "ix_movimiento_reserva_reserva_id_fecha_hora",
        "movimiento_reserva",
        ["reserva_id", "fecha_hora"],
    )
    # Historial de las reservas existentes: el alta y, si avanzó, el estado actual (no se
    # conoce el camino intermedio ni quién lo hizo).
    op.execute(
        """
        INSERT INTO movimiento_reserva
            (reserva_id, estado_anterior, estado_nuevo, fecha_hora, usuario_id, observacion)
        SELECT id, NULL, 'PENDIENTE', fecha_reserva, registrada_por_id, 'Reserva registrada'
        FROM reserva
        """
    )
    op.execute(
        """
        INSERT INTO movimiento_reserva
            (reserva_id, estado_anterior, estado_nuevo, fecha_hora, usuario_id, observacion)
        SELECT id, 'PENDIENTE', estado, COALESCE(fecha_cierre, actualizado_en), NULL,
               'Estado registrado al incorporar el historial'
        FROM reserva
        WHERE estado <> 'PENDIENTE'
        """
    )
    op.execute(
        "CREATE TRIGGER trg_movimiento_reserva_solo_insercion "
        "BEFORE UPDATE OR DELETE ON movimiento_reserva "
        "FOR EACH ROW EXECUTE FUNCTION historial_solo_insercion()"
    )
    op.drop_constraint(op.f("ck_reserva_disponible_con_ejemplar"), "reserva", type_="check")
    op.create_check_constraint(op.f("ck_reserva_datos_segun_estado"), "reserva", DATOS_SEGUN_ESTADO)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_reserva_datos_segun_estado"), "reserva", type_="check")
    op.create_check_constraint(
        op.f("ck_reserva_disponible_con_ejemplar"), "reserva", DISPONIBLE_CON_EJEMPLAR
    )
    op.execute("DROP TRIGGER IF EXISTS trg_movimiento_reserva_solo_insercion ON movimiento_reserva")
    op.drop_index("ix_movimiento_reserva_reserva_id_fecha_hora", table_name="movimiento_reserva")
    op.drop_table("movimiento_reserva")
