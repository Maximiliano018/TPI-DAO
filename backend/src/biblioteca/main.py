from fastapi import FastAPI

from biblioteca.api.errors import registrar_manejadores
from biblioteca.api.routers import health
from biblioteca.config import settings

app = FastAPI(title="Biblioteca - Préstamos Interbibliotecarios", version="0.1.0")

registrar_manejadores(app)

app.include_router(health.router, prefix=settings.api_prefix)
