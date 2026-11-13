"""Catálogo: categorías, autores, libros, ejemplares e historial del ejemplar

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

CATEGORIAS = [
    "Literatura argentina",
    "Literatura latinoamericana",
    "Literatura universal",
    "Infantil y juvenil",
    "Historia",
    "Ciencias sociales",
    "Ciencias naturales",
    "Tecnología e informática",
    "Arte y música",
    "Filosofía",
    "Obras de referencia",
    "Otros",
]

ESTADOS = "'DISPONIBLE','APARTADO','RESERVADO','PRESTADO','EN_TRANSITO','EN_REVISION','BAJA'"


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


def upgrade() -> None:
    categoria = op.create_table(
        "categoria",
        sa.Column("nombre", sa.String(length=60), nullable=False),
        *_auditoria(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categoria")),
        sa.UniqueConstraint("nombre", name=op.f("uq_categoria_nombre")),
    )
    op.bulk_insert(categoria, [{"nombre": nombre} for nombre in CATEGORIAS])

    op.create_table(
        "autor",
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=100), nullable=False),
        *_auditoria(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_autor")),
        sa.UniqueConstraint("nombre_normalizado", name=op.f("uq_autor_nombre_normalizado")),
    )

    op.create_table(
        "libro",
        sa.Column("isbn", sa.String(length=13), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("titulo_normalizado", sa.String(length=200), nullable=False),
        sa.Column("editorial", sa.String(length=100), nullable=True),
        sa.Column("anio_edicion", sa.SmallInteger(), nullable=True),
        sa.Column("categoria_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_material", sa.String(length=20), nullable=False),
        sa.Column("clave_natural", sa.String(length=420), nullable=True),
        sa.Column("creado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por_id", sa.BigInteger(), nullable=True),
        *_auditoria(),
        sa.CheckConstraint(
            "tipo_material IN ('LIBRO','REVISTA','OBRA_DE_REFERENCIA','OTRO')",
            name=op.f("ck_libro_tipo_material_valido"),
        ),
        sa.CheckConstraint(
            "(isbn IS NULL) = (clave_natural IS NOT NULL)", name=op.f("ck_libro_isbn_o_clave")
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categoria.id"], name=op.f("fk_libro_categoria_id_categoria")
        ),
        sa.ForeignKeyConstraint(
            ["creado_por_id"], ["usuario.id"], name=op.f("fk_libro_creado_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["actualizado_por_id"], ["usuario.id"], name=op.f("fk_libro_actualizado_por_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_libro")),
        sa.UniqueConstraint("isbn", name=op.f("uq_libro_isbn")),
        sa.UniqueConstraint("clave_natural", name=op.f("uq_libro_clave_natural")),
    )
    op.create_index("ix_libro_titulo_normalizado", "libro", ["titulo_normalizado"])

    op.create_table(
        "libro_autor",
        sa.Column("libro_id", sa.BigInteger(), nullable=False),
        sa.Column("autor_id", sa.BigInteger(), nullable=False),
        sa.Column("orden", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["libro_id"],
            ["libro.id"],
            name=op.f("fk_libro_autor_libro_id_libro"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["autor_id"], ["autor.id"], name=op.f("fk_libro_autor_autor_id_autor")
        ),
        sa.PrimaryKeyConstraint("libro_id", "autor_id", name=op.f("pk_libro_autor")),
    )

    op.create_table(
        "ejemplar",
        sa.Column("codigo_inventario", sa.String(length=30), nullable=False),
        sa.Column("libro_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_propietaria_id", sa.BigInteger(), nullable=False),
        sa.Column("sede_actual_id", sa.BigInteger(), nullable=False),
        sa.Column("estado_fisico", sa.String(length=10), nullable=False),
        sa.Column("estado", sa.String(length=15), nullable=False),
        sa.Column("observaciones", sa.String(length=300), nullable=True),
        sa.Column("fecha_baja", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_baja", sa.String(length=300), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *_auditoria(),
        sa.CheckConstraint(
            "estado_fisico IN ('NUEVO','BUENO','REGULAR','DANADO')",
            name=op.f("ck_ejemplar_estado_fisico_valido"),
        ),
        sa.CheckConstraint(f"estado IN ({ESTADOS})", name=op.f("ck_ejemplar_estado_valido")),
        sa.CheckConstraint(
            "(estado = 'BAJA') = (fecha_baja IS NOT NULL AND motivo_baja IS NOT NULL)",
            name=op.f("ck_ejemplar_baja_con_datos"),
        ),
        sa.CheckConstraint(
            "codigo_inventario ~ '^[A-Z0-9][A-Z0-9-]{2,29}$'",
            name=op.f("ck_ejemplar_codigo_formato"),
        ),
        sa.ForeignKeyConstraint(
            ["libro_id"], ["libro.id"], name=op.f("fk_ejemplar_libro_id_libro")
        ),
        sa.ForeignKeyConstraint(
            ["sede_propietaria_id"], ["sede.id"], name=op.f("fk_ejemplar_sede_propietaria_id_sede")
        ),
        sa.ForeignKeyConstraint(
            ["sede_actual_id"], ["sede.id"], name=op.f("fk_ejemplar_sede_actual_id_sede")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ejemplar")),
        sa.UniqueConstraint("codigo_inventario", name=op.f("uq_ejemplar_codigo_inventario")),
    )
    op.create_index(
        "ix_ejemplar_libro_id_sede_actual_id_estado",
        "ejemplar",
        ["libro_id", "sede_actual_id", "estado"],
    )
    op.create_index(
        "ix_ejemplar_sede_propietaria_id_estado", "ejemplar", ["sede_propietaria_id", "estado"]
    )

    op.create_table(
        "movimiento_ejemplar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ejemplar_id", sa.BigInteger(), nullable=False),
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
            ["ejemplar_id"],
            ["ejemplar.id"],
            name=op.f("fk_movimiento_ejemplar_ejemplar_id_ejemplar"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_movimiento_ejemplar_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimiento_ejemplar")),
    )
    op.create_index(
        "ix_movimiento_ejemplar_ejemplar_id_fecha_hora",
        "movimiento_ejemplar",
        ["ejemplar_id", "fecha_hora"],
    )

    # Los historiales son de solo inserción: la misma función protege los de cada módulo.
    op.execute(
        """
        CREATE FUNCTION historial_solo_insercion() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla % es de solo inserción', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_movimiento_ejemplar_solo_insercion
        BEFORE UPDATE OR DELETE ON movimiento_ejemplar
        FOR EACH ROW EXECUTE FUNCTION historial_solo_insercion()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_movimiento_ejemplar_solo_insercion ON movimiento_ejemplar"
    )
    op.execute("DROP FUNCTION IF EXISTS historial_solo_insercion()")
    op.drop_table("movimiento_ejemplar")
    op.drop_table("ejemplar")
    op.drop_table("libro_autor")
    op.drop_table("libro")
    op.drop_table("autor")
    op.drop_table("categoria")
