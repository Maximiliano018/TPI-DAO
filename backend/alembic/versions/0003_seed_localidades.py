"""Carga inicial: provincia de Córdoba y sus principales localidades.

Es una lista de partida (ciudad de Córdoba y principales localidades por departamento);
la carga completa del catálogo oficial se hace con una migración de datos posterior.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

PROVINCIA = "Córdoba"

LOCALIDADES = [
    ("Córdoba", "Capital"),
    ("Villa Allende", "Colón"),
    ("Río Ceballos", "Colón"),
    ("Unquillo", "Colón"),
    ("Mendiolaza", "Colón"),
    ("Saldán", "Colón"),
    ("La Calera", "Colón"),
    ("Salsipuedes", "Colón"),
    ("Jesús María", "Colón"),
    ("Colonia Caroya", "Colón"),
    ("Malvinas Argentinas", "Colón"),
    ("Alta Gracia", "Santa María"),
    ("Malagueño", "Santa María"),
    ("Despeñaderos", "Santa María"),
    ("Villa Carlos Paz", "Punilla"),
    ("Cosquín", "Punilla"),
    ("La Falda", "Punilla"),
    ("Capilla del Monte", "Punilla"),
    ("Bialet Massé", "Punilla"),
    ("Valle Hermoso", "Punilla"),
    ("Huerta Grande", "Punilla"),
    ("La Cumbre", "Punilla"),
    ("Villa General Belgrano", "Calamuchita"),
    ("Santa Rosa de Calamuchita", "Calamuchita"),
    ("Embalse", "Calamuchita"),
    ("Río Cuarto", "Río Cuarto"),
    ("Las Higueras", "Río Cuarto"),
    ("Sampacho", "Río Cuarto"),
    ("Vicuña Mackenna", "Río Cuarto"),
    ("Alcira Gigena", "Río Cuarto"),
    ("Villa María", "General San Martín"),
    ("Villa Nueva", "General San Martín"),
    ("Río Tercero", "Tercero Arriba"),
    ("Oliva", "Tercero Arriba"),
    ("Almafuerte", "Tercero Arriba"),
    ("Hernando", "Tercero Arriba"),
    ("Río Segundo", "Río Segundo"),
    ("Oncativo", "Río Segundo"),
    ("Pilar", "Río Segundo"),
    ("Villa del Rosario", "Río Segundo"),
    ("San Francisco", "San Justo"),
    ("Morteros", "San Justo"),
    ("Arroyito", "San Justo"),
    ("Las Varillas", "San Justo"),
    ("Freyre", "San Justo"),
    ("Brinkmann", "San Justo"),
    ("Balnearia", "San Justo"),
    ("Bell Ville", "Unión"),
    ("Morrison", "Unión"),
    ("Justiniano Posse", "Unión"),
    ("Noetinger", "Unión"),
    ("Monte Maíz", "Unión"),
    ("Marcos Juárez", "Marcos Juárez"),
    ("Corral de Bustos", "Marcos Juárez"),
    ("Leones", "Marcos Juárez"),
    ("Laboulaye", "Presidente Roque Sáenz Peña"),
    ("Huinca Renancó", "General Roca"),
    ("General Cabrera", "Juárez Celman"),
    ("La Carlota", "Juárez Celman"),
    ("General Deheza", "Juárez Celman"),
    ("Alejandro Roca", "Juárez Celman"),
    ("Cruz del Eje", "Cruz del Eje"),
    ("Villa de Soto", "Cruz del Eje"),
    ("Deán Funes", "Ischilín"),
    ("Villa Dolores", "San Javier"),
    ("Mina Clavero", "San Alberto"),
    ("Villa Cura Brochero", "San Alberto"),
]


def upgrade() -> None:
    conexion = op.get_bind()
    provincia_id = conexion.execute(
        sa.text("INSERT INTO provincia (nombre) VALUES (:n) RETURNING id"), {"n": PROVINCIA}
    ).scalar_one()
    conexion.execute(
        sa.text("INSERT INTO localidad (provincia_id, nombre, departamento) VALUES (:p, :n, :d)"),
        [{"p": provincia_id, "n": n, "d": d} for n, d in LOCALIDADES],
    )


def downgrade() -> None:
    op.execute("DELETE FROM localidad")
    op.execute("DELETE FROM provincia")
