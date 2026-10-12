"""Datos iniciales y de demostración (ARCHITECTURE.md §5.5 y §5.6).

- `cargar_datos_iniciales`: parámetros del sistema y categorías. Es idempotente:
  solo agrega lo que falta y nunca pisa un valor que el ADMIN ya cambió.
- `cargar_demo`: sedes, libros, ejemplares y socios de ejemplo, para desarrollo.

El primer ADMIN se crea cuando exista el módulo de autenticación (hash argon2).
"""

from datetime import UTC, date, datetime, time
from typing import NamedTuple

from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection

from biblioteca.domain.enums import TipoParametro
from biblioteca.infrastructure.db.insercion import insertar
from biblioteca.infrastructure.db.secuencias import (
    SECUENCIA_SOCIO,
    formatear_codigo_inventario,
    secuencia_inventario,
    siguiente_valor,
)
from biblioteca.infrastructure.db.tables import (
    autor,
    categoria,
    ejemplar,
    horario_sede,
    libro,
    libro_autor,
    parametro,
    sede,
    socio,
)


class ParametroInicial(NamedTuple):
    clave: str
    valor: int
    descripcion: str


PARAMETROS_INICIALES = (
    ParametroInicial("plazo_prestamo_dias", 14, "Días de préstamo desde la entrega al socio"),
    ParametroInicial("max_prestamos_simultaneos", 3, "Préstamos abiertos permitidos por socio"),
    ParametroInicial("multa_por_dia", 50000, "Multa por día de atraso, en centavos"),
    ParametroInicial("multa_tope_dias", 30, "Máximo de días de atraso que se cobran"),
    ParametroInicial("dias_para_retiro", 3, "Días para retirar una reserva o un préstamo listo"),
    ParametroInicial("dias_max_transito", 7, "Días en tránsito antes de marcar un remito demorado"),
    ParametroInicial("dias_aviso_vencimiento", 2, "Anticipación del aviso de vencimiento"),
)

CATEGORIAS_INICIALES = (
    "Literatura argentina",
    "Literatura universal",
    "Historia",
    "Ciencias",
    "Infantil y juvenil",
    "Obras de referencia",
)


def cargar_datos_iniciales(conn: Connection) -> None:
    claves_existentes = set(conn.execute(select(parametro.c.clave)).scalars())
    for p in PARAMETROS_INICIALES:
        if p.clave not in claves_existentes:
            conn.execute(
                insert(parametro).values(
                    clave=p.clave,
                    valor=str(p.valor),
                    tipo=TipoParametro.ENTERO,
                    descripcion=p.descripcion,
                )
            )

    categorias_existentes = set(conn.execute(select(categoria.c.nombre)).scalars())
    for nombre in CATEGORIAS_INICIALES:
        if nombre not in categorias_existentes:
            conn.execute(insert(categoria).values(nombre=nombre))


# ---------------------------------------------------------------------------- Demostración


class _SedeDemo(NamedTuple):
    codigo: str
    nombre: str
    direccion: str
    # Franjas (dias, apertura, cierre); varias por día = horario cortado.
    franjas: tuple[tuple[range, time, time], ...]


class _LibroDemo(NamedTuple):
    titulo: str
    autores: tuple[str, ...]
    anio: int
    categoria: str
    # Cantidad de ejemplares por código de sede.
    ejemplares: dict[str, int]
    solo_consulta: bool = False


_LUNES_A_VIERNES = range(1, 6)
_SABADO = range(6, 7)

_SEDES_DEMO = (
    _SedeDemo(
        "CEN",
        "Sede Central",
        "Av. Colón 100",
        ((_LUNES_A_VIERNES, time(8), time(20)), (_SABADO, time(9), time(13))),
    ),
    _SedeDemo(
        "NOR",
        "Sede Norte",
        "Av. Rafael Núñez 4500",
        ((_LUNES_A_VIERNES, time(8), time(12)), (_LUNES_A_VIERNES, time(16), time(20))),
    ),
    _SedeDemo(
        "SUR", "Sede Sur", "Av. Vélez Sarsfield 3000", ((_LUNES_A_VIERNES, time(9), time(17)),)
    ),
)

