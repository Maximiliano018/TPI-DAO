# 00. Stack y decisiones

## Resumen

| Capa | Tecnología | Motivo principal |
|------|------------|------------------|
| API | Python 3.12 + FastAPI | Tipado, validación automática y documentación OpenAPI integrada |
| Validación y esquemas | Pydantic v2 | Contratos de request y response claros y verificables |
| Persistencia | SQLAlchemy 2.0 + Alembic | ORM estándar de Python y migraciones versionadas |
| Base de datos | PostgreSQL 16 | Restricciones, índices parciales y bloqueo de filas |
| Tests | Repositorios en memoria + PostgreSQL | Sin SQLite: ver [Testing](07-testing-y-calidad.md) |
| Frontend | React 18 + JavaScript + Vite | Ecosistema amplio y arranque rápido |
| Calidad Python | pytest, ruff, mypy | Estándar actual del ecosistema |
| Calidad JS | Vitest, React Testing Library, ESLint, Prettier | Pruebas de componentes y estilo consistente |
| Entrega | docker-compose con base, backend y frontend | `docker compose up -d --build` levanta todo (frontend servido por nginx con proxy a la API); para desarrollar, solo `db` y los comandos de `CLAUDE.md` |

## Decisiones y justificación

### D1. PostgreSQL como base de datos

El dominio exige no prestar un ejemplar que ya está prestado, aunque dos bibliotecarios lo intenten a la vez. PostgreSQL ofrece lo necesario para garantizarlo en la base y no solo en el código:

- **Índices únicos parciales**, por ejemplo un solo préstamo abierto por ejemplar (`UNIQUE (ejemplar_id) WHERE estado IN (...)`).
- **Bloqueo de filas** (`SELECT ... FOR UPDATE`) al cambiar el estado de un ejemplar o remito.
- **Restricciones `CHECK`** para reglas como «origen igual a destino solo en préstamos locales».
- **Tipos precisos** para fechas con zona horaria y montos (`NUMERIC`).

Alternativa considerada: SQLite. Es más simple de entregar, pero no bloquea filas ni ofrece la misma garantía bajo concurrencia. **No se usa SQLite en ningún caso**: las exclusiones de horarios (`btree_gist`), los índices parciales y el bloqueo de filas no existen o se comportan distinto. Los tests unitarios y de servicios usan repositorios en memoria (no tocan base) y todo lo que toca la base corre contra PostgreSQL (servicio en CI y `docker-compose` local).

### D2. FastAPI

- Documentación OpenAPI y Swagger UI generadas del código, que cubren el requisito de documentar endpoints con request y response.
- Inyección de dependencias nativa, útil para repositorios, sesión y usuario autenticado.
- Validación de entrada y salida con Pydantic.

### D3. SQLAlchemy 2.0 y Alembic

- SQLAlchemy 2.0 con tipado (`Mapped[...]`) y sesión por solicitud.
- Alembic versiona el esquema: cada cambio de modelo es una migración revisable en el PR.
- La base se elige con la variable `DATABASE_URL`, sin cambiar código.

### D4. Arquitectura en capas

Las reglas viven en el dominio y no en la interfaz, como pide el enunciado. Detalle en [Arquitectura del backend](01-arquitectura-backend.md).

### D5. React con JavaScript

- JavaScript, sin TypeScript. Se compensa con JSDoc en funciones y componentes compartidos, ESLint estricto y validación de formularios con esquemas.
- Vite para desarrollo y empaquetado.
- Detalle en [Frontend](09-frontend.md).

### D6. Autenticación y permisos

| Aspecto | Decisión |
|---------|----------|
| Credenciales | Usuario y contraseña. Hash **Argon2id** (`argon2-cffi`); nunca se guarda ni registra la contraseña |
| Token | JWT firmado HS256 (`PyJWT`) con `sub` (id de usuario), `rol`, `sede_id`, `iat` y `exp`. Duración 60 minutos (`ACCESS_TOKEN_MINUTES`). Sin refresh token en esta etapa |
| Clave de firma | `SECRET_KEY` por variable de entorno, de al menos 32 caracteres; la aplicación **no arranca** con el valor de ejemplo |
| Verificación | En cada solicitud se valida el token y se **recarga el usuario** de la base: un usuario dado de baja, reasignado o con otro rol queda reflejado de inmediato. Los datos del token son informativos |
| Roles | `ADMIN`, `BIBLIOTECARIO`, `SOCIO`: tres roles **fijos** (enunciado), definidos en código y no administrables |
| Permisos | Enumeración `Permiso` (`SEDE_LEER_PUBLICO`, `SEDE_LEER_BASICO`, `SEDE_LEER_COMPLETO`, `SEDE_ADMINISTRAR`, `SEDE_VER_HISTORIAL`, `USUARIO_ADMINISTRAR`…) y un mapa rol → permisos en el dominio. Se descartó una tabla de permisos en base: sin roles dinámicos no aporta, y el mapa en código se prueba y se versiona |
| Autorización | Dependencia `requiere(Permiso.X)` en cada endpoint, más la regla de sede del bibliotecario en el servicio |
| Login | Mensaje único `CREDENCIALES_INVALIDAS`; se verifica un hash ficticio si el usuario no existe, para no revelar cuál dato falló por tiempo de respuesta |
| Fuera de alcance | Refresh token, bloqueo por intentos fallidos, recuperación de contraseña, doble factor |

### D7. Tareas periódicas

Tres procesos deben correr solos: marcar préstamos vencidos (e inhabilitar al socio), cancelar los préstamos solicitados que no se retiraron a tiempo y vencer las reservas no retiradas. Se resuelven con **APScheduler** dentro del proceso del backend: todos los días a las 00:05 en la zona de negocio y una vez al iniciar. Las mismas funciones se invocan desde un endpoint administrativo o desde las pruebas. No se agrega una cola de mensajes porque no hace falta a esta escala.

