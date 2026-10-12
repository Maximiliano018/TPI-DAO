"""Traducción de errores a HTTP con un cuerpo uniforme `{codigo, mensaje, detalle?}`."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from biblioteca.domain.errors import (
    AccesoDenegado,
    ConflictoDeConcurrencia,
    CredencialesInvalidas,
    DomainError,
    DuplicadoError,
    LibroConHistorial,
    NoAutenticado,
    NoEncontrado,
    SedeConActividadAbierta,
    SedeDadaDeBaja,
    TransicionInvalida,
)

logger = logging.getLogger(__name__)

# Excepción de dominio -> código HTTP. Lo no listado responde 422.
_STATUS_POR_ERROR: dict[type[DomainError], int] = {
    CredencialesInvalidas: 401,
    NoAutenticado: 401,
    AccesoDenegado: 403,
    NoEncontrado: 404,
    DuplicadoError: 409,
    TransicionInvalida: 409,
    ConflictoDeConcurrencia: 409,
    LibroConHistorial: 409,
    SedeConActividadAbierta: 409,
    SedeDadaDeBaja: 409,
}


def _respuesta(
    status: int, codigo: str, mensaje: str, detalle: object | None = None
) -> JSONResponse:
    cuerpo: dict[str, object] = {"codigo": codigo, "mensaje": mensaje}
    if detalle is not None:
        cuerpo["detalle"] = detalle
    # 401 indica al cliente cómo autenticarse (RFC 7235).
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(status_code=status, content=jsonable_encoder(cuerpo), headers=headers)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _manejar_error_dominio(_request: Request, exc: DomainError) -> JSONResponse:
        status = next(
            (s for tipo, s in _STATUS_POR_ERROR.items() if isinstance(exc, tipo)),
            422,
        )
        return _respuesta(status, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """Datos con forma inválida (campo faltante, tipo incorrecto): mismo formato de error."""
        errores = exc.errors()
        primero = errores[0] if errores else {}
        campo = ".".join(str(p) for p in primero.get("loc", ()) if p != "body")
        mensaje = f"{campo}: {primero.get('msg', 'dato inválido')}" if campo else "Datos inválidos"
        return _respuesta(
            422,
            "DATOS_INVALIDOS",
            mensaje,
            [{"campo": e.get("loc"), "mensaje": e.get("msg")} for e in errores],
        )

    @app.exception_handler(IntegrityError)
    async def _manejar_integridad(_request: Request, exc: IntegrityError) -> JSONResponse:
        # Red de seguridad: el dominio debería haberlo evitado antes. Se registra para
        # detectar la validación que falta, pero no se expone el SQL al cliente.
        logger.warning("Restricción de la base violada: %s", exc.orig)
        return _respuesta(
            409, "CONFLICTO_DE_DATOS", "La operación entra en conflicto con datos existentes"
        )
