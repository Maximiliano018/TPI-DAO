# 01. Arquitectura del backend

## Capas

```
┌─────────────────────────────────────────────────────┐
│ controllers   Routers FastAPI, seguridad            │  recibe y responde HTTP
│ dtos          Request y response (Pydantic)         │  contratos de la API
├─────────────────────────────────────────────────────┤
│ services      Casos de uso                          │  orquesta, controla transacciones
├─────────────────────────────────────────────────────┤
│ models        Entidades, estados, políticas, reglas │  lógica del negocio, sin frameworks
├─────────────────────────────────────────────────────┤
│ repositories  Interfaces e implementaciones         │  acceso a datos
│ db            Engine, sesión, modelos ORM, Alembic  │  PostgreSQL
└─────────────────────────────────────────────────────┘
  Transversales: config, exceptions, utils
```

Regla de dependencia: `controllers → services → repositories → db`, y **`models` no importa a ninguna otra capa**. Los services dependen de las **interfaces** de repositorio; las implementaciones con SQLAlchemy se inyectan (inversión de dependencias). `config`, `exceptions` y `utils` no importan de las capas de negocio.

| Capa | Responsabilidad | No debe |
|------|-----------------|---------|
| `controllers` | Recibir el DTO de request, autenticar, autorizar por rol, llamar a un service y devolver un DTO de response. Traducir excepciones a HTTP | Contener reglas de negocio ni consultar la base |
| `dtos` | `request/` y `response/`: esquemas Pydantic distintos de las entidades | Contener lógica ni importar `models` |
| `services` | Un servicio por proceso (`PrestamoService`, `RemitoService`…). Cargar entidades, invocar al dominio, guardar, abrir y cerrar la transacción | Conocer HTTP ni SQL |
| `models` | Entidades con comportamiento, estados (State), políticas (Strategy) y factories | Importar FastAPI, SQLAlchemy ni Pydantic |
| `repositories` | `interfaces/` (puertos por agregado) e `impl/` (SQLAlchemy), mappers entre ORM y entidad, Unit of Work | Contener reglas de negocio |
| `db` | Engine, sesión, **modelos ORM** (tablas) y migraciones Alembic | Contener reglas de negocio |
| `config` | Variables de entorno (`settings`), seguridad (hash, JWT), logging | Importar capas de negocio |
| `exceptions` | Excepciones de negocio con código estable | Importar HTTP |
| `utils` | Funciones puras reutilizables (normalización de texto, fechas, numeración) | Tener estado ni dependencias de otras capas |

## Estructura de carpetas

```
backend/
├── app/
│   ├── main.py                    # crea la app, registra routers y manejadores de error
│   ├── config/                    # settings.py, security.py, logging.py
│   ├── controllers/               # sede_controller.py, socio_controller.py, prestamo_controller.py, ...
│   │   └── dependencies.py        # sesión, usuario actual, control de rol
│   ├── dtos/
│   │   ├── request/               # *_request.py
│   │   └── response/              # *_response.py
│   ├── services/                  # sede_service.py, prestamo_service.py, ...; reports/ (R1-R6)
│   ├── models/                    # entidades de dominio: sede.py, socio.py, ejemplar.py, prestamo.py, remito.py, ...
│   │   ├── states/                # estados de remito, préstamo, ejemplar, reserva
│   │   ├── policies/              # cálculo de multa, plazos, selección de ejemplar y sede origen
│   │   └── factories/             # PrestamoFactory
│   ├── repositories/
│   │   ├── interfaces/            # puertos por agregado (sede_repository.py, ...)
│   │   ├── impl/                  # implementaciones SQLAlchemy
│   │   ├── mappers.py             # modelo ORM <-> entidad
│   │   └── unit_of_work.py
│   ├── db/
│   │   ├── session.py             # engine y sesión
│   │   ├── models/                # modelos ORM (tablas)
│   │   └── seed.py                # datos de demostración (solo desarrollo y test)
│   ├── exceptions/                # errores de negocio con código
│   └── utils/                     # funciones puras
├── alembic/                       # migraciones
├── tests/                         # estructura completa en 07-testing-y-calidad.md
│   ├── unit/                      # models y políticas, sin base
│   ├── services/                  # casos de uso con repositorios en memoria
│   ├── integration/               # repositorios y restricciones sobre PostgreSQL
│   ├── controllers/               # endpoints con TestClient
│   ├── contract/                  # contratos entre módulos (verificadores de baja, OpenAPI)
│   ├── fakes/                     # repositorios y verificadores en memoria
│   └── factories/                 # fábricas de datos de prueba
├── pyproject.toml
└── Dockerfile
```

## Entidades de dominio y modelos del ORM

**Decisión T1 (confirmada).** Se mantienen separadas:

- Las **entidades de dominio** (`app/models/`) son clases Python comunes con comportamiento (`prestamo.entregar(...)`, `remito.despachar(...)`). No conocen la base.
- Los **modelos del ORM** (`app/db/models/`) describen tablas y columnas. Los repositorios convierten entre ambos con `mappers.py`.

Ventajas: el dominio se prueba sin base ni frameworks (tests unitarios rápidos), las reglas no se mezclan con el esquema, y se evidencia la arquitectura que la cátedra evalúa. Costo: un mapeo adicional por entidad. Alternativa más corta: usar los modelos del ORM como entidades; es válida pero acopla el dominio a SQLAlchemy y complica los tests unitarios.