Implementación: `app/tareas.py` arranca el programador en el ciclo de vida de FastAPI (salvo con `ENTORNO=test`) y cada tarea usa su propia sesión y transacción; el administrador las ejecuta a mano con `POST /admin/tareas/...`.

### D8. Zona horaria y dinero

- Las marcas de tiempo se guardan en UTC con zona (`TIMESTAMPTZ`).
- Los plazos se calculan en días calendario de la zona `America/Argentina/Cordoba`.
- Los montos usan `Decimal` en Python y `NUMERIC(10,2)` en la base; nunca `float`.

### D9. Verificación de baja de sede mediante un puerto

La baja de una sede consulta datos de otros procesos (usuarios, ejemplares, préstamos, remitos, reservas), que se construyeron después que las sedes. Para no acoplar `SedeService` a ellos, el dominio define un **puerto** y cada módulo aporta su propia verificación; hoy están los seis verificadores (`services/verificadores_baja_sede.py`). Detalle y patrón en [Patrones de diseño](05-patrones-de-diseno.md#4-strategy--composite-verificación-de-baja-de-sede).

### D10. Catálogo geográfico como tabla de referencia

Provincias y localidades son tablas de referencia cargadas por migración, no texto libre ni enumerados en código: la lista cerrada se puede ampliar sin cambiar la aplicación, y la sede guarda una clave foránea a la localidad.

### D11. Dependencias

| Capa | Paquetes | Uso |
|------|----------|-----|
| Backend | `fastapi`, `uvicorn`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]` 3, `pydantic-settings`, `email-validator`, `argon2-cffi`, `PyJWT`, `APScheduler` | API, persistencia, migraciones, configuración, validación de correo, hash, token y tareas periódicas |
| Backend (desarrollo) | `pytest`, `pytest-cov`, `httpx`, `ruff`, `mypy`, `factory-boy`, `freezegun` | Pruebas, cobertura, cliente de pruebas, estilo, tipos y datos de prueba (`freezegun` está instalado pero las pruebas usan el reloj inyectable) |
| Frontend | `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `react-hook-form`, `zod`, `@hookform/resolvers`, `date-fns` | Interfaz, rutas, datos del servidor, formularios y validación, fechas |
| Frontend (desarrollo) | `msw`, `jest-axe`, `@testing-library/user-event`, `@vitest/coverage-v8` | API simulada, accesibilidad, interacción, cobertura |
| Contenedores | `python:3.12-slim`, `node:20-alpine` (compilación), `nginx:1.27-alpine`, `postgres:16` | Imágenes de backend, frontend y base |

Las versiones se fijan en `pyproject.toml` y `package.json`. Dependabot (`.github/dependabot.yml`) propone cada semana actualizaciones de `pip`, `npm`, las imágenes de los `Dockerfile` y las GitHub Actions; las menores y los parches de `pip` y `npm` llegan agrupadas en un solo PR.

### D12. Pago en línea de multas simulado

El pago en línea del socio es una simulación (checkout del propio sistema en tres pasos; la tarjeta de prueba terminada en `0002` simula un rechazo), sin pasarela externa ni dependencias nuevas: alcanza para demostrar el flujo y no exige cuentas ni credenciales. Ver [12. Pago de multas](12-pago-de-multas.md).

## Alternativas descartadas

| Alternativa | Por qué no |
|-------------|------------|
| Django | Es más pesado y su ORM empuja la lógica a los modelos; el enunciado pide una arquitectura en capas explícita |
| MongoDB | El dominio es relacional y exige integridad referencial y restricciones |
| TypeScript en el frontend | El frontend se hace en JavaScript |
| Redux | El estado del servidor lo maneja TanStack Query y el resto es local; Redux agrega código sin beneficio |
| Celery y Redis | Excesivo para tres tareas diarias |
| SQLite para tests | No soporta exclusiones, índices parciales ni bloqueo de filas |
| Tabla de permisos y roles en base | Los roles son fijos; sumaría complejidad sin necesidad |
| Sesiones con cookies | Se eligió JWT con cabecera `Authorization` para simplificar CORS y pruebas |

## Estructura del repositorio

```
TPI-DAO/
├── backend/            # API en Python (ver arquitectura)
├── frontend/           # Aplicación React
├── docs/               # Esta documentación
├── database/           # Documentación de la base, diccionario de datos y script de init
├── docker-compose.yml  # Base (PostgreSQL 16), backend y frontend
└── .github/            # Workflows y plantillas
```

## Entrega del trabajo práctico

1. `CARGAR_SEED=1 docker compose up -d --build` levanta el sistema completo: PostgreSQL, el backend (`backend/Dockerfile`: aplica `alembic upgrade head` al arrancar y, con `CARGAR_SEED=1`, el seed) y el frontend (`frontend/Dockerfile`: compila con Vite y lo sirve nginx en el puerto 8080, con `/api` redirigido al backend). Para desarrollar, `docker compose up -d db` y los comandos de [`CLAUDE.md`](../../CLAUDE.md).
2. La documentación interactiva de la API queda en `http://localhost:8000/docs`.
3. Los datos de ejemplo incluyen sedes, socios, libros, ejemplares, usuarios de cada rol y 45 días de actividad, para demostrar los flujos y los reportes sin cargar nada a mano ([seed](04-modelo-de-datos.md#seed-de-demostración)).
4. La instalación paso a paso está en el [README raíz](../../README.md) y la de la base en [`database/README.md`](../../database/README.md).
