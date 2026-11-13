"""Préstamos y remitos: parámetros, préstamos, remitos con su detalle, historiales e incidencias

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

PARAMETROS = [
    ("plazo_prestamo_local_dias", "14", "Plazo de préstamo local (días corridos desde la entrega)"),
    (
        "plazo_prestamo_inter_dias",
        "21",
        "Plazo de préstamo interbibliotecario (días desde la entrega)",
    ),
    ("renovaciones_maximas", "1", "Renovaciones permitidas por préstamo"),
    ("prestamos_maximos_por_socio", "3", "Préstamos simultáneos por socio"),
    ("reservas_maximas_por_socio", "3", "Reservas activas por socio"),
    ("vigencia_retiro_reserva_dias", "3", "Días para retirar una reserva disponible"),
    ("multa_por_dia", "200.00", "Multa por día de atraso (pesos)"),
    ("transito_maximo_dias", "7", "Días de tránsito antes de poder dar un envío por extraviado"),
]


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


def _movimientos(tabla: str, referencia: str, destino: str) -> None:
    op.create_table(
        tabla,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(referencia, sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=15), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=15), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            [referencia], [f"{destino}.id"], name=op.f(f"fk_{tabla}_{referencia}_{destino}")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f(f"fk_{tabla}_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{tabla}")),
    )
    op.create_index(f"ix_{tabla}_{referencia}_fecha_hora", tabla, [referencia, "fecha_hora"])
    op.execute(
        f"CREATE TRIGGER trg_{tabla}_solo_insercion BEFORE UPDATE OR DELETE ON {tabla} "
        "FOR EACH ROW EXECUTE FUNCTION historial_solo_insercion()"
    )


def upgrade() -> None:
    parametro = op.create_table(
        "parametro",
        sa.Column("clave", sa.String(length=40), nullable=False),
        sa.Column("valor", sa.String(length=40), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("clave", name=op.f("pk_parametro")),
    )
    op.bulk_insert(
        parametro,
        [{"clave": c, "valor": v, "descripcion": d} for c, v, d in PARAMETROS],
    )

    op.create_table(
        "prestamo",
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("socio_id", sa.BigInteger(), nullable=False),
        sa.Column("ejemplar_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("sede_origen_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_destino_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=15), nullable=False),
        sa.Column("fecha_solicitud", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("fecha_devolucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renovaciones", sa.SmallInteger(), nullable=False),
        sa.Column("registrado_por_id", sa.BigInteger(), nullable=False),
        *_auditoria(),
        sa.CheckConstraint(
            "tipo IN ('LOCAL','INTERBIBLIOTECARIO')", name=op.f("ck_prestamo_tipo_valido")
        ),
        sa.CheckConstraint(
            "estado IN ('SOLICITADO','EN_ENVIO','ACTIVO','VENCIDO','DEVUELTO','CANCELADO')",
            name=op.f("ck_prestamo_estado_valido"),
        ),
        sa.CheckConstraint(
            "(tipo = 'LOCAL' AND sede_origen_id = sede_destino_id)"
            " OR (tipo = 'INTERBIBLIOTECARIO' AND sede_origen_id <> sede_destino_id)",
            name=op.f("ck_prestamo_sedes_segun_tipo"),
        ),
        sa.CheckConstraint("renovaciones >= 0", name=op.f("ck_prestamo_renovaciones_no_negativas")),
        sa.ForeignKeyConstraint(
            ["socio_id"], ["socio.id"], name=op.f("fk_prestamo_socio_id_socio")
        ),
        sa.ForeignKeyConstraint(
            ["ejemplar_id"], ["ejemplar.id"], name=op.f("fk_prestamo_ejemplar_id_ejemplar")
        ),
        sa.ForeignKeyConstraint(
            ["sede_origen_id"], ["sede.id"], name=op.f("fk_prestamo_sede_origen_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["sede_destino_id"], ["sede.id"], name=op.f("fk_prestamo_sede_destino_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["registrado_por_id"],
            ["usuario.id"],
            name=op.f("fk_prestamo_registrado_por_id_usuario"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prestamo")),
        sa.UniqueConstraint("numero", name=op.f("uq_prestamo_numero")),
    )
    op.create_index(
        "uq_prestamo_abierto_por_ejemplar",
        "prestamo",
        ["ejemplar_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('SOLICITADO','EN_ENVIO','ACTIVO','VENCIDO')"),
    )
    op.create_index("ix_prestamo_socio_id_estado", "prestamo", ["socio_id", "estado"])
    op.create_index(
        "ix_prestamo_estado_fecha_vencimiento", "prestamo", ["estado", "fecha_vencimiento"]
    )
    op.create_index("ix_prestamo_tipo_fecha_solicitud", "prestamo", ["tipo", "fecha_solicitud"])

    op.create_table(
        "remito",
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("sede_origen_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_destino_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(length=15), nullable=False),
        sa.Column("estado", sa.String(length=15), nullable=False),
        sa.Column("fecha_generacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_despacho", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_recepcion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *_auditoria(),
        sa.CheckConstraint(
            "sede_origen_id <> sede_destino_id", name=op.f("ck_remito_sedes_distintas")
        ),
        sa.CheckConstraint(
            "motivo IN ('ENVIO','RETORNO','TRASLADO')", name=op.f("ck_remito_motivo_valido")
        ),
        sa.CheckConstraint(
            "estado IN ('GENERADO','EMPAQUETADO','DESPACHADO','EN_TRANSITO','RECIBIDO',"
            "'EXTRAVIADO','DANADO','DESTRUIDO','ANULADO')",
            name=op.f("ck_remito_estado_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["sede_origen_id"], ["sede.id"], name=op.f("fk_remito_sede_origen_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["sede_destino_id"], ["sede.id"], name=op.f("fk_remito_sede_destino_id_sede")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remito")),
        sa.UniqueConstraint("numero", name=op.f("uq_remito_numero")),
    )
    op.create_index(
        "ix_remito_estado_sede_origen_id_sede_destino_id",
        "remito",
        ["estado", "sede_origen_id", "sede_destino_id"],
    )

    op.create_table(
        "detalle_remito",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("remito_id", sa.BigInteger(), nullable=False),
        sa.Column("ejemplar_id", sa.BigInteger(), nullable=False),
        sa.Column("prestamo_id", sa.BigInteger(), nullable=True),
        sa.Column("estado_fisico_salida", sa.String(length=10), nullable=False),
        sa.Column("estado_fisico_llegada", sa.String(length=10), nullable=True),
        sa.Column("resultado", sa.String(length=10), nullable=True),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["remito_id"], ["remito.id"], name=op.f("fk_detalle_remito_remito_id_remito")
        ),
        sa.ForeignKeyConstraint(
            ["ejemplar_id"], ["ejemplar.id"], name=op.f("fk_detalle_remito_ejemplar_id_ejemplar")
        ),
        sa.ForeignKeyConstraint(
            ["prestamo_id"], ["prestamo.id"], name=op.f("fk_detalle_remito_prestamo_id_prestamo")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_detalle_remito")),
        sa.UniqueConstraint(
            "remito_id", "ejemplar_id", name=op.f("uq_detalle_remito_remito_id_ejemplar_id")
        ),
    )

    _movimientos("movimiento_prestamo", "prestamo_id", "prestamo")
    _movimientos("movimiento_remito", "remito_id", "remito")

    op.create_table(
        "incidencia",
        sa.Column("tipo", sa.String(length=15), nullable=False),
        sa.Column("origen", sa.String(length=15), nullable=False),
        sa.Column("ejemplar_id", sa.BigInteger(), nullable=False),
        sa.Column("socio_id", sa.BigInteger(), nullable=True),
        sa.Column("prestamo_id", sa.BigInteger(), nullable=True),
        sa.Column("remito_id", sa.BigInteger(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        *_auditoria(),
        sa.CheckConstraint(
            "tipo IN ('EXTRAVIO','DANIO','DESTRUCCION')", name=op.f("ck_incidencia_tipo_valido")
        ),
        sa.CheckConstraint(
            "origen IN ('DEVOLUCION','REMITO')", name=op.f("ck_incidencia_origen_valido")
        ),
        sa.ForeignKeyConstraint(
            ["ejemplar_id"], ["ejemplar.id"], name=op.f("fk_incidencia_ejemplar_id_ejemplar")
        ),
        sa.ForeignKeyConstraint(
            ["socio_id"], ["socio.id"], name=op.f("fk_incidencia_socio_id_socio")
        ),
        sa.ForeignKeyConstraint(
            ["prestamo_id"], ["prestamo.id"], name=op.f("fk_incidencia_prestamo_id_prestamo")
        ),
        sa.ForeignKeyConstraint(
            ["remito_id"], ["remito.id"], name=op.f("fk_incidencia_remito_id_remito")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_incidencia_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidencia")),
    )

    op.execute("CREATE SEQUENCE prestamo_numero_seq")
    op.execute("CREATE SEQUENCE remito_numero_seq")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS remito_numero_seq")
    op.execute("DROP SEQUENCE IF EXISTS prestamo_numero_seq")
    op.drop_table("incidencia")
    for tabla in ("movimiento_remito", "movimiento_prestamo"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_solo_insercion ON {tabla}")
        op.drop_table(tabla)
    op.drop_table("detalle_remito")
    op.drop_table("remito")
    op.drop_table("prestamo")
    op.drop_table("parametro")
