# TPI-DAO
Desarrollo del trabajo práctico integrador de la materia desarrollo de aplicaciones con objetos, UTN FRC 2026

## Cómo levantar el proyecto

Requisitos: [uv](https://docs.astral.sh/uv/) (`pip install uv`) y Node.js 20+. uv descarga Python 3.12 y crea el entorno virtual solo.

### Backend (FastAPI) — terminal 1

```bash
cd backend
uv sync                                      # instala dependencias en .venv
uv run biblioteca crear-base --demo          # crea biblioteca.db con datos de ejemplo
uv run biblioteca crear-admin --username admin --nombre "Nombre Apellido"   # pide la contraseña
uv run uvicorn biblioteca.main:app --reload  # http://localhost:8000/docs
```

Base de datos (SQLite, archivo `backend/biblioteca.db`):

```bash
uv run biblioteca crear-base [--demo]               # migraciones + datos iniciales
uv run biblioteca seed [--demo]                     # solo datos iniciales (idempotente)
uv run biblioteca reset-base --confirmar [--demo]   # borra la base y la recrea (desarrollo)
```

Después de un `git pull` que traiga migraciones nuevas, alcanza con `uv run biblioteca crear-base`.

Para probar la API desde Swagger (`/docs`): botón **Authorize**, usuario y contraseña del ADMIN. La configuración opcional (secreto de sesión, base, zona horaria) está en `backend/.env.example`.

Otros comandos:

```bash
uv run pytest                                # tests
uv run ruff check . && uv run ruff format .  # lint y formato
uv run mypy src tests                        # tipos
uv run alembic revision --autogenerate -m "mensaje"   # nueva migración (tras cambiar tables.py)
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
