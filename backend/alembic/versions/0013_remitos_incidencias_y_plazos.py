"""Remitos: responsable de las incidencias, faltantes, plazo de despacho y recuperación

- ``incidencia.sede_responsable_id``: una incidencia de remito queda a cargo de la sede origen
  (la que lo despachó) y ya no del socio; las de devolución siguen a cargo del socio. Las
  incidencias de remito existentes se corrigen: se quita el socio y se asigna la sede origen.
- ``incidencia.resuelta_en``, ``resuelta_por_id`` y ``resolucion``: un extravío se resuelve
  cuando el ejemplar aparece y se recupera.
- Estado de remito ``INCOMPLETO`` (recibido con faltantes) y resultado de línea ``FALTANTE``.
- Parámetro ``despacho_maximo_dias`` (3): pasado ese plazo sin despachar, el remito se marca
  atrasado.
- ``CHECK`` nuevos: fechas del remito según su estado, valores y coherencia del detalle, y
  responsable de la incidencia según su origen.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_ESTADOS = (
    "'GENERADO','EMPAQUETADO','DESPACHADO','EN_TRANSITO','RECIBIDO','EXTRAVIADO','DANADO',"
    "'DESTRUIDO'{extra},'ANULADO'"
)
_FISICOS = "('NUEVO','BUENO','REGULAR','DANADO')"


def upgrade() -> None:
    # --- incidencias: responsable y resolución
    op.add_column("incidencia", sa.Column("sede_responsable_id", sa.BigInteger(), nullable=True))
    op.add_column("incidencia", sa.Column("resuelta_en", sa.DateTime(timezone=True)))
    op.add_column("incidencia", sa.Column("resuelta_por_id", sa.BigInteger(), nullable=True))
    op.add_column("incidencia", sa.Column("resolucion", sa.Text(), nullable=True))
    op.create_foreign_key(
        op.f("fk_incidencia_sede_responsable_id_sede"),
        "incidencia",
        "sede",
        ["sede_responsable_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_incidencia_resuelta_por_id_usuario"),
        "incidencia",
        "usuario",
        ["resuelta_por_id"],
        ["id"],
    )
    op.execute(
        """
        UPDATE incidencia i SET socio_id = NULL, sede_responsable_id = r.sede_origen_id
        FROM remito r WHERE i.origen = 'REMITO' AND r.id = i.remito_id
        """
    )
    op.create_check_constraint(
        op.f("ck_incidencia_responsable_segun_origen"),
        "incidencia",
        "(origen = 'REMITO' AND remito_id IS NOT NULL AND socio_id IS NULL "
        "AND sede_responsable_id IS NOT NULL) "
        "OR (origen = 'DEVOLUCION' AND prestamo_id IS NOT NULL AND socio_id IS NOT NULL "
        "AND sede_responsable_id IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_incidencia_resolucion_coherente"),
        "incidencia",
        "(resuelta_en IS NULL) = (resolucion IS NULL) "
        "AND (resuelta_en IS NULL OR tipo = 'EXTRAVIO')",
    )

    # --- remito: estado INCOMPLETO y fechas según el estado
    op.drop_constraint(op.f("ck_remito_estado_valido"), "remito", type_="check")
    op.create_check_constraint(
        op.f("ck_remito_estado_valido"),
        "remito",
        f"estado IN ({_ESTADOS.format(extra=",'INCOMPLETO'")})",
    )
    op.create_check_constraint(
        op.f("ck_remito_despacho_segun_estado"),
        "remito",
        "(estado IN ('GENERADO','EMPAQUETADO','ANULADO')) = (fecha_despacho IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_remito_recepcion_segun_estado"),
        "remito",
        "(estado IN ('RECIBIDO','DANADO','DESTRUIDO','INCOMPLETO')) "
        "= (fecha_recepcion IS NOT NULL)",
    )

    # --- detalle: valores válidos y coherencia entre resultado y estado físico de llegada
    op.create_check_constraint(
        op.f("ck_detalle_remito_estado_fisico_salida_valido"),
        "detalle_remito",
        f"estado_fisico_salida IN {_FISICOS}",
    )
    op.create_check_constraint(
        op.f("ck_detalle_remito_estado_fisico_llegada_valido"),
        "detalle_remito",
        f"estado_fisico_llegada IS NULL OR estado_fisico_llegada IN {_FISICOS}",
    )
    op.create_check_constraint(
        op.f("ck_detalle_remito_resultado_valido"),
        "detalle_remito",
        "resultado IS NULL OR resultado IN ('RECIBIDO','DANADO','DESTRUIDO','FALTANTE')",
    )
    op.create_check_constraint(
        op.f("ck_detalle_remito_llegada_segun_resultado"),
        "detalle_remito",
        "(estado_fisico_llegada IS NOT NULL) "
        "= (resultado IS NOT NULL AND resultado <> 'FALTANTE')",
    )

    op.execute(
        "INSERT INTO parametro (clave, valor, descripcion) VALUES ('despacho_maximo_dias', '3', "
        "'Días para despachar un remito generado antes de marcarlo atrasado')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametro WHERE clave = 'despacho_maximo_dias'")
    for nombre in (
        "ck_detalle_remito_llegada_segun_resultado",
        "ck_detalle_remito_resultado_valido",
        "ck_detalle_remito_estado_fisico_llegada_valido",
        "ck_detalle_remito_estado_fisico_salida_valido",
    ):
        op.drop_constraint(op.f(nombre), "detalle_remito", type_="check")
    # Un remito incompleto no existía: queda como dañado (recibido con incidencia).
    op.execute("UPDATE remito SET estado = 'DANADO' WHERE estado = 'INCOMPLETO'")
    op.execute("UPDATE detalle_remito SET resultado = 'DESTRUIDO' WHERE resultado = 'FALTANTE'")
    for nombre in (
        "ck_remito_recepcion_segun_estado",
        "ck_remito_despacho_segun_estado",
        "ck_remito_estado_valido",
    ):
        op.drop_constraint(op.f(nombre), "remito", type_="check")
    op.create_check_constraint(
        op.f("ck_remito_estado_valido"), "remito", f"estado IN ({_ESTADOS.format(extra='')})"
    )
    op.drop_constraint(op.f("ck_incidencia_resolucion_coherente"), "incidencia", type_="check")
    op.drop_constraint(op.f("ck_incidencia_responsable_segun_origen"), "incidencia", type_="check")
    op.drop_constraint(op.f("fk_incidencia_resuelta_por_id_usuario"), "incidencia", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_incidencia_sede_responsable_id_sede"), "incidencia", type_="foreignkey"
    )
    op.drop_column("incidencia", "resolucion")
    op.drop_column("incidencia", "resuelta_por_id")
    op.drop_column("incidencia", "resuelta_en")
    op.drop_column("incidencia", "sede_responsable_id")
