# 01. Arquitectura del backend

## Capas

```
┌──────────────────────────────────────────────┐
│ api            Routers, esquemas, seguridad  │  recibe y responde HTTP
├──────────────────────────────────────────────┤
│ application    Servicios (casos de uso)      │  orquesta, controla transacciones
├──────────────────────────────────────────────┤
│ domain         Entidades, reglas, estados    │  lógica del negocio, sin frameworks
├──────────────────────────────────────────────┤
│ infrastructure Repositorios, ORM, relojes    │  base de datos y servicios externos
└──────────────────────────────────────────────┘
```

Regla de dependencia: cada capa solo conoce a la de abajo, y **`domain` no importa a ninguna otra**. La base de datos depende del dominio, no al revés: el dominio define las interfaces de los repositorios y `infrastructure` las implementa (inversión de dependencias).

| Capa | Responsabilidad | No debe |
|------|-----------------|---------|
| `api` | Validar la forma de la entrada (Pydantic), autenticar, autorizar por rol, traducir excepciones a HTTP | Contener reglas de negocio ni consultar la base |
| `application` | Un servicio por proceso (`PrestamoService`, `RemitoService`…). Cargar entidades, invocar al dominio, guardar, abrir y cerrar la transacción | Conocer HTTP ni SQL |
| `domain` | Entidades con comportamiento, estados, políticas, excepciones de negocio, interfaces de repositorio | Importar FastAPI, SQLAlchemy ni Pydantic |
| `infrastructure` | Modelos del ORM, repositorios, Unit of Work, scheduler, generador de números | Contener reglas de negocio |

## Estructura de carpetas

```
backend/
├── app/
│   ├── main.py                    # crea la app, registra routers y manejadores de error
│   ├── core/
│   │   ├── config.py              # configuración desde variables de entorno
│   │   ├── security.py            # hash de contraseñas, creación y lectura de JWT
│   │   └── logging.py
│   ├── api/
│   │   ├── dependencies.py        # sesión, usuario actual, control de rol
│   │   ├── errors.py              # excepción de dominio -> respuesta HTTP
│   │   ├── routers/               # sedes.py, socios.py, catalogo.py, prestamos.py, ...
│   │   └── schemas/               # modelos Pydantic de request y response
│   ├── application/
│   │   ├── services/              # sede_service.py, prestamo_service.py, ...
│   │   └── reports/               # consultas de lectura de los reportes R1-R6
│   ├── domain/
│   │   ├── entities/              # sede.py, socio.py, ejemplar.py, prestamo.py, remito.py, ...
│   │   ├── states/                # estados de remito, préstamo, ejemplar, reserva
│   │   ├── policies/              # cálculo de multa, plazos, selección de ejemplar
│   │   ├── factories/             # PrestamoFactory
│   │   ├── events.py              # eventos de dominio
│   │   ├── exceptions.py          # errores de negocio con código
│   │   └── repositories.py        # interfaces (puertos) de repositorio
│   └── infrastructure/
│       ├── db/
│       │   ├── session.py         # engine y sesión
│       │   ├── models/            # modelos SQLAlchemy
│       │   ├── mappers.py         # modelo ORM <-> entidad
│       │   ├── repositories/      # implementaciones SQLAlchemy
│       │   └── unit_of_work.py
│       ├── scheduler.py           # tareas periódicas
│       └── notifications.py       # observadores de eventos (opcional)
├── alembic/                       # migraciones
├── tests/
│   ├── unit/                      # dominio y políticas, sin base
│   ├── services/                  # casos de uso con repositorios en memoria
│   ├── integration/               # repositorios y restricciones sobre PostgreSQL
│   └── api/                       # endpoints con TestClient
├── pyproject.toml
└── Dockerfile
```

## Entidades de dominio y modelos del ORM

**Propuesta T1.** Se mantienen separadas:

- Las **entidades de dominio** son clases Python comunes con comportamiento (`prestamo.entregar(...)`, `remito.despachar(...)`). No conocen la base.
- Los **modelos del ORM** describen tablas y columnas. Los repositorios convierten entre ambos con `mappers.py`.

Ventajas: el dominio se prueba sin base ni frameworks (tests unitarios rápidos), las reglas no se mezclan con el esquema, y se evidencia la arquitectura que la cátedra evalúa. Costo: un mapeo adicional por entidad. Alternativa más corta: usar los modelos del ORM como entidades; es válida pero acopla el dominio a SQLAlchemy y complica los tests unitarios.

## Flujo de una solicitud

```
Cliente ── HTTP ──▶ Router
                     │ valida esquema, autentica y autoriza el rol
                     ▼
                  Servicio (application)
                     │ abre Unit of Work; carga entidades por repositorio
                     ▼
                  Dominio: entidad.operación()   ◀── reglas y cambio de estado
                     │ lanza excepción de negocio si una regla no se cumple
                     ▼
                  Servicio: guarda y confirma la transacción
                     │ publica eventos de dominio
                     ▼
                  Router ──▶ esquema de respuesta ──▶ Cliente
```

