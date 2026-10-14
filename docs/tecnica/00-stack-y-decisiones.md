# 00. Stack y decisiones

## Resumen

| Capa | Tecnología | Motivo principal |
|------|------------|------------------|
| API | Python 3.12 + FastAPI | Tipado, validación automática y documentación OpenAPI integrada |
| Validación y esquemas | Pydantic v2 | Contratos de request y response claros y verificables |
| Persistencia | SQLAlchemy 2.0 + Alembic | ORM estándar de Python y migraciones versionadas |
| Base de datos | PostgreSQL 16 | Restricciones, índices parciales y bloqueo de filas |
| Tests de base | SQLite en memoria | Rápidos y sin instalación (ver límites abajo) |
| Frontend | React 18 + JavaScript + Vite | Ecosistema amplio y arranque rápido |
| Calidad Python | pytest, ruff, mypy | Estándar actual del ecosistema |
| Calidad JS | Vitest, React Testing Library, ESLint, Prettier | Pruebas de componentes y estilo consistente |
| Entrega | docker-compose | Una sola orden levanta todo el sistema |

## Decisiones y justificación

### D1. PostgreSQL como base de datos

El dominio exige no prestar un ejemplar que ya está prestado, aunque dos bibliotecarios lo intenten a la vez. PostgreSQL ofrece lo necesario para garantizarlo en la base y no solo en el código:

- **Índices únicos parciales**, por ejemplo un solo préstamo abierto por ejemplar (`UNIQUE (ejemplar_id) WHERE estado IN (...)`).
- **Bloqueo de filas** (`SELECT ... FOR UPDATE`) al cambiar el estado de un ejemplar o remito.
- **Restricciones `CHECK`** para reglas como «origen igual a destino solo en préstamos locales».
- **Tipos precisos** para fechas con zona horaria y montos (`NUMERIC`).

Alternativa considerada: SQLite. Es más simple de entregar, pero no bloquea filas ni ofrece la misma garantía bajo concurrencia. Se usa **solo en los tests unitarios y de servicios**, no en producción. Los tests de repositorios y de concurrencia corren contra PostgreSQL (servicio en CI y `docker-compose` local), porque algunas restricciones se comportan distinto.

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

### D6. Autenticación

JWT de corta duración con usuario y contraseña (hash con Argon2 o bcrypt), rol en el token y autorización por dependencia en cada endpoint. Alcanza para los tres roles definidos en negocio y es verificable en tests.

### D7. Tareas periódicas

Dos procesos deben correr solos: marcar préstamos vencidos y vencer reservas no retiradas. Se resuelven con **APScheduler** dentro del proceso del backend (una tarea al día más una ejecución al iniciar), y las mismas funciones se pueden invocar desde un endpoint administrativo o desde tests. No se agrega una cola de mensajes porque no hace falta a esta escala.

### D8. Zona horaria y dinero

- Las marcas de tiempo se guardan en UTC con zona (`TIMESTAMPTZ`).
- Los plazos se calculan en días calendario de la zona `America/Argentina/Cordoba`.
- Los montos usan `Decimal` en Python y `NUMERIC(10,2)` en la base; nunca `float`.

## Alternativas descartadas

| Alternativa | Por qué no |
|-------------|------------|
| Django | Es más pesado y su ORM empuja la lógica a los modelos; el enunciado pide una arquitectura en capas explícita |
| MongoDB | El dominio es relacional y exige integridad referencial y restricciones |
| TypeScript en el frontend | El frontend se hace en JavaScript |
| Redux | El estado del servidor lo maneja TanStack Query y el resto es local; Redux agrega código sin beneficio |
| Celery y Redis | Excesivo para dos tareas diarias |

## Estructura del repositorio

```
TPI-DAO/
├── backend/            # API en Python (ver arquitectura)
├── frontend/           # Aplicación React
├── docs/               # Esta documentación
├── docker-compose.yml  # Base de datos, backend y frontend
└── .github/            # Workflows y plantillas
```

## Entrega del trabajo práctico

1. `docker compose up` levanta PostgreSQL, aplica las migraciones, carga datos de ejemplo y expone backend (puerto 8000) y frontend (puerto 5173).
2. La documentación interactiva de la API queda en `/docs`.
3. Los datos de ejemplo incluyen sedes, socios, libros, ejemplares y usuarios de cada rol para demostrar los flujos sin cargar nada a mano.
4. El README raíz explica la instalación con Docker y también sin Docker.
