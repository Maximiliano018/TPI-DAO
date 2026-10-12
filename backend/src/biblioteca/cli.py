"""Comandos de administración de la base de datos.

Uso (desde backend/):
    uv run biblioteca crear-base           # migraciones + datos iniciales
    uv run biblioteca seed [--demo]        # datos iniciales (y de ejemplo)
    uv run biblioteca reset-base --confirmar [--demo]   # solo desarrollo, borra la base SQLite
    uv run biblioteca crear-admin --username admin --nombre "Nombre Apellido"
"""

import argparse
import getpass
import os
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from biblioteca.application.services.usuario_service import UsuarioService
from biblioteca.config import settings
from biblioteca.domain.errors import DomainError
from biblioteca.infrastructure.db.migraciones import aplicar_migraciones
from biblioteca.infrastructure.db.seed import cargar_datos_iniciales, cargar_demo
from biblioteca.infrastructure.db.session import SessionLocal, engine
from biblioteca.infrastructure.security import HasherArgon2
from biblioteca.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

# Para scripts y CI: si está definida, crear-admin no pide la contraseña por consola.
VARIABLE_CONTRASENA_ADMIN = "BIBLIOTECA_ADMIN_PASSWORD"


def _seed(demo: bool) -> None:
    if not inspect(engine).has_table("parametro"):
        raise SystemExit(
            "La base no tiene el esquema creado. Ejecutar primero: biblioteca crear-base"
        )
    with engine.begin() as conn:
        cargar_datos_iniciales(conn)
        print("Datos iniciales cargados (parámetros y categorías).")
        if demo:
            if cargar_demo(conn):
                print("Datos de demostración cargados.")
            else:
                print("La base ya tiene sedes: no se cargaron datos de demostración.")


def _crear_base(demo: bool) -> None:
    aplicar_migraciones()
    print(f"Esquema actualizado en {settings.database_url}")
    _seed(demo)


def _reset_base(confirmar: bool, demo: bool) -> None:
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise SystemExit("reset-base solo funciona con una base SQLite en archivo.")
    if not confirmar:
        raise SystemExit(f"Esto borra {url.database}. Repetir con --confirmar.")

    engine.dispose()
    archivo = Path(url.database)
    for ruta in (archivo, Path(f"{archivo}-wal"), Path(f"{archivo}-shm")):
        ruta.unlink(missing_ok=True)
    print(f"Base {archivo} eliminada.")
    _crear_base(demo)


def _pedir_contrasena() -> str:
    if contrasena := os.environ.get(VARIABLE_CONTRASENA_ADMIN):
        return contrasena
    contrasena = getpass.getpass("Contraseña: ")
    if contrasena != getpass.getpass("Repetir contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    return contrasena


def _crear_admin(username: str, nombre: str) -> None:
    if not inspect(engine).has_table("usuario"):
        raise SystemExit(
            "La base no tiene el esquema creado. Ejecutar primero: biblioteca crear-base"
        )
    servicio = UsuarioService(SqlAlchemyUnitOfWork(SessionLocal), HasherArgon2())
    try:
        usuario = servicio.registrar_admin(username, nombre, _pedir_contrasena())
    except DomainError as error:
        raise SystemExit(error.mensaje) from error
    print(f"Usuario ADMIN '{usuario.username}' creado.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="biblioteca", description=__doc__.splitlines()[0])
    comandos = parser.add_subparsers(dest="comando", required=True)

    crear = comandos.add_parser("crear-base", help="Aplica migraciones y carga datos iniciales")
    crear.add_argument("--demo", action="store_true", help="Carga también datos de ejemplo")

    seed = comandos.add_parser("seed", help="Carga datos iniciales (idempotente)")
    seed.add_argument("--demo", action="store_true", help="Carga también datos de ejemplo")

    reset = comandos.add_parser("reset-base", help="Borra la base SQLite y la vuelve a crear")
    reset.add_argument("--confirmar", action="store_true", help="Confirma el borrado")
    reset.add_argument("--demo", action="store_true", help="Carga también datos de ejemplo")

    admin = comandos.add_parser("crear-admin", help="Crea un usuario ADMIN")
    admin.add_argument("--username", required=True)
    admin.add_argument("--nombre", required=True, help="Nombre completo")

    args = parser.parse_args()
    if args.comando == "crear-base":
        _crear_base(args.demo)
    elif args.comando == "seed":
        _seed(args.demo)
    elif args.comando == "reset-base":
        _reset_base(args.confirmar, args.demo)
    elif args.comando == "crear-admin":
        _crear_admin(args.username, args.nombre)


if __name__ == "__main__":
    main()
