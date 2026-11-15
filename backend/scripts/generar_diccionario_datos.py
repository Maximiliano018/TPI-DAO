"""Genera el diccionario de datos y los diagramas entidad-relación desde la base.

Uso (desde ``backend/``, con la base migrada a la última versión):
    python scripts/generar_diccionario_datos.py            # escribe el archivo
    python scripts/generar_diccionario_datos.py --verificar  # error si está desactualizado

Lee el esquema real de PostgreSQL (``DATABASE_URL``): columnas, claves, restricciones
``CHECK``, índices (también los parciales), restricciones de exclusión y disparadores. La
descripción de cada tabla sale del docstring de su modelo del ORM. El resultado es
``database/diccionario-de-datos.md``; no se edita a mano.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import CheckConstraint, create_engine, text

from app.config.settings import get_settings
from app.db import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.db.base import Base

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "database" / "diccionario-de-datos.md"

# Módulos del dominio y sus tablas, en el orden de los procesos del enunciado.
MODULOS: list[tuple[str, str, list[str]]] = [
    (
        "Sedes y acceso",
        "Ubicación de las sedes, sus horarios y cierres, el historial de cambios y los usuarios "
        "del sistema (administrador, bibliotecario y socio con cuenta).",
        [
            "provincia",
            "localidad",
            "sede",
            "horario_sede",
            "excepcion_horario_sede",
            "historial_sede",
            "usuario",
        ],
    ),
    (
        "Socios",
        "Socios de la red, su estado (habilitado, inhabilitado, baja) y su historial.",
        ["socio", "historial_socio"],
    ),
    (
        "Catálogo",
        "Libros (el título), sus autores y categorías, y los ejemplares (las copias físicas), "
        "con el historial de cada ejemplar.",
        ["categoria", "autor", "libro", "libro_autor", "ejemplar", "movimiento_ejemplar"],
    ),
    (
        "Préstamos, remitos e incidencias",
        "Préstamos locales e interbibliotecarios, los remitos que trasladan ejemplares entre "
        "sedes (con su detalle y su historial) y las incidencias (extravío, daño, destrucción).",
        [
            "prestamo",
            "movimiento_prestamo",
            "remito",
            "detalle_remito",
            "movimiento_remito",
            "incidencia",
        ],
    ),
    (
        "Reservas",
        "Cola de reservas por libro y sede de retiro, con su historial.",
        ["reserva", "movimiento_reserva"],
    ),
    (
        "Devoluciones, multas, pagos y parámetros",
        "Devoluciones de préstamos, multas (por atraso, daño o extravío), sus pagos, los "
        "parámetros de negocio configurables y su auditoría.",
        ["devolucion", "multa", "pago", "parametro", "historial_parametro"],
    ),
]

# Claves foráneas de auditoría (quién creó, modificó o registró): se documentan en las
# tablas pero no se dibujan en los diagramas, para que se lean.
AUDITORIA = {
    "creado_por_id",
    "actualizado_por_id",
    "baja_por_id",
    "registrado_por_id",
    "registrada_por_id",
    "saldada_por_id",
    "resuelta_por_id",
}

TIPOS_CORTOS = {
    "bigint": "bigint",
    "integer": "int",
    "smallint": "smallint",
    "character varying": "varchar",
    "text": "text",
    "boolean": "bool",
    "date": "date",
    "time without time zone": "time",
    "timestamp with time zone": "timestamptz",
    "numeric": "numeric",
}


@dataclass
class Columna:
    nombre: str
    tipo: str
    nula: bool
    defecto: str | None


@dataclass
class Tabla:
    nombre: str
    columnas: list[Columna] = field(default_factory=list)
    pk: list[str] = field(default_factory=list)
    unicas: list[tuple[str, list[str]]] = field(default_factory=list)
    fks: list[tuple[str, str, str, str]] = field(default_factory=list)  # nombre, col, tabla, accion
    checks: list[tuple[str, str]] = field(default_factory=list)
    exclusiones: list[tuple[str, str]] = field(default_factory=list)
    indices: list[tuple[str, str]] = field(default_factory=list)
    disparadores: list[tuple[str, str]] = field(default_factory=list)

    @property
    def unica_por_columna(self) -> set[str]:
        return {cols[0] for _, cols in self.unicas if len(cols) == 1}


def _tipo(fila: dict[str, object]) -> str:
    base = str(fila["data_type"])
    if base == "character varying" and fila["character_maximum_length"]:
        return f"VARCHAR({fila['character_maximum_length']})"
    if base == "numeric" and fila["numeric_precision"]:
        return f"NUMERIC({fila['numeric_precision']},{fila['numeric_scale']})"
    return {
        "timestamp with time zone": "TIMESTAMPTZ",
        "time without time zone": "TIME",
        "character varying": "VARCHAR",
    }.get(base, base.upper())


def leer_esquema(url: str) -> dict[str, Tabla]:
    motor = create_engine(url)
    tablas: dict[str, Tabla] = {}
    with motor.connect() as con:
        for fila in con.execute(
            text(
                "SELECT table_name, column_name, data_type, character_maximum_length, "
                "numeric_precision, numeric_scale, is_nullable, column_default "
                "FROM information_schema.columns WHERE table_schema = 'public' "
                "AND table_name <> 'alembic_version' ORDER BY table_name, ordinal_position"
            )
        ).mappings():
            tabla = tablas.setdefault(fila["table_name"], Tabla(fila["table_name"]))
            defecto = fila["column_default"]
            if defecto and defecto.startswith("nextval("):
                defecto = "secuencia"
            tabla.columnas.append(
                Columna(
                    fila["column_name"], _tipo(dict(fila)), fila["is_nullable"] == "YES", defecto
                )
            )
        restricciones = con.execute(
            text(
                "SELECT rel.relname AS tabla, con.conname AS nombre, con.contype AS tipo, "
                "pg_get_constraintdef(con.oid) AS definicion, "
                "ARRAY(SELECT att.attname FROM unnest(con.conkey) WITH ORDINALITY k(n, o) "
                "  JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = k.n "
                "  ORDER BY k.o) AS columnas, "
                "ref.relname AS referida "
                "FROM pg_constraint con JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "LEFT JOIN pg_class ref ON ref.oid = con.confrelid "
                "WHERE ns.nspname = 'public' ORDER BY rel.relname, con.conname"
            )
        ).mappings()
        for r in restricciones:
            tabla = tablas.get(r["tabla"])
            if tabla is None:
                continue
            columnas = list(r["columnas"])
            if r["tipo"] == "p":
                tabla.pk = columnas
            elif r["tipo"] == "u":
                tabla.unicas.append((r["nombre"], columnas))
            elif r["tipo"] == "f":
                accion = "ON DELETE CASCADE" if "ON DELETE CASCADE" in r["definicion"] else ""
                tabla.fks.append((r["nombre"], columnas[0], r["referida"], accion))
            elif r["tipo"] == "c":
                definicion = r["definicion"].removeprefix("CHECK ").strip()
                tabla.checks.append((r["nombre"], definicion))
            elif r["tipo"] == "x":
                tabla.exclusiones.append((r["nombre"], r["definicion"]))
        indices = con.execute(
            text(
                "SELECT i.tablename, i.indexname, i.indexdef FROM pg_indexes i "
                "WHERE i.schemaname = 'public' AND NOT EXISTS (SELECT 1 FROM pg_constraint c "
                "WHERE c.conname = i.indexname) ORDER BY i.tablename, i.indexname"
            )
        ).mappings()
        for r in indices:
            if r["tablename"] in tablas:
                definicion = r["indexdef"].split(" USING ", 1)[-1]
                unico = "UNIQUE " if "UNIQUE INDEX" in r["indexdef"] else ""
                tablas[r["tablename"]].indices.append((r["indexname"], unico + definicion))
                if unico and " WHERE " not in definicion:
                    cols = definicion.split("(", 1)[1].rsplit(")", 1)[0].split(", ")
                    tablas[r["tablename"]].unicas.append((r["indexname"], cols))
        disparadores = con.execute(
            text(
                "SELECT event_object_table AS tabla, trigger_name AS nombre, "
                "string_agg(event_manipulation, ' o ' ORDER BY event_manipulation) AS eventos, "
                "min(action_timing) AS momento, min(action_statement) AS accion "
                "FROM information_schema.triggers GROUP BY 1, 2 ORDER BY 1, 2"
            )
        ).mappings()
        for r in disparadores:
            if r["tabla"] in tablas:
                tablas[r["tabla"]].disparadores.append(
                    (r["nombre"], f"{r['momento']} {r['eventos']}: {r['accion']}")
                )
    motor.dispose()
    return tablas


def checks_del_orm() -> dict[str, str]:
    """Texto de cada ``CHECK`` tal como está escrito en el modelo del ORM, por nombre."""
    resultado = {}
    for tabla in Base.metadata.tables.values():
        for restriccion in tabla.constraints:
            if isinstance(restriccion, CheckConstraint) and restriccion.name:
                nombre = str(restriccion.name)
                if not nombre.startswith("ck_"):
                    nombre = f"ck_{tabla.name}_{nombre}"
                resultado[nombre] = " ".join(str(restriccion.sqltext).split())
    return resultado


def ordenar_columnas(tablas: dict[str, "Tabla"]) -> None:
    """Clave primaria primero, después el orden del modelo y al final las fechas de auditoría."""
    for nombre, tabla in tablas.items():
        orm = Base.metadata.tables.get(nombre)
        orden = {c.name: i for i, c in enumerate(orm.columns)} if orm is not None else {}

        def clave(col: Columna, tabla: Tabla = tabla, orden: dict[str, int] = orden) -> tuple:
            final = col.nombre in ("creado_en", "actualizado_en")
            return (col.nombre not in tabla.pk, final, orden.get(col.nombre, 999))

        tabla.columnas.sort(key=clave)


def descripciones() -> dict[str, str]:
    """Primer párrafo del docstring de cada modelo del ORM, por nombre de tabla."""
    resultado = {}
    for mapper in Base.registry.mappers:
        clase = mapper.class_
        doc = (clase.__doc__ or "").strip()
        if doc and getattr(clase, "__tablename__", None):
            resultado[clase.__tablename__] = " ".join(doc.split("\n\n")[0].split())
    return resultado


def _relaciones(tabla: Tabla) -> list[str]:
    """Una línea por clave foránea de dominio: ``padre ||--o{ hija : "columna"``."""
    lineas = []
    for _, col, referida, _ in tabla.fks:
        if col in AUDITORIA or (referida == "usuario" and col == "usuario_id"):
            continue
        nula = next(c.nula for c in tabla.columnas if c.nombre == col)
        padre = "|o" if nula else "||"
        hija = "o|" if col in tabla.unica_por_columna else "o{"
        lineas.append(f'    {referida} {padre}--{hija} {tabla.nombre} : "{col}"')
    return lineas


def _diagrama(tablas: dict[str, Tabla], nombres: list[str]) -> list[str]:
    lineas = ["```mermaid", "erDiagram"]
    relaciones = []
    for nombre in nombres:
        tabla = tablas[nombre]
        claves_fk = {col for _, col, _, _ in tabla.fks}
        unicas = tabla.unica_por_columna
        lineas.append(f"    {nombre} {{")
        for col in tabla.columnas:
            marcas = []
            if col.nombre in tabla.pk:
                marcas.append("PK")
            if col.nombre in claves_fk:
                marcas.append("FK")
            if col.nombre in unicas:
                marcas.append("UK")
            tipo = TIPOS_CORTOS.get(col.tipo.split("(")[0].lower(), col.tipo.split("(")[0].lower())
            sufijo = f" {', '.join(marcas)}" if marcas else ""
            nota = ' "opcional"' if col.nula and not marcas else ""
            lineas.append(f"        {tipo} {col.nombre}{sufijo}{nota}")
        lineas.append("    }")
        relaciones.extend(_relaciones(tabla))
    lineas.extend(relaciones)
    lineas.append("```")
    return lineas


def _diagrama_general(tablas: dict[str, Tabla]) -> list[str]:
    lineas = ["```mermaid", "erDiagram"]
    for nombre in sorted(tablas):
        lineas.extend(_relaciones(tablas[nombre]))
    lineas.append("```")
    return lineas


_CONVERSIONES = re.compile(r"::(?:text|character varying|date|time without time zone)(?:\[\])?")
_ANY = re.compile(r"\(?\((\w+)\) = ANY \(\(?ARRAY\[([^\]]*)\]\)?\)\)?")


def _legible(sql: str) -> str:
    """Quita las conversiones de tipo que agrega PostgreSQL y vuelve ``= ANY (ARRAY[...])``
    a ``IN (...)``, para que se lea como está escrito en las migraciones."""
    sql = _CONVERSIONES.sub("", sql)
    sql = _ANY.sub(lambda m: f"{m.group(1)} IN ({m.group(2)})", sql)
    return re.sub(r"(?<!btree )(?<!gist )\((\w+)\)", r"\1", sql)


def _celda(texto: str) -> str:
    return _legible(texto).replace("|", "\\|").replace("\n", " ")


def generar(tablas: dict[str, Tabla]) -> str:
    docs = descripciones()
    del_orm = checks_del_orm()
    ordenar_columnas(tablas)
    sin_modulo = sorted(set(tablas) - {t for _, _, ts in MODULOS for t in ts})
    if sin_modulo:
        raise SystemExit(f"Tablas sin módulo en el script: {', '.join(sin_modulo)}")
    salida = [
        "# Diccionario de datos",
        "",
        "<!-- Generado con backend/scripts/generar_diccionario_datos.py: no editar a mano. -->",
        "",
        "Esquema real de la base (PostgreSQL 16) en la última migración de Alembic: tablas, "
        "columnas, claves, restricciones, índices y disparadores. El diseño y el porqué de cada "
        "decisión están en [docs/tecnica/04-modelo-de-datos.md]"
        "(../docs/tecnica/04-modelo-de-datos.md).",
        "",
        "Para regenerarlo después de una migración (desde `backend/`, con la base migrada):",
        "",
        "```bash",
        ".venv/bin/python scripts/generar_diccionario_datos.py",
        "```",
        "",
        "**Cómo leer los diagramas.** Cada caja es una tabla con sus columnas (`PK` clave "
        "primaria, `FK` clave foránea, `UK` única; «opcional» admite `NULL`). Las líneas son "
        "claves foráneas, rotuladas con la columna: `||` exactamente uno, `|o` cero o uno, "
        "`o{` cero o muchos. Las claves de auditoría hacia `usuario` (quién creó, modificó o "
        "registró) no se dibujan para que el diagrama se lea; figuran en cada tabla.",
        "",
        "## Índice",
        "",
    ]
    for titulo, _, nombres in MODULOS:
        ancla = titulo.lower().replace(",", "").replace(" ", "-")  # como las anclas de GitHub
        enlaces = ", ".join(f"[`{n}`](#{n})" for n in nombres)
        salida.append(f"- [{titulo}](#{ancla}): {enlaces}")
    salida += ["", "## Vista general", "", "Todas las tablas y sus relaciones de dominio.", ""]
    salida += _diagrama_general(tablas)
    for titulo, descripcion, nombres in MODULOS:
        salida += ["", f"## {titulo}", "", descripcion, ""]
        salida += _diagrama(tablas, nombres)
        for nombre in nombres:
            tabla = tablas[nombre]
            salida += ["", f"### {nombre}", ""]
            if nombre in docs:
                salida += [docs[nombre], ""]
            claves_fk = {col: (ref, accion) for _, col, ref, accion in tabla.fks}
            salida += ["| Columna | Tipo | Nulo | Por defecto | Clave |", "|---|---|---|---|---|"]
            for col in tabla.columnas:
                clave = []
                if col.nombre in tabla.pk:
                    clave.append("PK")
                if col.nombre in claves_fk:
                    ref, accion = claves_fk[col.nombre]
                    clave.append(f"FK → `{ref}`" + (f" ({accion})" if accion else ""))
                if col.nombre in tabla.unica_por_columna:
                    clave.append("UNIQUE")
                salida.append(
                    f"| `{col.nombre}` | {col.tipo} | {'sí' if col.nula else 'no'} | "
                    f"{_celda(col.defecto or '')} | {', '.join(clave)} |"
                )
            compuestas = [(n, c) for n, c in tabla.unicas if len(c) > 1]
            if compuestas or tabla.checks or tabla.exclusiones:
                salida += ["", "Restricciones:", ""]
                for n, cols in compuestas:
                    salida.append(f"- `{n}`: `UNIQUE ({', '.join(cols)})`")
                for n, definicion in tabla.checks:
                    texto = f"({del_orm[n]})" if n in del_orm else definicion
                    salida.append(f"- `{n}`: `CHECK {_celda(texto)}`")
                for n, definicion in tabla.exclusiones:
                    salida.append(f"- `{n}`: `{_celda(definicion)}`")
            if tabla.indices:
                salida += ["", "Índices:", ""]
                for n, definicion in tabla.indices:
                    salida.append(f"- `{n}`: `{_celda(definicion)}`")
            if tabla.disparadores:
                salida += ["", "Disparadores:", ""]
                for n, definicion in tabla.disparadores:
                    salida.append(f"- `{n}`: {_celda(definicion)}")
    return "\n".join(salida) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true", help="falla si está desactualizado")
    args = parser.parse_args()
    contenido = generar(leer_esquema(get_settings().database_url))
    if args.verificar:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print(f"{DESTINO.relative_to(RAIZ)} está desactualizado: regenerarlo.")
            return 1
        print(f"{DESTINO.relative_to(RAIZ)} está al día.")
        return 0
    DESTINO.write_text(contenido, encoding="utf-8")
    print(f"Escrito {DESTINO.relative_to(RAIZ)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
