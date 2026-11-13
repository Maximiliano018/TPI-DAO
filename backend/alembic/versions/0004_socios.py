"""Socios: estados, causas de inhabilitación, baja lógica, auditoría y numeración

Completa la tabla ``socio`` creada en ``0002`` (solo estructura) para el módulo de socios.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "socio",
        sa.Column(
            "inhabilitacion_administrativa",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("socio", sa.Column("motivo_administrativo", sa.String(length=300)))
    op.add_column("socio", sa.Column("motivo_baja", sa.String(length=300)))
    op.add_column("socio", sa.Column("creado_por_id", sa.BigInteger()))
    op.add_column("socio", sa.Column("actualizado_por_id", sa.BigInteger()))
    op.create_foreign_key(
        op.f("fk_socio_creado_por_id_usuario"), "socio", "usuario", ["creado_por_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_socio_actualizado_por_id_usuario"),
        "socio",
        "usuario",
        ["actualizado_por_id"],
        ["id"],
    )

    op.drop_constraint(op.f("ck_socio_estado_valido"), "socio", type_="check")
    op.create_check_constraint(
        op.f("ck_socio_estado_valido"), "socio", "estado IN ('HABILITADO','INHABILITADO','BAJA')"
    )
    # Filas cargadas con el formato anterior: la baja era solo ``fecha_baja`` y el motivo de
    # inhabilitación no tenía reglas. Se llevan al formato nuevo antes de las restricciones.
    sin_motivo = "'Sin motivo registrado'"
    op.execute(
        f"UPDATE socio SET estado = 'BAJA', motivo_baja = {sin_motivo} WHERE fecha_baja IS NOT NULL"
    )
    op.execute(
        "UPDATE socio SET motivo_inhabilitacion = 'ADMINISTRATIVA' "
        "WHERE estado = 'INHABILITADO' AND motivo_inhabilitacion IS NULL"
    )
    op.execute(
        "UPDATE socio SET motivo_inhabilitacion = NULL "
        "WHERE estado <> 'INHABILITADO' AND motivo_inhabilitacion IS NOT NULL"
    )
    op.execute(
        "UPDATE socio SET inhabilitacion_administrativa = true, "
        f"motivo_administrativo = {sin_motivo} WHERE motivo_inhabilitacion = 'ADMINISTRATIVA'"
    )
    op.create_check_constraint(
        op.f("ck_socio_tipo_documento_valido"),
        "socio",
        "tipo_documento IN ('DNI','LE','LC','PASAPORTE')",
    )
    op.create_check_constraint(
        op.f("ck_socio_motivo_valido"),
        "socio",
        "motivo_inhabilitacion IS NULL OR motivo_inhabilitacion IN "
        "('ADMINISTRATIVA','PRESTAMO_VENCIDO','MULTA_IMPAGA')",
    )
    op.create_check_constraint(
        op.f("ck_socio_inhabilitado_con_motivo"),
        "socio",
        "(estado = 'INHABILITADO') = (motivo_inhabilitacion IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_socio_administrativa_con_motivo"),
        "socio",
        "inhabilitacion_administrativa = (motivo_administrativo IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_socio_administrativa_prioritaria"),
        "socio",
        "NOT inhabilitacion_administrativa OR motivo_inhabilitacion = 'ADMINISTRATIVA'",
    )
    op.create_check_constraint(
        op.f("ck_socio_baja_con_datos"),
        "socio",
        "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL)"
        " OR (estado <> 'BAJA' AND fecha_baja IS NULL AND motivo_baja IS NULL)",
    )
    op.create_index("ix_socio_apellido_nombre", "socio", ["apellido", "nombre"])

    # El número de socio sale de una secuencia; arranca después del mayor número existente.
    op.execute("CREATE SEQUENCE socio_numero_seq")
    op.execute(
        "SELECT setval('socio_numero_seq', "
        "COALESCE((SELECT MAX(numero_socio::bigint) FROM socio WHERE numero_socio ~ '^[0-9]+$'), 0)"
        " + 1, false)"
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE socio_numero_seq")
    op.drop_index("ix_socio_apellido_nombre", table_name="socio")
    for nombre in (
        "ck_socio_baja_con_datos",
        "ck_socio_administrativa_prioritaria",
        "ck_socio_administrativa_con_motivo",
        "ck_socio_inhabilitado_con_motivo",
        "ck_socio_motivo_valido",
        "ck_socio_tipo_documento_valido",
        "ck_socio_estado_valido",
    ):
        op.drop_constraint(op.f(nombre), "socio", type_="check")
    # En 0003 la baja era solo ``fecha_baja``: los socios en baja vuelven a ese formato.
    op.execute("UPDATE socio SET estado = 'HABILITADO' WHERE estado = 'BAJA'")
    op.create_check_constraint(
        op.f("ck_socio_estado_valido"), "socio", "estado IN ('HABILITADO','INHABILITADO')"
    )
    op.drop_constraint(op.f("fk_socio_actualizado_por_id_usuario"), "socio", type_="foreignkey")
    op.drop_constraint(op.f("fk_socio_creado_por_id_usuario"), "socio", type_="foreignkey")
    for columna in (
        "actualizado_por_id",
        "creado_por_id",
        "motivo_baja",
        "motivo_administrativo",
        "inhabilitacion_administrativa",
    ):
        op.drop_column("socio", columna)
