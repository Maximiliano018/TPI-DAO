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