Ejemplo, registrar un préstamo interbibliotecario (`PrestamoService.registrar`):

1. Abre la Unit of Work y bloquea la fila del ejemplar (`FOR UPDATE`).
2. Carga socio, ejemplar y sedes por repositorio.
3. `PrestamoFactory` decide el tipo y la política de plazo, y construye el préstamo `Solicitado`.
4. Las validaciones de negocio (socio habilitado, ejemplar disponible y de la sede origen, sedes activas, tope de préstamos) se ejecutan en el dominio.
5. El ejemplar pasa a `Apartado`, el préstamo se guarda y se registra el movimiento.
6. Se confirma la transacción.

## Transacciones y concurrencia

- **Una transacción por caso de uso**, controlada por el servicio mediante la Unit of Work. Si algo falla, no queda nada a medias.
- **Bloqueo pesimista** (`SELECT ... FOR UPDATE`) sobre el ejemplar o el remito al cambiar su estado, para que dos operaciones simultáneas no apliquen la misma transición.
- **Respaldo en la base**: índices únicos parciales y restricciones `CHECK` (ver [Modelo de datos](04-modelo-de-datos.md)); si el código fallara, la base igualmente rechaza el estado inválido.
- **Versionado optimista** (`version`) en ejemplar y remito para detectar escrituras cruzadas.

## Errores

El dominio lanza excepciones propias con un código estable; la capa `api` las traduce a HTTP en un único lugar.

| Excepción (dominio) | Código de error | HTTP |
|---------------------|-----------------|------|
| `EntidadNoEncontrada` | `NOT_FOUND` | 404 |
| `ReglaDeNegocioViolada` (base de las siguientes) | según subtipo | 409 o 422 |
| `SocioInhabilitado` | `SOCIO_INHABILITADO` | 409 |
| `EjemplarNoDisponible` | `EJEMPLAR_NO_DISPONIBLE` | 409 |
| `EjemplarNoPerteneceASede` | `EJEMPLAR_FUERA_DE_SEDE_ORIGEN` | 422 |
| `SedeEnBaja` | `SEDE_EN_BAJA` | 409 |
| `LimitePrestamosExcedido` | `LIMITE_PRESTAMOS` | 409 |
| `TransicionInvalida` | `TRANSICION_INVALIDA` | 409 |
| `DuplicadoError` | `DUPLICADO` | 409 |
| `SedeConActividadPendiente` | `SEDE_CON_ACTIVIDAD_PENDIENTE` | 409 |
| `PermisoDenegado` | `FORBIDDEN` | 403 |
| `CredencialesInvalidas` | `CREDENCIALES_INVALIDAS` | 401 |
| `EjemplarEnOtroRemito` | `EJEMPLAR_EN_OTRO_REMITO` | 409 |
| `HayEjemplaresDisponibles` | `HAY_EJEMPLARES_DISPONIBLES` | 409 |
| `ReservaDuplicada` | `RESERVA_DUPLICADA` | 409 |
| `LimiteReservasExcedido` | `LIMITE_RESERVAS` | 409 |
| `HorarioInvalido` | `HORARIO_INVALIDO` | 422 |

La tabla no es exhaustiva: cada regla de negocio nueva suma su excepción y su código, y el catálogo vive en `domain/exceptions.py`. Los errores de forma (campo faltante, tipo inválido) los devuelve FastAPI con 422 y el mismo formato de respuesta. Formato en [API REST](06-api.md#errores).

## Seguridad

- Contraseñas con hash (Argon2 o bcrypt); nunca se guardan ni se registran en claro.
- JWT con vencimiento corto; el token incluye `sub`, `rol` y `sede_id`.
- Autorización por dependencia: cada endpoint declara los roles que admite. Además, el servicio verifica que el bibliotecario opere solo sobre **su** sede (`RF-ACC-04`).
- El socio accede solo a sus propios datos (`RF-ACC-05`): el filtro se aplica en el servicio, no en el cliente.
- Secretos y credenciales solo por variables de entorno; `.env` está en `.gitignore` y existe un `.env.example` sin valores reales.
- CORS restringido al origen del frontend.
- Toda escritura registra usuario y momento (`RF-ACC-07`).

## Configuración

Variables de entorno leídas con `pydantic-settings`:

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | Conexión a PostgreSQL |
| `SECRET_KEY` | Firma de los JWT |
| `ACCESS_TOKEN_MINUTES` | Duración del token |
| `CORS_ORIGINS` | Orígenes permitidos |
| `TZ_NEGOCIO` | Zona horaria para plazos (`America/Argentina/Cordoba`) |

Los parámetros de negocio (plazos, límites, monto de multa) **no** son variables de entorno sino filas de la tabla `parametro`, editables por el administrador sin redesplegar.

## Observabilidad

Registro estructurado (`logging`) con identificador de solicitud, usuario y operación. Los cambios de estado de remito, préstamo y ejemplar se registran además en sus tablas de movimientos, que son la fuente de trazabilidad y de los reportes.
