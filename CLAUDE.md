# Instrucciones para agentes

Proyecto: **TPI-DAO**, Sistema de Préstamos Interbibliotecarios (UTN FRC 2026). Contexto en `enunciado.md` y `analisis-enunciado.md`.

## Reglas
- Responder y documentar en **español**.
- Seguir `CONTRIBUTING.md`: ramas con prefijo, commits convencionales, PR contra `main`.
- Nunca pushear a `main`; siempre rama propia y PR (en borrador si no está terminado).
- No commitear secretos ni archivos `.env`.
- Cambios pequeños y enfocados; no reformatear archivos no relacionados.
- Respetar el alcance definido en `analisis-enunciado.md`; ante dudas, preguntar antes de ampliar.

## Comandos

Stack: backend Python 3.12 + FastAPI + SQLAlchemy/Alembic; frontend React + Vite; PostgreSQL 16. Detalle en `docs/tecnica/`.

**Base de datos** (necesita `.env` copiado de `.env.example`):
```bash
docker compose up -d db
```

**Backend** (desde `backend/`; el venv no se commitea):
```bash
uv venv .venv --python 3.12 && uv pip install -e ".[dev]"   # o: python -m venv .venv && pip install -e ".[dev]"
.venv/bin/alembic upgrade head          # migraciones
.venv/bin/python -m app.db.seed         # datos de demostración (solo desarrollo/test)
.venv/bin/uvicorn app.main:app --reload # API en :8000, documentación en /docs
.venv/bin/pytest -m "not integration"   # pruebas rápidas, sin base
.venv/bin/pytest --cov=app              # todas (PostgreSQL con la base `<nombre>_test`)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy app/models app/services
.venv/bin/python scripts/verificar_trazabilidad_ca.py --prefijos SED,ACC,SOC,CAT,PRE,REM,RES,DEV,REP --estricto
```

**Frontend** (desde `frontend/`; Node según `.nvmrc`, ver instrucciones globales de nvm):
```bash
npm ci && npm run dev      # :5173
npm test && npm run lint && npm run format:check && npm run build
```
