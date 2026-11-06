# backend

API en Python 3.12 con FastAPI, SQLAlchemy 2 y Alembic, organizada en capas.
Estructura y reglas en [docs/tecnica/01-arquitectura-backend.md](../docs/tecnica/01-arquitectura-backend.md).

## Estructura

`app/` se organiza en `controllers`, `dtos` (`request` y `response`), `services`, `models` (dominio), `repositories`, `db`, `config`, `exceptions` y `utils`. Las carpetas están creadas vacías; se completan con cada módulo.

Pendiente: mypy, conexión a la base y Alembic.

## Comandos

Requiere Python 3.12 o superior.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload   # http://localhost:8000 (documentación en /docs)
pytest
ruff check .
```

`GET /api/version` devuelve el estado y la versión del backend; el frontend lo muestra en `/version`.
