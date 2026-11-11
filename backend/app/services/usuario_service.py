"""Casos de uso de la gestión de usuarios del personal (solo administrador)."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from app.config.security import hashear_clave
from app.exceptions import DuplicadoError, SedeEnBaja, UsuarioNoEncontrado
from app.models.paginacion import Pagina
from app.models.usuario import (
    Permiso,
    Rol,
    SedeRef,
    Usuario,
    UsuarioRef,
    validar_asignacion_de_sede,
    validar_clave,
    validar_nombre_usuario,
    validar_rol_de_personal,
    validar_username,
)
from app.repositories.interfaces.usuario_repository import FiltroUsuarios
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj
from app.utils.texto import normalizar

MENSAJE_NO_ENCONTRADO = "El usuario solicitado no existe."
MENSAJE_SEDE_EN_BAJA = "La sede está dada de baja. Elija una sede activa."


@dataclass(frozen=True)
class DatosUsuarioNuevo:
    """Datos del alta de un usuario del personal."""

    username: str
    password: str
    nombre: str
    rol: Rol
    sede_id: int | None = None


class UsuarioService:
    """Alta, modificación, baja y reactivación del personal; las reglas viven en ``Usuario``."""

    def __init__(
        self,
        uow: UnitOfWork,
        reloj: Reloj,
        hashear: Callable[[str], str] = hashear_clave,
    ) -> None:
        self._uow = uow
        self._reloj = reloj
        self._hashear = hashear

    # --- escritura ------------------------------------------------------------------------

    def crear(self, actor: Usuario, datos: DatosUsuarioNuevo) -> Usuario:
        """Da de alta un administrador o un bibliotecario (este, en una sede activa).

        Orden: forma (422) → usuario repetido (409) → sede (404/409). La sede se bloquea en modo
        compartido para que no pase a ``Baja`` mientras se la asigna.

        Raises:
            PermisoDenegado: Si no es administrador.
            ErrorDeValidacion: Usuario, nombre o contraseña inválidos, rol que no es de personal,
                bibliotecario sin sede o administrador con sede.
            DuplicadoError: El nombre de usuario ya existe.
            SedeNoEncontrada, SedeEnBaja: La sede no existe o está dada de baja.
        """
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        username = validar_username(datos.username)
        nombre = validar_nombre_usuario(datos.nombre)
        clave = validar_clave(datos.password)
        validar_rol_de_personal(datos.rol)
        validar_asignacion_de_sede(datos.rol, datos.sede_id is not None)
        password_hash = self._hashear(clave)  # antes de bloquear nada: Argon2 es lento a propósito
        with self._transaccion():
            if self._uow.usuarios.obtener_por_username(username) is not None:
                raise DuplicadoError(
                    f"Ya existe el usuario {username}.",
                    [{"campo": "username", "problema": "duplicado"}],
                )
            sede = self._sede_activa(datos.sede_id) if datos.sede_id is not None else None
            usuario = Usuario.crear_personal(
                username=username,
                nombre=nombre,
                rol=datos.rol,
                sede=sede,
                password_hash=password_hash,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            self._uow.usuarios.agregar(usuario)
        return usuario

    def modificar(
        self, actor: Usuario, usuario_id: int, nombre: str, sede_id: int | None
    ) -> Usuario:
        """Cambia el nombre y, si es bibliotecario, lo reasigna a otra sede **activa**.

        El cambio rige desde la siguiente solicitud del usuario: cada solicitud recarga al
        usuario de la base (CA-ACC-08). Se puede reasignar a un usuario dado de baja, para
        poder reactivarlo cuando su sede anterior está en ``Baja``.

        Raises:
            UsuarioNoEncontrado, ErrorDeValidacion, SedeNoEncontrada, SedeEnBaja.
        """
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        with self._transaccion():
            usuario = self._para_modificar(usuario_id)
            validar_asignacion_de_sede(usuario.rol, sede_id is not None)
            sede = usuario.sede
            if sede_id is not None and sede_id != usuario.sede_id:
                sede = self._sede_activa(sede_id)
            if usuario.modificar(
                nombre=nombre, sede=sede, actor=_ref(actor), ahora=self._reloj.ahora()
            ):
                self._uow.usuarios.guardar(usuario)
        return usuario

    def dar_de_baja(self, actor: Usuario, usuario_id: int) -> Usuario:
        """Baja lógica. Se permite aunque tenga operaciones en curso: conserva el historial.

        Raises:
            UsuarioNoEncontrado, UsuarioYaEnBaja.
            ErrorDeValidacion: Si el administrador intenta darse de baja a sí mismo.
        """
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        with self._transaccion():
            usuario = self._para_modificar(usuario_id)
            usuario.dar_de_baja(actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.usuarios.guardar(usuario)
        return usuario

    def reactivar(self, actor: Usuario, usuario_id: int) -> Usuario:
        """Reactiva a un usuario; un bibliotecario exige que su sede esté activa.

        Raises:
            UsuarioNoEncontrado, UsuarioYaActivo.
            SedeEnBaja: La sede del bibliotecario está en ``Baja``: hay que reasignarlo primero.
        """
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        with self._transaccion():
            usuario = self._para_modificar(usuario_id)
            if not usuario.activo and usuario.sede_id is not None:
                self._sede_activa(usuario.sede_id)
            usuario.reactivar(actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.usuarios.guardar(usuario)
        return usuario

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, actor: Usuario, usuario_id: int) -> Usuario:
        """Detalle de un usuario del personal.

        Raises:
            UsuarioNoEncontrado: No existe o es un socio.
        """
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        usuario = self._uow.usuarios.obtener_detalle(usuario_id)
        if usuario is None or usuario.rol == Rol.SOCIO:
            raise UsuarioNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return usuario

    def listar(
        self,
        actor: Usuario,
        rol: Rol | None,
        sede_id: int | None,
        activo: bool | None,
        texto: str | None,
        page: int,
        size: int,
    ) -> Pagina[Usuario]:
        """Listado paginado del personal, ordenado por nombre."""
        actor.exigir(Permiso.USUARIO_ADMINISTRAR)
        filtro = FiltroUsuarios(
            rol=rol, sede_id=sede_id, activo=activo, texto=normalizar(texto) if texto else None
        )
        usuarios, total = self._uow.usuarios.listar(filtro, page, size)
        return Pagina(usuarios, total, page, size)

    # --- internos -------------------------------------------------------------------------

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()

    def _para_modificar(self, usuario_id: int) -> Usuario:
        usuario = self._uow.usuarios.obtener_para_modificar(usuario_id)
        if usuario is None or usuario.rol == Rol.SOCIO:
            raise UsuarioNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return usuario

    def _sede_activa(self, sede_id: int) -> SedeRef:
        """Sede activa bloqueada en modo compartido (serializa contra su baja)."""
        try:
            sede = self._uow.sedes.obtener_para_operar(sede_id)
        except SedeEnBaja as error:
            raise SedeEnBaja(
                MENSAJE_SEDE_EN_BAJA, [{"campo": "sede_id", "problema": "sede_en_baja"}]
            ) from error
        assert sede.id is not None
        return SedeRef(sede.id, sede.codigo.valor, sede.nombre)


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
