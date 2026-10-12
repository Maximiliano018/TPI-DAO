from fastapi import FastAPI

from biblioteca.api.errors import registrar_manejadores
from biblioteca.api.routers import (
    auth,
    catalogo,
    circulacion,
    health,
    logistica,
    organizacion,
    reportes,
)
from biblioteca.config import settings
from biblioteca.infrastructure.db.mappers import configurar_mapeos

configurar_mapeos()

app = FastAPI(title="Biblioteca - Préstamos Interbibliotecarios", version="0.1.0")

registrar_manejadores(app)

for modulo in (health, auth, organizacion, catalogo, circulacion, logistica, reportes):
    app.include_router(modulo.router, prefix=settings.api_prefix)
