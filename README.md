# TPI-DAO: Sistema de Préstamos Interbibliotecarios

Trabajo práctico integrador de la materia **Desarrollo de Aplicaciones con Objetos** (UTN FRC, 2026).

Reemplaza la gestión manual de una **red de bibliotecas** organizada en sedes. Además de socios, catálogo, préstamos, devoluciones y disponibilidad, resuelve el rasgo distintivo del dominio: el **préstamo interbibliotecario**, en el que un socio pide un ejemplar que está en otra sede y el sistema gestiona su traslado con **remitos** y trazabilidad completa. Consigna en [`enunciado.md`](enunciado.md) y análisis en [`analisis-enunciado.md`](analisis-enunciado.md).

## Funcionalidades por rol

| Rol | Qué hace |
|-----|----------|
| **Administrador** | Sedes (alta, horarios, cierres, baja con verificación de actividad pendiente), usuarios del personal, catálogo de libros, parámetros del negocio (plazos, límites, montos), los seis reportes y las tareas automáticas |
| **Bibliotecario** | Opera en su sede: socios y sus cuentas, ejemplares, préstamos en el mostrador, remitos (generar, empaquetar, despachar, recibir), reservas, devoluciones, cobro de multas y reportes operativos |
| **Socio** | Consulta el catálogo y la disponibilidad, pide préstamos para sí, reserva libros, ve sus préstamos y multas, paga sus multas en línea (simulado) y descarga el comprobante |

Procesos clave: ciclo de vida del remito (patrón State), préstamo local o entre sedes elegido automáticamente (Factory), cola FIFO de reservas, multas por atraso, daño o extravío (Strategy), inhabilitación automática del socio y seis reportes (R1 a R6) exportables a CSV.

## Stack

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, APScheduler, JWT (PyJWT) con contraseñas Argon2id |
| Base de datos | PostgreSQL 16 (en Docker) |
| Frontend | React 18, Vite 5, React Router 6, TanStack Query 5 |
| Calidad | pytest, ruff, mypy; Vitest, Testing Library, MSW, ESLint, Prettier; CI en GitHub Actions |

## Estructura del repositorio

| Carpeta | Contenido |
|---------|-----------|
| [`backend/`](backend/) | API REST en capas: `models/` (dominio y patrones), `services/` (casos de uso), `repositories/`, `controllers/`, `db/` (ORM, seed) y `alembic/` (migraciones) |
| [`frontend/`](frontend/) | Aplicación React por módulos en `src/features/` |
| [`database/`](database/README.md) | Documentación de la base: diagrama entidad-relación, diccionario de datos, migraciones y operación |
| [`docs/`](docs/README.md) | Documentación de negocio, funcional y técnica |

## Cómo levantarlo con Docker (todo el sistema)

Requisito: Docker con Compose. Levanta PostgreSQL, el backend (aplica las migraciones al arrancar) y el frontend servido por nginx, que redirige `/api` al backend.

```bash
cp .env.example .env              # completar POSTGRES_PASSWORD, SECRET_KEY y SEED_PASSWORD
CARGAR_SEED=1 docker compose up -d --build   # con datos de demostración (o CARGAR_SEED=1 en .env)
docker compose ps                 # esperar los tres servicios en «healthy»
```

- Frontend: <http://localhost:8080> (`FRONTEND_PORT`). API y documentación: <http://localhost:8000/docs> (`BACKEND_PORT`).
- Sin `CARGAR_SEED=1`, el seed se carga después con `docker compose exec backend python -m app.db.seed`.
- `docker compose stop backend frontend` deja solo la base, para seguir desarrollando localmente. Si los puertos 8000 u 8080 están ocupados, cambiá `BACKEND_PORT` o `FRONTEND_PORT` en `.env`.

## Cómo levantarlo localmente (desarrollo)

Requisitos: Docker, Python 3.12 (con [uv](https://docs.astral.sh/uv/) o `venv`) y Node.js según `frontend/.nvmrc` (con nvm).

```bash
# 1. Base de datos (solo el servicio db)
cp .env.example .env            # completar POSTGRES_PASSWORD, SECRET_KEY y SEED_PASSWORD
docker compose up -d db

# 2. Backend (desde backend/)
cd backend
uv venv .venv --python 3.12 && uv pip install -e ".[dev]"   # o: python -m venv .venv && pip install -e ".[dev]"
.venv/bin/alembic upgrade head          # crea el esquema
.venv/bin/python -m app.db.seed         # datos de demostración (solo desarrollo y test)
.venv/bin/uvicorn app.main:app --reload # API en http://localhost:8000 (documentación en /docs)

# 3. Frontend (desde frontend/, en otra terminal)
cd frontend
nvm use
npm ci && npm run dev                   # http://localhost:5173
```

**Usuarios de demostración** (contraseña: el valor de `SEED_PASSWORD` del `.env`, de 10 a 128 caracteres con letras y números):

| Rol | Usuarios |
|-----|----------|
| Administrador | `admin`, `admin.operaciones` |
| Bibliotecario | `bibliotecario.cen` (Central), `bibliotecario.norte` (Norte), `bibliotecario.rc` (Río Cuarto), `bibliotecario.vm` (Villa María) |
| Socio | `socio.demo` (Carla), `martin.rios`, `camila.ferreyra`, `tomas.vera`; `diego.luna` y `ana.quiroga` están dados de baja y pueden pedir la reactivación |

El seed carga 90 días de historia: hay préstamos, remitos, reservas y multas en todos sus estados, para recorrer cada pantalla y los reportes.

### Demostración pública (solo lectura)

Para publicar el sistema y que cualquiera lo recorra sin poder modificar nada:

1. Crear desde **Usuarios** un usuario con rol Administrador (por ejemplo, `visitante`) y una contraseña propia, distinta de la de los demás usuarios: se va a mostrar en la web.
2. En el backend, `USUARIOS_SOLO_LECTURA=visitante`. Ese usuario ve todo, pero la API le rechaza cualquier alta, modificación o baja (`403 SOLO_LECTURA`), también si se la llama directamente.
3. Al compilar el frontend, `VITE_DEMO_USUARIO=visitante` y `VITE_DEMO_CLAVE=<su contraseña>`. El inicio público y el login muestran el acceso con un botón «Entrar como visitante», y dentro del sistema aparece el aviso «Modo demostración».

Sin esas variables no cambia nada.

## Pruebas y calidad

```bash
# Backend (desde backend/; las de integración usan la base <nombre>_test)
.venv/bin/pytest -m "not integration"   # rápidas, sin base
.venv/bin/pytest --cov=app              # todas
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy app/models app/services
.venv/bin/python scripts/verificar_trazabilidad_ca.py --prefijos SED,ACC,SOC,CAT,PRE,REM,RES,DEV,REP --estricto

# Frontend (desde frontend/)
npm test && npm run lint && npm run format:check && npm run build
npm run test:coverage                   # con cobertura y mínimos (lo corre CI)
```

Cada criterio de aceptación de la documentación funcional tiene al menos una prueba que lo cita; el script de trazabilidad lo verifica en CI.

## Documentación

- [`docs/README.md`](docs/README.md): índice de la documentación de negocio, funcional y técnica (arquitectura, modelo de clases, máquinas de estado, patrones de diseño, API).
- [`database/README.md`](database/README.md): base de datos.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): ramas, commits y pull requests.
- [`SECURITY.md`](SECURITY.md): reporte de vulnerabilidades.

## Licencia

[MIT](LICENSE).
