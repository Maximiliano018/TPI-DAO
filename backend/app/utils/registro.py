"""Registro (logging) estructurado con un identificador por solicitud.

* Cada solicitud HTTP tiene un **identificador** (``X-Request-ID``): se toma el que manda el
  cliente (si es razonable) o se genera uno (uuid4), y se devuelve en la respuesta.
* El identificador vive en un ``ContextVar`` durante la solicitud, y ``FiltroDeSolicitud`` lo
  agrega a **cada línea de log** que se emita mientras tanto (también desde los servicios, los
  manejadores de error o el hilo donde corre un endpoint sincrónico).
* Al terminar, el middleware deja una línea por solicitud con método, ruta, estado, duración y el
  usuario autenticado (solo su id: ni datos personales ni tokens).

Formato: ``2026-11-15 18:04:12,345 INFO app.solicitud [3f2a…] GET /api/v1/libros 200 12.4 ms
usuario=7``.
"""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response

ENCABEZADO = "X-Request-ID"
SIN_SOLICITUD = "-"
FORMATO = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
# Un identificador ajeno se acepta solo si es corto y sin caracteres raros (evita inyectar
# texto en los logs).
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

id_de_solicitud: ContextVar[str] = ContextVar("id_de_solicitud", default=SIN_SOLICITUD)
logger = logging.getLogger("app.solicitud")


class FiltroDeSolicitud(logging.Filter):
    """Agrega ``request_id`` (el de la solicitud en curso, o ``-``) a cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = id_de_solicitud.get()
        return True


def configurar_registro(nivel: str = "INFO") -> None:
    """Configura el logger ``app`` con el formato que incluye el identificador de solicitud.

    Es idempotente (no duplica el handler si la aplicación se crea más de una vez) y no toca los
    loggers de uvicorn. Los registros siguen propagándose a la raíz, así las pruebas los capturan.
    """
    raiz_app = logging.getLogger("app")
    raiz_app.setLevel(nivel.upper())
    if any(getattr(h, "_registro_tpi", False) for h in raiz_app.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(FORMATO))
    handler.addFilter(FiltroDeSolicitud())
    handler._registro_tpi = True  # type: ignore[attr-defined]
    raiz_app.addHandler(handler)


def _identificador(request: Request) -> str:
    recibido = request.headers.get(ENCABEZADO, "")
    return recibido if _ID_VALIDO.match(recibido) else uuid.uuid4().hex


async def registrar_solicitud(
    request: Request, siguiente: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware HTTP: identificador de solicitud y una línea de log por solicitud."""
    rid = _identificador(request)
    token = id_de_solicitud.set(rid)
    inicio = time.perf_counter()
    estado = 500
    try:
        respuesta = await siguiente(request)
        estado = respuesta.status_code
        respuesta.headers[ENCABEZADO] = rid
        return respuesta
    finally:
        duracion = (time.perf_counter() - inicio) * 1000
        usuario = getattr(request.state, "usuario_id", None)
        logger.info(
            "%s %s %s %.1f ms usuario=%s",
            request.method,
            request.url.path,
            estado,
            duracion,
            usuario if usuario is not None else "-",
            extra={"request_id": rid},
        )
        id_de_solicitud.reset(token)
