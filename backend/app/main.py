from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.controllers import auth_controller, version_controller
from app.controllers.manejo_errores import registrar_manejadores


def crear_app() -> FastAPI:
    """Crea la aplicación, registra routers, CORS y manejadores de error."""
    settings = get_settings()
    settings.validar_clave_secreta()
    app = FastAPI(title="Sistema de Préstamos Interbibliotecarios")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origenes_cors,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_manejadores(app)
    app.include_router(version_controller.router)
    app.include_router(auth_controller.router)
    return app


app = crear_app()