_LIBROS_DEMO = (
    _LibroDemo(
        "Martín Fierro", ("José Hernández",), 1872, "Literatura argentina", {"CEN": 2, "SUR": 1}
    ),
    _LibroDemo("Facundo", ("Domingo Faustino Sarmiento",), 1845, "Historia", {"CEN": 1, "NOR": 1}),
    _LibroDemo(
        "Don Segundo Sombra", ("Ricardo Güiraldes",), 1926, "Literatura argentina", {"NOR": 1}
    ),
    _LibroDemo(
        "Ficciones",
        ("Jorge Luis Borges",),
        1944,
        "Literatura argentina",
        {"CEN": 1, "NOR": 1, "SUR": 1},
    ),
    _LibroDemo("Rayuela", ("Julio Cortázar",), 1963, "Literatura argentina", {"SUR": 2}),
    _LibroDemo(
        "Don Quijote de la Mancha",
        ("Miguel de Cervantes",),
        1605,
        "Literatura universal",
        {"CEN": 1},
    ),
    _LibroDemo(
        "El Principito", ("Antoine de Saint-Exupéry",), 1943, "Infantil y juvenil", {"NOR": 2}
    ),
    _LibroDemo(
        "Diccionario de la lengua española",
        ("Real Academia Española",),
        2014,
        "Obras de referencia",
        {"CEN": 1},
        solo_consulta=True,
    ),
)

_SOCIOS_DEMO = (
    ("30111222", "Ana", "Pérez"),
    ("31222333", "Bruno", "Gómez"),
    ("32333444", "Carla", "Díaz"),
    ("33444555", "Diego", "Romero"),
    ("34555666", "Elena", "Suárez"),
)


def isbn13_con_verificador(base_12_digitos: str) -> str:
    """Completa un ISBN-13 con su dígito verificador (pesos alternados 1 y 3)."""
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base_12_digitos))
    return base_12_digitos + str((10 - suma % 10) % 10)


def _normalizar_nombre(nombre: str) -> str:
    sin_tildes = nombre.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))
    return " ".join(sin_tildes.split())


def cargar_demo(conn: Connection) -> bool:
    """Carga datos de ejemplo. Devuelve False si la base ya tiene sedes (no hace nada)."""
    if conn.execute(select(func.count()).select_from(sede)).scalar_one() > 0:
        return False

    hoy = date.today()
    ids_sede: dict[str, int] = {}
    for s in _SEDES_DEMO:
        sede_id = insertar(
            conn, sede, codigo=s.codigo, nombre=s.nombre, direccion=s.direccion, localidad="Córdoba"
        )
        ids_sede[s.codigo] = sede_id
        for dias, apertura, cierre in s.franjas:
            for dia in dias:
                conn.execute(
                    insert(horario_sede).values(
                        sede_id=sede_id, dia_semana=dia, hora_apertura=apertura, hora_cierre=cierre
                    )
                )

    ids_categoria = {
        nombre: id_ for nombre, id_ in conn.execute(select(categoria.c.nombre, categoria.c.id))
    }
    ids_autor: dict[str, int] = {}
    for n, datos in enumerate(_LIBROS_DEMO, start=1):
        # ISBN ficticios (prefijo 978-0-00000) con dígito verificador válido.
        libro_id = insertar(
            conn,
            libro,
            isbn=isbn13_con_verificador(f"97800000{n:04d}"),
            titulo=datos.titulo,
            anio_publicacion=datos.anio,
            categoria_id=ids_categoria[datos.categoria],
        )

        for orden, nombre in enumerate(datos.autores, start=1):
            if nombre not in ids_autor:
                ids_autor[nombre] = insertar(
                    conn, autor, nombre=nombre, nombre_normalizado=_normalizar_nombre(nombre)
                )
            conn.execute(
                insert(libro_autor).values(
                    libro_id=libro_id, autor_id=ids_autor[nombre], orden=orden
                )
            )

        for codigo_sede, cantidad in datos.ejemplares.items():
            for _ in range(cantidad):
                numero = siguiente_valor(conn, secuencia_inventario(codigo_sede))
                conn.execute(
                    insert(ejemplar).values(
                        codigo_inventario=formatear_codigo_inventario(codigo_sede, numero),
                        libro_id=libro_id,
                        sede_id=ids_sede[codigo_sede],
                        prestable=not datos.solo_consulta,
                        fecha_alta=hoy,
                    )
                )

    for i, (dni, nombre, apellido) in enumerate(_SOCIOS_DEMO):
        inhabilitado = i == len(_SOCIOS_DEMO) - 1
        conn.execute(
            insert(socio).values(
                numero_socio=siguiente_valor(conn, SECUENCIA_SOCIO),
                dni=dni,
                nombre=nombre,
                apellido=apellido,
                email=f"{nombre.lower()}.{_normalizar_nombre(apellido)}@ejemplo.com",
                fecha_alta=hoy,
                habilitado=not inhabilitado,
                motivo_inhabilitacion="Ejemplo de socio sancionado" if inhabilitado else None,
                fecha_inhabilitacion=datetime.now(UTC) if inhabilitado else None,
            )
        )
    return True
