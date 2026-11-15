"""Contrato de la API: cada endpoint queda documentado en OpenAPI (``/docs``).

Recorre las rutas de la aplicación y su operación en ``app.openapi()`` y exige:

* ``summary`` (título corto en español), ``description`` (el docstring del endpoint) y ``tags``.
* Una respuesta exitosa con esquema (``response_model``), salvo ``204`` o las que devuelven un
  archivo (contenido que no es JSON, como el comprobante en PDF).
* Las respuestas de error que el endpoint puede dar, documentadas:

  - ``401`` en toda ruta protegida (las que piden el token).
  - ``403`` en las que exigen con ``requiere(...)`` un permiso que algún rol no tiene. Las que
    admiten a todos los roles (por ejemplo, el catálogo) nunca responden 403 por permiso, así que
    no se les exige.
  - ``404`` en las que reciben un identificador en la ruta (``{…_id}``).
  - ``422`` en las que reciben parámetros o un cuerpo.

Si alguna falla, se completa el decorador del endpoint (``summary``, ``responses``) o su docstring.
"""

import inspect
from collections.abc import Iterable, Iterator

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from app.main import app
from app.models.usuario import ROL_PERMISOS, Permiso

ESPEC = app.openapi()


def _rutas(rutas: Iterable[BaseRoute]) -> Iterator[APIRoute]:
    """Las rutas de la API, también las de los routers incluidos (FastAPI los anida)."""
    for ruta in rutas:
        if isinstance(ruta, APIRoute):
            yield ruta
        elif (router := getattr(ruta, "original_router", None)) is not None:
            yield from _rutas(router.routes)


def _operaciones() -> Iterator[tuple[str, APIRoute, dict]]:
    for ruta in _rutas(app.routes):
        if not ruta.include_in_schema:
            continue
        for metodo in sorted(ruta.methods):
            operacion = ESPEC["paths"][ruta.path_format][metodo.lower()]
            yield f"{metodo} {ruta.path_format}", ruta, operacion


OPERACIONES = list(_operaciones())
NOMBRES = [nombre for nombre, _, _ in OPERACIONES]


def _permisos_exigidos(dependant: Dependant) -> Iterator[Permiso]:
    """Permisos que piden las dependencias ``requiere(...)`` de la ruta (también anidadas)."""
    for dependencia in dependant.dependencies:
        llamada = dependencia.call
        if getattr(llamada, "__qualname__", "").startswith("requiere."):
            yield from inspect.getclosurevars(llamada).nonlocals["permisos"]
        yield from _permisos_exigidos(dependencia)


def _puede_responder_403(ruta: APIRoute) -> bool:
    """Algún rol no tiene alguno de los permisos que exige la ruta."""
    exigidos = set(_permisos_exigidos(ruta.dependant))
    return any(not exigidos <= permisos for permisos in ROL_PERMISOS.values())


def test_la_api_tiene_endpoints_documentados():
    assert len(OPERACIONES) > 80
    # La regla del 403 se aplica de verdad: hay rutas que algún rol no puede usar.
    assert sum(_puede_responder_403(ruta) for _, ruta, _ in OPERACIONES) > 40


@pytest.mark.parametrize(("nombre", "ruta", "operacion"), OPERACIONES, ids=NOMBRES)
def test_cada_endpoint_esta_documentado(nombre, ruta, operacion):
    assert (operacion.get("summary") or "").strip(), f"{nombre}: falta summary"
    assert (operacion.get("description") or "").strip(), f"{nombre}: falta el docstring"
    assert operacion.get("tags"), f"{nombre}: falta tags"


@pytest.mark.parametrize(("nombre", "ruta", "operacion"), OPERACIONES, ids=NOMBRES)
def test_cada_respuesta_exitosa_tiene_esquema(nombre, ruta, operacion):
    exitosas = {c: r for c, r in operacion["responses"].items() if c.startswith("2")}
    assert exitosas, f"{nombre}: no documenta la respuesta exitosa"
    for codigo, respuesta in exitosas.items():
        contenido = respuesta.get("content", {})
        if codigo == "204" or (contenido and "application/json" not in contenido):
            continue  # sin cuerpo, o un archivo (PDF)
        assert contenido.get("application/json", {}).get("schema"), (
            f"{nombre}: la respuesta {codigo} no tiene response_model"
        )


@pytest.mark.parametrize(("nombre", "ruta", "operacion"), OPERACIONES, ids=NOMBRES)
def test_cada_endpoint_documenta_sus_errores(nombre, ruta, operacion):
    respuestas = operacion["responses"]
    faltan = []
    if operacion.get("security") and "401" not in respuestas:
        faltan.append("401")
    if _puede_responder_403(ruta) and "403" not in respuestas:
        faltan.append("403")
    if "{" in ruta.path_format and "404" not in respuestas:
        faltan.append("404")
    if (operacion.get("parameters") or operacion.get("requestBody")) and "422" not in respuestas:
        faltan.append("422")
    assert not faltan, f"{nombre}: faltan las respuestas {', '.join(faltan)}"
