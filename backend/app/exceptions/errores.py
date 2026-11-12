"""Excepciones de negocio con código estable.

El dominio las lanza; la capa ``controllers`` las traduce a HTTP en un único lugar.
No importan nada de HTTP.
"""

from typing import Any


class ErrorDeNegocio(Exception):
    """Base de todos los errores de negocio.

    Attributes:
        codigo: Código estable que usa el frontend para decidir qué mostrar.
        mensaje: Texto en español legible por una persona.
        detalles: Lista de datos adicionales (campo, problema, elementos...).
    """

    codigo = "ERROR_DE_NEGOCIO"

    def __init__(self, mensaje: str, detalles: list[dict[str, Any]] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles: list[dict[str, Any]] = detalles or []


class EntidadNoEncontrada(ErrorDeNegocio):
    codigo = "NOT_FOUND"


class SedeNoEncontrada(EntidadNoEncontrada):
    codigo = "SEDE_NO_ENCONTRADA"


class UsuarioNoEncontrado(EntidadNoEncontrada):
    codigo = "USUARIO_NO_ENCONTRADO"


class ExcepcionHorarioNoEncontrada(EntidadNoEncontrada):
    codigo = "EXCEPCION_HORARIO_NO_ENCONTRADA"


class ReglaDeNegocioViolada(ErrorDeNegocio):
    codigo = "REGLA_DE_NEGOCIO"


class DuplicadoError(ReglaDeNegocioViolada):
    codigo = "DUPLICADO"


class SedeCodigoDuplicado(DuplicadoError):
    codigo = "SEDE_CODIGO_DUPLICADO"


class SedeNombreDuplicado(DuplicadoError):
    codigo = "SEDE_NOMBRE_DUPLICADO"


class DireccionDuplicada(DuplicadoError):
    codigo = "DIRECCION_DUPLICADA"


class SedeEnBaja(ReglaDeNegocioViolada):
    codigo = "SEDE_EN_BAJA"


class SedeYaEnBaja(ReglaDeNegocioViolada):
    codigo = "SEDE_YA_EN_BAJA"


class SedeYaActiva(ReglaDeNegocioViolada):
    codigo = "SEDE_YA_ACTIVA"


class SedeConActividadPendiente(ReglaDeNegocioViolada):
    codigo = "SEDE_CON_ACTIVIDAD_PENDIENTE"


class ConflictoDeVersion(ReglaDeNegocioViolada):
    codigo = "CONFLICTO_DE_VERSION"


class UsuarioYaEnBaja(ReglaDeNegocioViolada):
    codigo = "USUARIO_YA_EN_BAJA"


class UsuarioYaActivo(ReglaDeNegocioViolada):
    codigo = "USUARIO_YA_ACTIVO"


class ExcepcionHorarioSuperpuesta(ReglaDeNegocioViolada):
    codigo = "EXCEPCION_HORARIO_SUPERPUESTA"


# --- socios ------------------------------------------------------------------------------------


class SocioNoEncontrado(EntidadNoEncontrada):
    codigo = "SOCIO_NO_ENCONTRADO"


class PosibleDuplicado(DuplicadoError):
    """Otro socio con el mismo nombre, apellido y fecha de nacimiento: hay que confirmar."""

    codigo = "POSIBLE_DUPLICADO"


class SocioInhabilitado(ReglaDeNegocioViolada):
    codigo = "SOCIO_INHABILITADO"


class SocioEnBaja(ReglaDeNegocioViolada):
    codigo = "SOCIO_EN_BAJA"


class SocioYaEnBaja(ReglaDeNegocioViolada):
    codigo = "SOCIO_YA_EN_BAJA"


class SocioYaActivo(ReglaDeNegocioViolada):
    codigo = "SOCIO_YA_ACTIVO"


class SocioYaHabilitado(ReglaDeNegocioViolada):
    codigo = "SOCIO_YA_HABILITADO"


class SocioYaInhabilitado(ReglaDeNegocioViolada):
    codigo = "SOCIO_YA_INHABILITADO"


class SocioConCausasVigentes(ReglaDeNegocioViolada):
    codigo = "SOCIO_CON_CAUSAS_VIGENTES"


class SocioConActividadPendiente(ReglaDeNegocioViolada):
    codigo = "SOCIO_CON_ACTIVIDAD_PENDIENTE"


class SocioConCuenta(ReglaDeNegocioViolada):
    codigo = "SOCIO_CON_CUENTA"


class ErrorDeValidacion(ErrorDeNegocio):
    """Dato con forma válida pero que incumple una regla de campo (422)."""

    codigo = "VALIDACION"


class CodigoInmutable(ErrorDeValidacion):
    codigo = "CODIGO_INMUTABLE"


class LocalidadInvalida(ErrorDeValidacion):
    codigo = "LOCALIDAD_INVALIDA"


class HorarioInvalido(ErrorDeValidacion):
    codigo = "HORARIO_INVALIDO"


class ExcepcionHorarioInvalida(ErrorDeValidacion):
    codigo = "EXCEPCION_HORARIO_INVALIDA"


class PermisoDenegado(ErrorDeNegocio):
    codigo = "FORBIDDEN"


class CredencialesInvalidas(ErrorDeNegocio):
    codigo = "CREDENCIALES_INVALIDAS"


class TokenInvalido(ErrorDeNegocio):
    codigo = "TOKEN_INVALIDO"