## Flujo de una solicitud

```
Cliente ── HTTP ──▶ Controller (DTO request)
                     │ valida esquema, autentica y autoriza el rol
                     ▼
                  Service
                     │ abre Unit of Work; carga entidades por repositorio
                     ▼
                  Models: entidad.operación()   ◀── reglas y cambio de estado
                     │ lanza excepción de negocio si una regla no se cumple
                     ▼
                  Servicio: guarda y confirma la transacción
                     │ publica eventos de dominio
                     ▼
                  Controller ──▶ DTO response ──▶ Cliente
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

El dominio lanza excepciones propias con un código estable; la capa `controllers` las traduce a HTTP en un único lugar.

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
| `ErrorDeValidacion` (forma: tipo, largo, formato) | `VALIDACION` | 422 |
| `CredencialesInvalidas` | `CREDENCIALES_INVALIDAS` | 401 |
| `EjemplarEnOtroRemito` | `EJEMPLAR_EN_OTRO_REMITO` | 409 |
| `HayEjemplaresDisponibles` | `HAY_EJEMPLARES_DISPONIBLES` | 409 |
| `ReservaDuplicada` | `RESERVA_DUPLICADA` | 409 |
| `LimiteReservasExcedido` | `LIMITE_RESERVAS` | 409 |
| `HorarioInvalido` | `HORARIO_INVALIDO` | 422 |
| `SedeNoEncontrada` | `SEDE_NO_ENCONTRADA` | 404 |
| `SedeCodigoDuplicado` | `SEDE_CODIGO_DUPLICADO` | 409 |
| `SedeNombreDuplicado` | `SEDE_NOMBRE_DUPLICADO` | 409 |
| `DireccionDuplicada` | `DIRECCION_DUPLICADA` | 409 |
| `SedeYaEnBaja` / `SedeYaActiva` | `SEDE_YA_EN_BAJA` / `SEDE_YA_ACTIVA` | 409 |
| `CodigoInmutable` | `CODIGO_INMUTABLE` | 422 |
| `LocalidadInvalida` | `LOCALIDAD_INVALIDA` | 422 |
| `ExcepcionHorarioInvalida` | `EXCEPCION_HORARIO_INVALIDA` | 422 |
| `ExcepcionHorarioSuperpuesta` | `EXCEPCION_HORARIO_SUPERPUESTA` | 409 |
| `ConflictoDeVersion` | `CONFLICTO_DE_VERSION` | 409 |
| `TokenInvalido` | `TOKEN_INVALIDO` | 401 |
| `SocioNoEncontrado` | `SOCIO_NO_ENCONTRADO` | 404 |
| `PosibleDuplicado` | `POSIBLE_DUPLICADO` | 409 |
| `SocioEnBaja` / `SocioYaEnBaja` / `SocioYaActivo` | `SOCIO_EN_BAJA` / `SOCIO_YA_EN_BAJA` / `SOCIO_YA_ACTIVO` | 409 |
| `SocioYaHabilitado` / `SocioYaInhabilitado` | `SOCIO_YA_HABILITADO` / `SOCIO_YA_INHABILITADO` | 409 |
| `SocioConCausasVigentes` | `SOCIO_CON_CAUSAS_VIGENTES` | 409 |
| `SocioConActividadPendiente` | `SOCIO_CON_ACTIVIDAD_PENDIENTE` | 409 |
| `SocioConCuenta` | `SOCIO_CON_CUENTA` | 409 |

La tabla no es exhaustiva: cada regla de negocio nueva suma su excepción y su código, y el catálogo vive en `exceptions/`. Los errores de forma (campo faltante, tipo inválido) los devuelve FastAPI con 422 y el mismo formato de respuesta. Formato en [API REST](06-api.md#errores).

## Seguridad

- Contraseñas con hash (Argon2 o bcrypt); nunca se guardan ni se registran en claro.
- JWT con vencimiento corto (60 min); el token incluye `sub`, `rol` y `sede_id`, pero el usuario se **recarga de la base en cada solicitud** (`RF-ACC-08`, `RF-ACC-10`).
- Autorización por **permiso**: el dominio define el mapa rol → permisos (`models/permisos.py`); cada endpoint declara con `requiere(Permiso.X)` lo que exige. Además, el servicio verifica que el bibliotecario opere solo sobre **su** sede (`RF-ACC-04`) con `usuario.opera_en(sede_id)`.
- El DTO de respuesta de sede se elige según el permiso de lectura que tenga el usuario (completo, básico o público), de modo que un campo no autorizado **nunca se serializa**: no se «oculta» después.
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
| `TZ_NEGOCIO` | Zona horaria para plazos y horarios de sede (`America/Argentina/Cordoba`) |
| `ENTORNO` | `desarrollo`, `test` o `produccion`; el seed solo corre en los dos primeros |
| `SEED_PASSWORD` | Contraseña de los usuarios de demostración (solo seed) |

Los parámetros de negocio (plazos, límites, monto de multa) **no** son variables de entorno sino filas de la tabla `parametro`, editables por el administrador sin redesplegar.

## Observabilidad

Registro estructurado (`logging`) con identificador de solicitud, usuario y operación. Los cambios de estado de remito, préstamo y ejemplar se registran además en sus tablas de movimientos, que son la fuente de trazabilidad y de los reportes.
