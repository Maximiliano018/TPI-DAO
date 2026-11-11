"""Repositorio de usuarios sobre SQLAlchemy."""

from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import UsuarioORM
from app.exceptions import DuplicadoError
from app.models.usuario import ROLES_DE_PERSONAL, Rol, SedeRef, Usuario, UsuarioRef
from app.repositories.impl.consultas import nombres_de_usuarios, sin_tildes
from app.repositories.interfaces.usuario_repository import FiltroUsuarios


def a_dominio(orm: UsuarioORM, nombres: dict[int, str] | None = None) -> Usuario:
    """Convierte la fila ORM en la entidad de dominio.

    Con ``nombres`` completa quién creó y modificó al usuario (solo la gestión del personal lo
    necesita; el camino de autenticación no).
    """
    sede = SedeRef(orm.sede.id, orm.sede.codigo, orm.sede.nombre) if orm.sede else None

    def ref(usuario_id: int | None) -> UsuarioRef | None:
        if nombres is None or usuario_id is None:
            return None
        return UsuarioRef(usuario_id, nombres.get(usuario_id, "Usuario eliminado"))

    return Usuario(
        id=orm.id,
        username=orm.username,
        nombre=orm.nombre,
        rol=Rol(orm.rol),
        activo=orm.activo,
        sede=sede,
        socio_id=orm.socio_id,
        password_hash=orm.password_hash,
        creado_en=orm.creado_en,
        creado_por=ref(orm.creado_por_id),
        actualizado_en=orm.actualizado_en,
        actualizado_por=ref(orm.actualizado_por_id),
    )


def _auditores(filas: list[UsuarioORM]) -> set[int]:
    ids: set[int] = set()
    for fila in filas:
        ids.update(i for i in (fila.creado_por_id, fila.actualizado_por_id) if i is not None)
    return ids


class SqlAlchemyUsuarioRepository:
    """Implementa ``UsuarioRepository`` con SQLAlchemy."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, usuario_id: int) -> Usuario | None:
        orm = self._sesion.get(UsuarioORM, usuario_id)
        return a_dominio(orm) if orm else None

    def obtener_por_username(self, username: str) -> Usuario | None:
        orm = self._sesion.scalar(select(UsuarioORM).where(UsuarioORM.username == username))
        return a_dominio(orm) if orm else None

    def obtener_detalle(self, usuario_id: int) -> Usuario | None:
        return self._con_auditoria(select(UsuarioORM).where(UsuarioORM.id == usuario_id))

    def obtener_para_modificar(self, usuario_id: int) -> Usuario | None:
        consulta = (
            select(UsuarioORM)
            .where(UsuarioORM.id == usuario_id)
            .with_for_update(of=UsuarioORM)
            .execution_options(populate_existing=True)
        )
        return self._con_auditoria(consulta)

    def listar(self, filtro: FiltroUsuarios, page: int, size: int) -> tuple[list[Usuario], int]:
        condiciones = self._condiciones(filtro)
        total = self._sesion.scalar(select(func.count(UsuarioORM.id)).where(*condiciones))
        filas = list(
            self._sesion.scalars(
                select(UsuarioORM)
                .where(*condiciones)
                .order_by(sin_tildes(UsuarioORM.nombre).collate("C"), UsuarioORM.id)
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return self._mapear(filas), total or 0

    def bibliotecarios_activos_de_sede(
        self, sede_id: int, limite: int
    ) -> tuple[list[Usuario], int]:
        condiciones = [
            UsuarioORM.rol == Rol.BIBLIOTECARIO.value,
            UsuarioORM.activo.is_(True),
            UsuarioORM.sede_id == sede_id,
        ]
        total = self._sesion.scalar(select(func.count(UsuarioORM.id)).where(*condiciones))
        filas = list(
            self._sesion.scalars(
                select(UsuarioORM).where(*condiciones).order_by(UsuarioORM.username).limit(limite)
            )
        )
        return [a_dominio(f) for f in filas], total or 0

    # --- escritura ------------------------------------------------------------------------

    def agregar(self, usuario: Usuario) -> None:
        orm = UsuarioORM(
            username=usuario.username,
            password_hash=usuario.password_hash,
            nombre=usuario.nombre,
            rol=usuario.rol.value,
            sede_id=usuario.sede_id,
            socio_id=usuario.socio_id,
            activo=usuario.activo,
            creado_en=usuario.creado_en,
            creado_por_id=usuario.creado_por.id if usuario.creado_por else None,
            actualizado_en=usuario.actualizado_en,
            actualizado_por_id=usuario.actualizado_por.id if usuario.actualizado_por else None,
        )
        self._persistir(lambda: self._sesion.add(orm))
        usuario.id = orm.id

    def guardar(self, usuario: Usuario) -> None:
        assert usuario.id is not None
        orm = self._sesion.get(UsuarioORM, usuario.id)
        assert orm is not None
        orm.nombre = usuario.nombre
        orm.sede_id = usuario.sede_id
        orm.activo = usuario.activo
        if usuario.actualizado_en is not None:
            orm.actualizado_en = usuario.actualizado_en
        orm.actualizado_por_id = usuario.actualizado_por.id if usuario.actualizado_por else None
        self._persistir(lambda: None)

    # --- internos -------------------------------------------------------------------------

    def _persistir(self, preparar: Any) -> None:
        """Escribe dentro de un savepoint y traduce el nombre de usuario repetido."""
        try:
            with self._sesion.begin_nested():
                preparar()
                self._sesion.flush()
        except IntegrityError as error:
            restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if restriccion != "uq_usuario_username":
                raise
            raise DuplicadoError(
                "Ya existe un usuario con ese nombre de usuario.",
                [{"campo": "username", "problema": "duplicado"}],
            ) from error

    def _con_auditoria(self, consulta: Any) -> Usuario | None:
        orm = self._sesion.scalars(consulta).first()
        if orm is None:
            return None
        return self._mapear([orm])[0]

    def _mapear(self, filas: list[UsuarioORM]) -> list[Usuario]:
        nombres = nombres_de_usuarios(self._sesion, _auditores(filas))
        return [a_dominio(f, nombres) for f in filas]

    @staticmethod
    def _condiciones(filtro: FiltroUsuarios) -> list[ColumnElement[bool]]:
        roles = [filtro.rol] if filtro.rol else sorted(ROLES_DE_PERSONAL)
        condiciones: list[ColumnElement[bool]] = [UsuarioORM.rol.in_([r.value for r in roles])]
        if filtro.sede_id is not None:
            condiciones.append(UsuarioORM.sede_id == filtro.sede_id)
        if filtro.activo is not None:
            condiciones.append(UsuarioORM.activo.is_(filtro.activo))
        if filtro.texto:
            condiciones.append(
                sin_tildes(UsuarioORM.nombre).contains(filtro.texto, autoescape=True)
                | UsuarioORM.username.contains(filtro.texto, autoescape=True)
            )
        return condiciones
