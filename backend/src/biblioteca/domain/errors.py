class DomainError(Exception):
    """Base de todas las excepciones de negocio.

    Cada subclase define un `codigo` estable que la API devuelve al front.
    """

    codigo = "ERROR_DOMINIO"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(DomainError):
    codigo = "NO_ENCONTRADO"


class DuplicadoError(DomainError):
    codigo = "DUPLICADO"


class TransicionInvalida(DomainError):
    codigo = "TRANSICION_INVALIDA"


class DatoInvalido(DomainError):
    codigo = "DATO_INVALIDO"


class IsbnInvalido(DatoInvalido):
    codigo = "ISBN_INVALIDO"


class ConflictoDeConcurrencia(DomainError):
    codigo = "CONFLICTO_DE_CONCURRENCIA"


# ----------------------------------------------------------------- Autenticación y permisos


class CredencialesInvalidas(DomainError):
    codigo = "CREDENCIALES_INVALIDAS"


class NoAutenticado(DomainError):
    codigo = "NO_AUTENTICADO"


class AccesoDenegado(DomainError):
    codigo = "ACCESO_DENEGADO"


# ---------------------------------------------------------------------------- Catálogo


class LibroConHistorial(DomainError):
    """El libro tiene ejemplares o reservas: no se borra para no perder su historial."""

    codigo = "LIBRO_CON_HISTORIAL"


# ------------------------------------------------------------------------------- Sedes


class SedeDadaDeBaja(DomainError):
    codigo = "SEDE_DADA_DE_BAJA"


class SedeConActividadAbierta(DomainError):
    codigo = "SEDE_CON_ACTIVIDAD_ABIERTA"
