"""Socios: tipos de baja, solicitud de reactivación e historial

- ``tipo_baja`` (a pedido, administrativa o fallecimiento) decide quién puede reactivar.
- ``reactivacion_solicitada_en`` y ``mensaje_solicitud``: pedido del socio desde su cuenta.
- La inhabilitación administrativa sobrevive a la baja: un socio en ``BAJA`` puede conservarla
  (no así las causas automáticas, porque la baja exige no tener préstamos ni multas).
- ``historial_socio``: eventos de solo inserción (un disparador impide UPDATE y DELETE).

Las bajas existentes no tenían tipo: se registran como ``A_PEDIDO``.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_CAUSAS = "(inhabilitacion_administrativa OR causa_prestamo_vencido OR causa_multa_impaga)"
_TIPOS_EVENTO = (
    "'ALTA','MODIFICACION','INHABILITACION','REHABILITACION','CAMBIO_AUTOMATICO','BAJA',"
    "'SOLICITUD_REACTIVACION','SOLICITUD_RECHAZADA','REACTIVACION','CUENTA_CREADA'"
)


def upgrade() -> None:
    op.add_column("socio", sa.Column("tipo_baja", sa.String(length=15)))
    op.add_column("socio", sa.Column("reactivacion_solicitada_en", sa.DateTime(timezone=True)))
    op.add_column("socio", sa.Column("mensaje_solicitud", sa.String(length=300)))
    op.execute("UPDATE socio SET tipo_baja = 'A_PEDIDO' WHERE estado = 'BAJA'")

    for nombre in (
        "ck_socio_inhabilitado_con_motivo",
        "ck_socio_causas_coherentes",
        "ck_socio_baja_con_datos",
    ):
        op.drop_constraint(op.f(nombre), "socio", type_="check")
    op.create_check_constraint(
        op.f("ck_socio_motivo_con_causas"),
        "socio",
        f"(motivo_inhabilitacion IS NOT NULL) = {_CAUSAS}",
    )
    op.create_check_constraint(
        op.f("ck_socio_causas_coherentes"),
        "socio",
        f"CASE estado WHEN 'HABILITADO' THEN NOT {_CAUSAS} "
        f"WHEN 'INHABILITADO' THEN {_CAUSAS} "
        "ELSE NOT (causa_prestamo_vencido OR causa_multa_impaga) END",
    )
    op.create_check_constraint(
        op.f("ck_socio_baja_con_datos"),
        "socio",
        "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL "
        "AND tipo_baja IS NOT NULL) OR (estado <> 'BAJA' AND fecha_baja IS NULL "
        "AND motivo_baja IS NULL AND tipo_baja IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_socio_tipo_baja_valido"),
        "socio",
        "tipo_baja IS NULL OR tipo_baja IN ('FALLECIMIENTO','ADMINISTRATIVA','A_PEDIDO')",
    )
    op.create_check_constraint(
        op.f("ck_socio_solicitud_coherente"),
        "socio",
        "(reactivacion_solicitada_en IS NULL "
        "OR (estado = 'BAJA' AND tipo_baja <> 'FALLECIMIENTO')) "
        "AND (mensaje_solicitud IS NULL OR reactivacion_solicitada_en IS NOT NULL)",
    )

    op.create_table(
        "historial_socio",
        sa.Column("socio_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=25), nullable=False),
        sa.Column(
            "fecha_hora", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("estado_anterior", sa.String(length=15), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=15), nullable=True),
        sa.Column("motivo", sa.String(length=300), nullable=True),
        sa.Column("origen", sa.String(length=200), nullable=True),
        sa.Column("cambios", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            f"tipo_evento IN ({_TIPOS_EVENTO})", name=op.f("ck_historial_socio_tipo_evento_valido")
        ),
        sa.ForeignKeyConstraint(
            ["socio_id"], ["socio.id"], name=op.f("fk_historial_socio_socio_id_socio")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_historial_socio_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historial_socio")),
    )
    op.create_index(
        "ix_historial_socio_socio_id_fecha_hora",
        "historial_socio",
        ["socio_id", sa.literal_column("fecha_hora DESC")],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION historial_socio_solo_insercion() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'historial_socio es de solo inserción';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_historial_socio_solo_insercion
        BEFORE UPDATE OR DELETE ON historial_socio
        FOR EACH ROW EXECUTE FUNCTION historial_socio_solo_insercion()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_historial_socio_solo_insercion ON historial_socio")
    op.execute("DROP FUNCTION IF EXISTS historial_socio_solo_insercion()")
    op.drop_index("ix_historial_socio_socio_id_fecha_hora", table_name="historial_socio")
    op.drop_table("historial_socio")

    # En 0009 un socio en baja no conservaba la inhabilitación administrativa.
    op.execute(
        "UPDATE socio SET inhabilitacion_administrativa = false, motivo_administrativo = NULL, "
        "motivo_inhabilitacion = NULL WHERE estado = 'BAJA'"
    )
    for nombre in (
        "ck_socio_solicitud_coherente",
        "ck_socio_tipo_baja_valido",
        "ck_socio_baja_con_datos",
        "ck_socio_causas_coherentes",
        "ck_socio_motivo_con_causas",
    ):
        op.drop_constraint(op.f(nombre), "socio", type_="check")
    op.create_check_constraint(
        op.f("ck_socio_inhabilitado_con_motivo"),
        "socio",
        "(estado = 'INHABILITADO') = (motivo_inhabilitacion IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_socio_causas_coherentes"), "socio", f"(estado = 'INHABILITADO') = {_CAUSAS}"
    )
    op.create_check_constraint(
        op.f("ck_socio_baja_con_datos"),
        "socio",
        "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL)"
        " OR (estado <> 'BAJA' AND fecha_baja IS NULL AND motivo_baja IS NULL)",
    )
    op.drop_column("socio", "mensaje_solicitud")
    op.drop_column("socio", "reactivacion_solicitada_en")
    op.drop_column("socio", "tipo_baja")
