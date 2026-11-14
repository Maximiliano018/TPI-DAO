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


class SocioNoReactivable(ReglaDeNegocioViolada):
    """La baja por fallecimiento es definitiva."""

    codigo = "SOCIO_NO_REACTIVABLE"


class SolicitudYaPendiente(ReglaDeNegocioViolada):
    codigo = "SOLICITUD_YA_PENDIENTE"


class SinSolicitudPendiente(ReglaDeNegocioViolada):
    codigo = "SIN_SOLICITUD_PENDIENTE"


# --- catálogo y estados ------------------------------------------------------------------------


class TransicionInvalida(ReglaDeNegocioViolada):
    """Operación que el estado actual de la entidad no admite (patrón State)."""

    codigo = "TRANSICION_INVALIDA"


class LibroNoEncontrado(EntidadNoEncontrada):
    codigo = "LIBRO_NO_ENCONTRADO"


class EjemplarNoEncontrado(EntidadNoEncontrada):
    codigo = "EJEMPLAR_NO_ENCONTRADO"


class LibroDuplicado(DuplicadoError):
    codigo = "LIBRO_DUPLICADO"


class EjemplarCodigoDuplicado(DuplicadoError):
    codigo = "EJEMPLAR_CODIGO_DUPLICADO"


class LibroConEjemplares(ReglaDeNegocioViolada):
    codigo = "LIBRO_CON_EJEMPLARES"


class EjemplarNoDisponible(ReglaDeNegocioViolada):
    codigo = "EJEMPLAR_NO_DISPONIBLE"


# --- préstamos y remitos ---------------------------------------------------------------------


class PrestamoNoEncontrado(EntidadNoEncontrada):
    codigo = "PRESTAMO_NO_ENCONTRADO"


class RemitoNoEncontrado(EntidadNoEncontrada):
    codigo = "REMITO_NO_ENCONTRADO"


class LimitePrestamosExcedido(ReglaDeNegocioViolada):
    codigo = "LIMITE_PRESTAMOS"


class LibroYaPrestado(ReglaDeNegocioViolada):
    codigo = "LIBRO_REPETIDO"


class RenovacionNoPermitida(ReglaDeNegocioViolada):
    codigo = "RENOVACION_NO_PERMITIDA"


class EjemplarEnOtroRemito(ReglaDeNegocioViolada):
    codigo = "EJEMPLAR_EN_OTRO_REMITO"


class EjemplarNoRecibido(ReglaDeNegocioViolada):
    """El préstamo interbibliotecario todavía no llegó a la sede destino."""

    codigo = "EJEMPLAR_NO_RECIBIDO"


class PlazoDeTransitoVigente(ReglaDeNegocioViolada):
    codigo = "PLAZO_DE_TRANSITO_VIGENTE"


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


class CategoriaInvalida(ErrorDeValidacion):
    codigo = "CATEGORIA_INVALIDA"


class EjemplarNoPerteneceASede(ErrorDeValidacion):
    codigo = "EJEMPLAR_FUERA_DE_SEDE_ORIGEN"


class RemitoInvalido(ErrorDeValidacion):
    """Líneas o sedes de un remito que no cumplen las reglas de armado."""

    codigo = "REMITO_INVALIDO"


# --- reservas -----------------------------------------------------------------------------------


class ReservaNoEncontrada(EntidadNoEncontrada):
    codigo = "RESERVA_NO_ENCONTRADA"


class HayEjemplaresDisponibles(ReglaDeNegocioViolada):
    codigo = "HAY_EJEMPLARES_DISPONIBLES"


class ReservaDuplicada(ReglaDeNegocioViolada):
    codigo = "RESERVA_DUPLICADA"


class LimiteReservasExcedido(ReglaDeNegocioViolada):
    codigo = "LIMITE_RESERVAS"


class LibroSinEjemplares(ReglaDeNegocioViolada):
    codigo = "LIBRO_SIN_EJEMPLARES"


# --- devoluciones y multas ----------------------------------------------------------------------


class MultaNoEncontrada(EntidadNoEncontrada):
    codigo = "MULTA_NO_ENCONTRADA"
