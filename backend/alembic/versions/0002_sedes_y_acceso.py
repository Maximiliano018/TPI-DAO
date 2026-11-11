"""Usuarios, socios, sedes, horarios, excepciones e historial

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("rol", sa.String(length=15), nullable=False),
        sa.Column("sede_id", sa.BigInteger(), nullable=True),
        sa.Column("socio_id", sa.BigInteger(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por_id", sa.BigInteger(), nullable=True),
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
            "(rol = 'SOCIO') = (socio_id IS NOT NULL)", name=op.f("ck_usuario_socio_con_ficha")
        ),
        sa.CheckConstraint(
            "rol <> 'ADMIN' OR sede_id IS NULL", name=op.f("ck_usuario_admin_sin_sede")
        ),
        sa.CheckConstraint(
            "rol <> 'BIBLIOTECARIO' OR sede_id IS NOT NULL",
            name=op.f("ck_usuario_bibliotecario_con_sede"),
        ),
        sa.CheckConstraint(
            "rol IN ('ADMIN','BIBLIOTECARIO','SOCIO')", name=op.f("ck_usuario_rol_valido")
        ),
        sa.CheckConstraint(
            "username ~ '^[a-z0-9._-]{3,50}$'", name=op.f("ck_usuario_username_formato")
        ),
        sa.ForeignKeyConstraint(
            ["actualizado_por_id"],
            ["usuario.id"],
            name=op.f("fk_usuario_actualizado_por_id_usuario"),
        ),
        sa.ForeignKeyConstraint(
            ["creado_por_id"], ["usuario.id"], name=op.f("fk_usuario_creado_por_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("socio_id", name=op.f("uq_usuario_socio_id")),
        sa.UniqueConstraint("username", name=op.f("uq_usuario_username")),
    )
    op.create_index(
        "ix_usuario_bibliotecarios_activos_por_sede",
        "usuario",
        ["sede_id"],
        unique=False,
        postgresql_where=sa.text("rol = 'BIBLIOTECARIO' AND activo"),
    )
    op.create_table(
        "sede",
        sa.Column("codigo", sa.String(length=15), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=100), nullable=False),
        sa.Column("calle", sa.String(length=100), nullable=False),
        sa.Column("numero", sa.String(length=10), nullable=False),
        sa.Column("localidad_id", sa.BigInteger(), nullable=False),
        sa.Column("direccion_normalizada", sa.String(length=200), nullable=False),
        sa.Column("telefono", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("responsable", sa.String(length=100), nullable=False),
        sa.Column("estado", sa.String(length=10), server_default="ACTIVA", nullable=False),
        sa.Column("fecha_baja", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_baja", sa.String(length=300), nullable=True),
        sa.Column("baja_por_id", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("creado_por_id", sa.BigInteger(), nullable=False),
        sa.Column("actualizado_por_id", sa.BigInteger(), nullable=False),
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
            "(estado = 'BAJA' AND fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL AND baja_por_id IS NOT NULL) OR (estado = 'ACTIVA' AND fecha_baja IS NULL AND motivo_baja IS NULL AND baja_por_id IS NULL)",
            name=op.f("ck_sede_datos_de_baja_coherentes"),
        ),
        sa.CheckConstraint("codigo ~ '^[A-Z0-9_]{3,15}$'", name=op.f("ck_sede_codigo_formato")),
        sa.CheckConstraint("estado IN ('ACTIVA','BAJA')", name=op.f("ck_sede_estado_valido")),
        sa.CheckConstraint(
            "telefono ~ '^\\+[1-9][0-9]{7,14}$'", name=op.f("ck_sede_telefono_e164")
        ),
        sa.ForeignKeyConstraint(
            ["actualizado_por_id"], ["usuario.id"], name=op.f("fk_sede_actualizado_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["baja_por_id"], ["usuario.id"], name=op.f("fk_sede_baja_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["creado_por_id"], ["usuario.id"], name=op.f("fk_sede_creado_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["localidad_id"], ["localidad.id"], name=op.f("fk_sede_localidad_id_localidad")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sede")),
        sa.UniqueConstraint("codigo", name=op.f("uq_sede_codigo")),
        sa.UniqueConstraint("nombre_normalizado", name=op.f("uq_sede_nombre_normalizado")),
    )
    op.create_index(
        "ix_sede_direccion_normalizada", "sede", ["direccion_normalizada"], unique=False
    )
    op.create_index("ix_sede_estado_nombre", "sede", ["estado", "nombre"], unique=False)
    op.create_table(
        "socio",
        sa.Column("numero_socio", sa.String(length=15), nullable=False),
        sa.Column("tipo_documento", sa.String(length=10), nullable=False),
        sa.Column("nro_documento", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("apellido", sa.String(length=100), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("domicilio", sa.String(length=200), nullable=True),
        sa.Column("sede_alta_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=15), nullable=False),
        sa.Column("motivo_inhabilitacion", sa.String(length=30), nullable=True),
        sa.Column("fecha_baja", sa.DateTime(timezone=True), nullable=True),
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
            "estado IN ('HABILITADO','INHABILITADO')", name=op.f("ck_socio_estado_valido")
        ),
        sa.ForeignKeyConstraint(
            ["sede_alta_id"], ["sede.id"], name=op.f("fk_socio_sede_alta_id_sede")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_socio")),
        sa.UniqueConstraint("numero_socio", name=op.f("uq_socio_numero_socio")),
        sa.UniqueConstraint(
            "tipo_documento", "nro_documento", name=op.f("uq_socio_tipo_documento_nro_documento")
        ),
    )
    op.create_table(
        "horario_sede",
        sa.Column("sede_id", sa.BigInteger(), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_apertura", sa.Time(), nullable=False),
        sa.Column("hora_cierre", sa.Time(), nullable=False),
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
        sa.CheckConstraint("dia_semana BETWEEN 1 AND 7", name=op.f("ck_horario_sede_dia_valido")),
        sa.CheckConstraint(
            "hora_cierre > hora_apertura", name=op.f("ck_horario_sede_cierre_posterior")
        ),
        sa.ForeignKeyConstraint(
            ["sede_id"], ["sede.id"], name=op.f("fk_horario_sede_sede_id_sede")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horario_sede")),
    )
    op.create_index(
        "ix_horario_sede_sede_id_dia_semana",
        "horario_sede",
        ["sede_id", "dia_semana"],
        unique=False,
    )
    op.create_table(
        "excepcion_horario_sede",
        sa.Column("sede_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=15), nullable=False),
        sa.Column("hora_desde", sa.Time(), nullable=True),
        sa.Column("hora_hasta", sa.Time(), nullable=True),
        sa.Column("motivo", sa.String(length=150), nullable=True),
        sa.Column("creado_por_id", sa.BigInteger(), nullable=False),
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
            "(tipo = 'CIERRE_TOTAL' AND hora_desde IS NULL AND hora_hasta IS NULL) OR (tipo = 'CIERRE_PARCIAL' AND hora_desde IS NOT NULL AND hora_hasta IS NOT NULL AND hora_desde < hora_hasta)",
            name=op.f("ck_excepcion_horario_sede_tipo_coherente"),
        ),
        sa.ForeignKeyConstraint(
            ["creado_por_id"],
            ["usuario.id"],
            name=op.f("fk_excepcion_horario_sede_creado_por_id_usuario"),
        ),
        sa.ForeignKeyConstraint(
            ["sede_id"], ["sede.id"], name=op.f("fk_excepcion_horario_sede_sede_id_sede")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_excepcion_horario_sede")),
    )
    op.create_index(
        "ix_excepcion_horario_sede_sede_id_fecha",
        "excepcion_horario_sede",
        ["sede_id", "fecha"],
        unique=False,
    )
    op.create_table(
        "historial_sede",
        sa.Column("sede_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=25), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=10), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=10), nullable=True),
        sa.Column("motivo", sa.String(length=300), nullable=True),
        sa.Column("cambios", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version_resultante", sa.Integer(), nullable=False),
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
            "tipo_evento IN ('ALTA','MODIFICACION','BAJA','REACTIVACION','EXCEPCION_AGREGADA','EXCEPCION_ELIMINADA')",
            name=op.f("ck_historial_sede_tipo_evento_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["sede_id"], ["sede.id"], name=op.f("fk_historial_sede_sede_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_historial_sede_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historial_sede")),
    )
    op.create_index(
        "ix_historial_sede_sede_id_fecha_hora",
        "historial_sede",
        ["sede_id", sa.literal_column("fecha_hora DESC")],
        unique=False,
    )

    # Las claves de usuario hacia sede y socio se agregan al final por la dependencia circular.
    op.create_foreign_key(op.f("fk_usuario_sede_id_sede"), "usuario", "sede", ["sede_id"], ["id"])
    op.create_foreign_key(
        op.f("fk_usuario_socio_id_socio"), "usuario", "socio", ["socio_id"], ["id"]
    )

    # Las franjas de un mismo día de una sede no se solapan (rango semiabierto [apertura, cierre)).
    op.execute(
        """
        ALTER TABLE horario_sede ADD CONSTRAINT ex_horario_sede_sin_solapamiento
        EXCLUDE USING gist (
            sede_id WITH =,
            dia_semana WITH =,
            tsrange(DATE '2000-01-01' + hora_apertura, DATE '2000-01-01' + hora_cierre, '[)') WITH &&
        )
        """
    )
    # Las excepciones de una sede no se solapan; el cierre total ocupa todo el día.
    op.execute(
        """
        ALTER TABLE excepcion_horario_sede ADD CONSTRAINT ex_excepcion_horario_sin_solapamiento
        EXCLUDE USING gist (
            sede_id WITH =,
            tsrange(
                fecha + COALESCE(hora_desde, TIME '00:00'),
                CASE WHEN tipo = 'CIERRE_TOTAL' THEN fecha + 1 ELSE fecha + hora_hasta END,
                '[)'
            ) WITH &&
        )
        """
    )
    # El historial es de solo inserción.
    op.execute(
        """
        CREATE FUNCTION historial_sede_solo_insercion() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'historial_sede es de solo inserción';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_historial_sede_solo_insercion
        BEFORE UPDATE OR DELETE ON historial_sede
        FOR EACH ROW EXECUTE FUNCTION historial_sede_solo_insercion()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_historial_sede_solo_insercion ON historial_sede")
    op.execute("DROP FUNCTION IF EXISTS historial_sede_solo_insercion()")
    op.drop_table("historial_sede")
    op.drop_table("excepcion_horario_sede")
    op.drop_table("horario_sede")
    op.drop_constraint(op.f("fk_usuario_socio_id_socio"), "usuario", type_="foreignkey")
    op.drop_constraint(op.f("fk_usuario_sede_id_sede"), "usuario", type_="foreignkey")
    op.drop_table("socio")
    op.drop_table("sede")
    op.drop_table("usuario")
