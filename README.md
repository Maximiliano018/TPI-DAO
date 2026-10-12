# TPI-DAO
Desarrollo del trabajo práctico integrador de la materia desarrollo de aplicaciones con objetos, UTN FRC 2026

## Cómo levantar el proyecto

Requisitos: [uv](https://docs.astral.sh/uv/) (`pip install uv`) y Node.js 20+. uv descarga Python 3.12 y crea el entorno virtual solo.

### Backend (FastAPI) — terminal 1

```bash
cd backend
uv sync                                      # instala dependencias en .venv
uv run uvicorn biblioteca.main:app --reload  # http://localhost:8000/docs
```

Otros comandos:

```bash
uv run pytest                                # tests
uv run ruff check . && uv run ruff format .  # lint y formato
uv run alembic revision --autogenerate -m "mensaje"   # nueva migración
uv run alembic upgrade head                           # aplicar migraciones
uv add <paquete>                             # agregar una dependencia
```

### Frontend (React + Vite) — terminal 2

```bash
cd frontend
npm install
npm run dev                                  # http://localhost:5173
```

En desarrollo, Vite reenvía las llamadas a `/api` al backend (ver `frontend/vite.config.ts`).

La arquitectura está documentada en [ARCHITECTURE.md](ARCHITECTURE.md).
