"""Traducción de excepciones a respuestas HTTP con el formato único de error."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    CredencialesInvalidas,
    EntidadNoEncontrada,
    ErrorDeNegocio,
    ErrorDeValidacion,
    PermisoDenegado,
    ReglaDeNegocioViolada,
    TokenInvalido,
)

logger = logging.getLogger(__name__)

_ESTADOS_POR_TIPO: list[tuple[type[ErrorDeNegocio], int]] = [
    (EntidadNoEncontrada, 404),
    (ErrorDeValidacion, 422),
    (ReglaDeNegocioViolada, 409),
    (PermisoDenegado, 403),
    (CredencialesInvalidas, 401),
    (TokenInvalido, 401),
]


def estado_http(error: ErrorDeNegocio) -> int:
    """Estado HTTP que corresponde a un error de negocio."""
    for tipo, estado in _ESTADOS_POR_TIPO:
        if isinstance(error, tipo):
            return estado
    return 400


def cuerpo_error(codigo: str, mensaje: str, detalles: list[dict[str, Any]] | None = None) -> dict:
    """Cuerpo estándar de toda respuesta de error."""
    return {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or []}}


def registrar_manejadores(app: FastAPI) -> None:
    """Registra los manejadores de error de la aplicación."""

    @app.exception_handler(ErrorDeNegocio)
    async def _negocio(_: Request, error: ErrorDeNegocio) -> JSONResponse:
        return JSONResponse(
            status_code=estado_http(error),
            content=cuerpo_error(error.codigo, error.mensaje, error.detalles),
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        detalles = []
        for e in error.errors():
            campo = ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path"))
            problema = str(e["msg"]).removeprefix("Value error, ")
            detalles.append({"campo": campo, "problema": problema})
        return JSONResponse(
            status_code=422,
            content=cuerpo_error("VALIDACION", "Hay datos inválidos en la solicitud.", detalles),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        codigo = "NOT_FOUND" if error.status_code == 404 else f"HTTP_{error.status_code}"
        return JSONResponse(
            status_code=error.status_code,
            content=cuerpo_error(codigo, str(error.detail)),
        )

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Error inesperado", exc_info=error)
        return JSONResponse(
            status_code=500,
            content=cuerpo_error("ERROR_INTERNO", "Ocurrió un error inesperado."),
        )
