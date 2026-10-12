class DomainError(Exception):
    """Base de todas las excepciones de negocio.

    Cada subclase define un `codigo` estable que la API devuelve al front.
    """

    codigo = "ERROR_DOMINIO"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class DatoInvalido(DomainError):
    codigo = "DATO_INVALIDO"


class NoEncontrado(DomainError):
    codigo = "NO_ENCONTRADO"


class DuplicadoError(DomainError):
    codigo = "DUPLICADO"


class TransicionInvalida(DomainError):
    codigo = "TRANSICION_INVALIDA"


class ConflictoDeConcurrencia(DomainError):
    codigo = "CONFLICTO_DE_CONCURRENCIA"


class CredencialesInvalidas(DomainError):
    codigo = "CREDENCIALES_INVALIDAS"


class NoAutenticado(DomainError):
    codigo = "NO_AUTENTICADO"


class AccesoDenegado(DomainError):
    codigo = "ACCESO_DENEGADO"


class SedeDadaDeBaja(DomainError):
    codigo = "SEDE_DADA_DE_BAJA"


class SedeConActividadAbierta(DomainError):
    codigo = "SEDE_CON_ACTIVIDAD_ABIERTA"
