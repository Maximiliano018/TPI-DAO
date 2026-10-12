from fastapi import FastAPI

from biblioteca.api.errors import registrar_manejadores
from biblioteca.api.routers import auth, health, sedes
from biblioteca.config import settings
from biblioteca.infrastructure.db.mappers import configurar_mapeos

configurar_mapeos()

app = FastAPI(title="Biblioteca - Préstamos Interbibliotecarios", version="0.1.0")

registrar_manejadores(app)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(sedes.router, prefix=settings.api_prefix)
