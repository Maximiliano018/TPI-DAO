from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from biblioteca.domain.errors import (
    DomainError,
    DuplicadoError,
    LibroConHistorial,
    NoEncontrado,
    TransicionInvalida,
)

# Excepción de dominio -> código HTTP. Lo no listado responde 422.
_STATUS_POR_ERROR: dict[type[DomainError], int] = {
    NoEncontrado: 404,
    DuplicadoError: 409,
    TransicionInvalida: 409,
    LibroConHistorial: 409,
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

    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """Datos con forma inválida (campo faltante, tipo incorrecto): mismo formato de error."""
        errores = exc.errors()
        primero = errores[0] if errores else {}
        campo = ".".join(str(p) for p in primero.get("loc", ()) if p != "body")
        mensaje = f"{campo}: {primero.get('msg', 'dato inválido')}" if campo else "Datos inválidos"
        return JSONResponse(
            status_code=422,
            content={
                "codigo": "DATOS_INVALIDOS",
                "mensaje": mensaje,
                "detalle": [{"campo": e.get("loc"), "mensaje": e.get("msg")} for e in errores],
            },
        )
