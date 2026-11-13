"""Usuario del sistema, roles y permisos.

Los roles son tres y fijos (los define el enunciado). Los permisos se resuelven en el servidor
a partir del rol: ``ROL_PERMISOS`` es la única fuente de verdad.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.exceptions import (
    ErrorDeValidacion,
    PermisoDenegado,
    UsuarioYaActivo,
    UsuarioYaEnBaja,
)

USERNAME_PATRON = re.compile(r"^[a-z0-9._-]{3,50}$")
NOMBRE_MIN, NOMBRE_MAX = 3, 100
CLAVE_MIN, CLAVE_MAX = 10, 128


def _error(campo: str, problema: str) -> ErrorDeValidacion:
    return ErrorDeValidacion(problema, [{"campo": campo, "problema": problema}])


class Rol(StrEnum):
    """Rol de un usuario."""

    ADMIN = "ADMIN"
    BIBLIOTECARIO = "BIBLIOTECARIO"
    SOCIO = "SOCIO"


class Permiso(StrEnum):
    """Capacidad concreta que un endpoint o caso de uso puede exigir."""

    SEDE_LEER_PUBLICO = "SEDE_LEER_PUBLICO"
    SEDE_LEER_BASICO = "SEDE_LEER_BASICO"
    SEDE_LEER_COMPLETO = "SEDE_LEER_COMPLETO"
    SEDE_ADMINISTRAR = "SEDE_ADMINISTRAR"
    SEDE_VER_HISTORIAL = "SEDE_VER_HISTORIAL"
    USUARIO_ADMINISTRAR = "USUARIO_ADMINISTRAR"
    SOCIO_LEER = "SOCIO_LEER"
    SOCIO_REGISTRAR = "SOCIO_REGISTRAR"
    SOCIO_ADMINISTRAR = "SOCIO_ADMINISTRAR"
    SOCIO_VER_PROPIO = "SOCIO_VER_PROPIO"
    CATALOGO_LEER = "CATALOGO_LEER"
    CATALOGO_ADMINISTRAR = "CATALOGO_ADMINISTRAR"
    EJEMPLAR_LEER = "EJEMPLAR_LEER"
    EJEMPLAR_ADMINISTRAR = "EJEMPLAR_ADMINISTRAR"
    PRESTAMO_REGISTRAR = "PRESTAMO_REGISTRAR"
    PRESTAMO_LEER = "PRESTAMO_LEER"
    PRESTAMO_VER_PROPIOS = "PRESTAMO_VER_PROPIOS"
    REMITO_OPERAR = "REMITO_OPERAR"
    REMITO_LEER = "REMITO_LEER"
    REMITO_EXTRAVIO = "REMITO_EXTRAVIO"
    TAREAS_EJECUTAR = "TAREAS_EJECUTAR"
    PARAMETROS_ADMINISTRAR = "PARAMETROS_ADMINISTRAR"
    RESERVA_REGISTRAR = "RESERVA_REGISTRAR"
    RESERVA_LEER = "RESERVA_LEER"
    RESERVA_PROPIA = "RESERVA_PROPIA"


ROL_PERMISOS: dict[Rol, frozenset[Permiso]] = {
    Rol.ADMIN: frozenset(
        {
            Permiso.SEDE_LEER_PUBLICO,
            Permiso.SEDE_LEER_BASICO,
            Permiso.SEDE_LEER_COMPLETO,
            Permiso.SEDE_ADMINISTRAR,
            Permiso.SEDE_VER_HISTORIAL,
            Permiso.USUARIO_ADMINISTRAR,
            Permiso.SOCIO_LEER,
            Permiso.SOCIO_REGISTRAR,
            Permiso.SOCIO_ADMINISTRAR,
            Permiso.CATALOGO_LEER,
            Permiso.CATALOGO_ADMINISTRAR,
            Permiso.EJEMPLAR_LEER,
            Permiso.EJEMPLAR_ADMINISTRAR,
            Permiso.PRESTAMO_LEER,
            Permiso.REMITO_LEER,
            Permiso.REMITO_EXTRAVIO,
            Permiso.TAREAS_EJECUTAR,
            Permiso.PARAMETROS_ADMINISTRAR,
            Permiso.RESERVA_LEER,
        }
    ),
    Rol.BIBLIOTECARIO: frozenset(
        {
            Permiso.SEDE_LEER_PUBLICO,
            Permiso.SEDE_LEER_BASICO,
            Permiso.SOCIO_LEER,
            Permiso.SOCIO_REGISTRAR,
            Permiso.CATALOGO_LEER,
            Permiso.EJEMPLAR_LEER,
            Permiso.EJEMPLAR_ADMINISTRAR,
            Permiso.PRESTAMO_REGISTRAR,
            Permiso.PRESTAMO_LEER,
            Permiso.REMITO_OPERAR,
            Permiso.REMITO_LEER,
            Permiso.REMITO_EXTRAVIO,
            Permiso.RESERVA_REGISTRAR,
            Permiso.RESERVA_LEER,
        }
    ),
    Rol.SOCIO: frozenset(
        {
            Permiso.SEDE_LEER_PUBLICO,
            Permiso.SOCIO_VER_PROPIO,
            Permiso.CATALOGO_LEER,
            Permiso.PRESTAMO_VER_PROPIOS,
            Permiso.RESERVA_PROPIA,
        }
    ),
}


@dataclass(frozen=True)
class SedeRef:
    """Referencia liviana a una sede (la usa el usuario para mostrar su sede)."""

    id: int
    codigo: str
    nombre: str


@dataclass(frozen=True)
class UsuarioRef:
    """Quién realizó una operación (id y nombre para mostrar)."""

    id: int
    nombre: str


def validar_username(texto: str) -> str:
    """Usuario en minúsculas: 3 a 50 caracteres entre ``a-z``, ``0-9``, ``.``, ``_`` y ``-``."""
    valor = (texto or "").strip().lower()
    if not USERNAME_PATRON.match(valor):
        raise _error(
            "username",
            "El usuario debe tener de 3 a 50 caracteres: letras, números, punto o guiones.",
        )
    return valor


def validar_nombre_usuario(texto: str) -> str:
    """Nombre para mostrar de 3 a 100 caracteres, sin espacios de más."""
    valor = " ".join((texto or "").split())
    if not NOMBRE_MIN <= len(valor) <= NOMBRE_MAX:
        raise _error("nombre", "El nombre debe tener entre 3 y 100 caracteres.")
    return valor


def validar_clave(texto: str) -> str:
    """Contraseña de 10 a 128 caracteres con al menos una letra y un número."""
    texto = texto or ""
    if not CLAVE_MIN <= len(texto) <= CLAVE_MAX:
        raise _error("password", "La contraseña debe tener entre 10 y 128 caracteres.")
    if not (re.search(r"[A-Za-z]", texto) and re.search(r"\d", texto)):
        raise _error("password", "La contraseña debe incluir al menos una letra y un número.")
    return texto


ROLES_DE_PERSONAL = frozenset({Rol.ADMIN, Rol.BIBLIOTECARIO})


def validar_rol_de_personal(rol: Rol) -> None:
    """Solo se gestionan administradores y bibliotecarios (los socios llegan con su alta)."""
    if rol not in ROLES_DE_PERSONAL:
        raise _error("rol", "El rol debe ser ADMIN o BIBLIOTECARIO.")


def validar_asignacion_de_sede(rol: Rol, tiene_sede: bool) -> None:
    """Un bibliotecario necesita sede y el administrador no puede tenerla."""
    if rol == Rol.BIBLIOTECARIO and not tiene_sede:
        raise _error("sede_id", "Un bibliotecario debe estar asignado a una sede.")
    if rol == Rol.ADMIN and tiene_sede:
        raise _error("sede_id", "El administrador no pertenece a ninguna sede.")


@dataclass
class Usuario:
    """Usuario autenticable. ``sede`` solo corresponde al bibliotecario."""

    id: int | None
    username: str
    nombre: str
    rol: Rol
    activo: bool = True
    sede: SedeRef | None = None
    socio_id: int | None = None
    password_hash: str = ""
    creado_en: datetime | None = None
    creado_por: UsuarioRef | None = None
    actualizado_en: datetime | None = None
    actualizado_por: UsuarioRef | None = None

    @property
    def sede_id(self) -> int | None:
        """Id de la sede asignada (``None`` para administradores y socios)."""
        return self.sede.id if self.sede else None

    @property
    def permisos(self) -> frozenset[Permiso]:
        """Permisos que le da su rol."""
        return ROL_PERMISOS[self.rol]

    def puede(self, permiso: Permiso) -> bool:
        """Indica si el usuario tiene el permiso."""
        return permiso in self.permisos

    def exigir(self, permiso: Permiso) -> None:
        """Lanza ``PermisoDenegado`` si el usuario no tiene el permiso."""
        if not self.puede(permiso):
            raise PermisoDenegado("No tiene permiso para realizar esta operación.")

    def opera_en(self, sede_id: int) -> bool:
        """Un bibliotecario opera solo en su sede; el administrador no opera por sede."""
        return self.rol == Rol.BIBLIOTECARIO and self.sede_id == sede_id

    # --- gestión del personal -------------------------------------------------------------

    @classmethod
    def crear_personal(
        cls,
        *,
        username: str,
        nombre: str,
        rol: Rol,
        sede: SedeRef | None,
        password_hash: str,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Usuario":
        """Crea un usuario del personal (administrador o bibliotecario) activo.

        ``sede`` debe ser una sede **activa** (lo garantiza el servicio al resolverla).

        Raises:
            ErrorDeValidacion: Rol que no es de personal, usuario o nombre inválidos, o la
                combinación rol-sede incorrecta.
        """
        validar_rol_de_personal(rol)
        validar_asignacion_de_sede(rol, sede is not None)
        return cls(
            id=None,
            username=validar_username(username),
            nombre=validar_nombre_usuario(nombre),
            rol=rol,
            activo=True,
            sede=sede,
            password_hash=password_hash,
            creado_en=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )

    @classmethod
    def crear_cuenta_socio(
        cls,
        *,
        username: str,
        nombre: str,
        socio_id: int,
        password_hash: str,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Usuario":
        """Crea la cuenta de acceso (rol ``SOCIO``) de un socio ya registrado.

        Raises:
            ErrorDeValidacion: Usuario o nombre inválidos.
        """
        return cls(
            id=None,
            username=validar_username(username),
            nombre=validar_nombre_usuario(nombre),
            rol=Rol.SOCIO,
            activo=True,
            socio_id=socio_id,
            password_hash=password_hash,
            creado_en=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )

    def modificar(
        self, *, nombre: str, sede: SedeRef | None, actor: UsuarioRef, ahora: datetime
    ) -> bool:
        """Cambia el nombre y, para un bibliotecario, la sede. El rol y el usuario no cambian.

        Returns:
            ``True`` si algo cambió.

        Raises:
            ErrorDeValidacion: Nombre inválido o combinación rol-sede incorrecta.
        """
        nuevo_nombre = validar_nombre_usuario(nombre)
        validar_asignacion_de_sede(self.rol, sede is not None)
        if (nuevo_nombre, sede) == (self.nombre, self.sede):
            return False
        self.nombre, self.sede = nuevo_nombre, sede
        self._registrar_cambio(actor, ahora)
        return True

    def dar_de_baja(self, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Baja lógica: conserva el historial y deja de contar como asignado a su sede.

        Raises:
            ErrorDeValidacion: Si el usuario intenta darse de baja a sí mismo.
            UsuarioYaEnBaja: Si ya estaba dado de baja.
        """
        if self.id == actor.id:
            raise _error("id", "No puede darse de baja a sí mismo.")
        if not self.activo:
            raise UsuarioYaEnBaja(f"El usuario {self.username} ya está dado de baja.")
        self.activo = False
        self._registrar_cambio(actor, ahora)

    def reactivar(self, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Vuelve a activar al usuario (el servicio verifica antes que su sede esté activa).

        Raises:
            UsuarioYaActivo: Si ya estaba activo.
        """
        if self.activo:
            raise UsuarioYaActivo(f"El usuario {self.username} ya está activo.")
        self.activo = True
        self._registrar_cambio(actor, ahora)

    def _registrar_cambio(self, actor: UsuarioRef, ahora: datetime) -> None:
        self.actualizado_en = ahora
        self.actualizado_por = actor
