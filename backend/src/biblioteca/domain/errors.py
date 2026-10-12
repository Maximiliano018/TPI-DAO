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


class LibroConHistorial(DomainError):
    """El libro tiene ejemplares o reservas: no se borra para no perder su historial."""

    codigo = "LIBRO_CON_HISTORIAL"
