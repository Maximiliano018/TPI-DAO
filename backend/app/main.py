from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.controllers import (
    auth_controller,
    catalogo_controller,
    devolucion_controller,
    pago_controller,
    prestamo_controller,
    publico_controller,
    remito_controller,
    reporte_controller,
    reserva_controller,
    sede_controller,
    socio_controller,
    usuario_controller,
    version_controller,
)
from app.controllers.manejo_errores import registrar_manejadores
from app.tareas import iniciar_programador
from app.utils.registro import configurar_registro, registrar_solicitud


def crear_app() -> FastAPI:
    """Crea la aplicación: registro, routers, CORS, manejadores de error y el middleware que da
    a cada solicitud su identificador (``X-Request-ID``) y una línea de log."""
    settings = get_settings()
    settings.validar_clave_secreta()
    configurar_registro(settings.log_level)

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        """Arranca las tareas periódicas (vencimientos) y las detiene al cerrar."""
        programador = iniciar_programador(settings)
        yield
        if programador is not None:
            programador.shutdown(wait=False)

    app = FastAPI(title="Sistema de Préstamos Interbibliotecarios", lifespan=ciclo_de_vida)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origenes_cors,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(registrar_solicitud)
    registrar_manejadores(app)
    app.include_router(version_controller.router)
    app.include_router(auth_controller.router)
    app.include_router(sede_controller.router)
    app.include_router(usuario_controller.router)
    app.include_router(socio_controller.router)
    app.include_router(catalogo_controller.router)
    app.include_router(prestamo_controller.router)
    app.include_router(remito_controller.router)
    app.include_router(reserva_controller.router)
    app.include_router(devolucion_controller.router)
    app.include_router(pago_controller.router)
    app.include_router(reporte_controller.router)
    app.include_router(publico_controller.router)
    return app


app = crear_app()
