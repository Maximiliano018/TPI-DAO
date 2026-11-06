# backend

API en Python 3.12 con FastAPI, SQLAlchemy 2 y Alembic, organizada en capas.
Estructura y reglas en [docs/tecnica/01-arquitectura-backend.md](../docs/tecnica/01-arquitectura-backend.md).

## Estructura

`app/` se organiza en `controllers`, `dtos` (`request` y `response`), `services`, `models` (dominio), `repositories`, `db`, `config`, `exceptions` y `utils`. Las carpetas están creadas vacías; se completan con cada módulo.

Pendiente: `main.py`, `pyproject.toml` y configuración de herramientas.
