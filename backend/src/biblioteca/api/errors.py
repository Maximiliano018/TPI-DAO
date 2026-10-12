from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from biblioteca.domain.errors import DomainError, DuplicadoError, NoEncontrado, TransicionInvalida

# Excepción de dominio -> código HTTP. Lo no listado responde 422.
_STATUS_POR_ERROR: dict[type[DomainError], int] = {
    NoEncontrado: 404,
    DuplicadoError: 409,
    TransicionInvalida: 409,
}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _manejar_error_dominio(_request: Request, exc: DomainError) -> JSONResponse:
        status = next(
            (s for tipo, s in _STATUS_POR_ERROR.items() if isinstance(exc, tipo)),
            422,
        )
        return JSONResponse(
            status_code=status, content={"codigo": exc.codigo, "mensaje": exc.mensaje}
        )
