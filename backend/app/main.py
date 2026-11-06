from fastapi import FastAPI

from app.controllers import version_controller

app = FastAPI(title="Sistema de Préstamos Interbibliotecarios")
app.include_router(version_controller.router)
