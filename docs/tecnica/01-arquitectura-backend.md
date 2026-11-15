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

**Excepción deliberada: los reportes.** `services/reports/reporte_service.py` consulta los modelos del ORM directamente con una `Session` (SQL agregado con `GROUP BY`, solo lectura): no devuelve entidades de dominio y pasar por repositorios no agregaría nada (ver [Patrones](05-patrones-de-diseno.md#5-repository-y-data-mapper)).

| Capa | Responsabilidad | No debe |
|------|-----------------|---------|
| `controllers` | Recibir el DTO de request, autenticar, autorizar por rol, llamar a un service y devolver un DTO de response. Traducir excepciones a HTTP | Contener reglas de negocio ni consultar la base |
| `dtos` | `request/` y `response/`: esquemas Pydantic distintos de las entidades | Contener lógica ni importar `models` |
| `services` | Un servicio por proceso (`PrestamoService`, `RemitoService`…). Cargar entidades, invocar al dominio, guardar, abrir y cerrar la transacción | Conocer HTTP ni SQL (salvo los reportes, ver arriba) |
| `models` | Entidades con comportamiento, estados (State), políticas (Strategy) y factories | Importar FastAPI, SQLAlchemy ni Pydantic |
| `repositories` | `interfaces/` (puertos por agregado) e `impl/` (SQLAlchemy, con el mapeo entre ORM y entidad dentro de cada repositorio), Unit of Work | Contener reglas de negocio |
| `db` | Engine, sesión, **modelos ORM** (tablas) y migraciones Alembic | Contener reglas de negocio |
| `config` | Variables de entorno (`settings.py`) y seguridad (`security.py`: hash y JWT) | Importar capas de negocio |
| `exceptions` | Excepciones de negocio con código estable | Importar HTTP |
| `utils` | Utilidades sin reglas de negocio: normalización de texto (`texto.py`), reloj inyectable (`reloj.py`), generador de PDF (`pdf.py`) y versión (`version.py`) | Depender de otras capas |

## Estructura de carpetas

```
backend/
├── app/
│   ├── main.py                    # crea la app, registra routers, CORS, manejadores de error y el programador
│   ├── tareas.py                  # tareas periódicas (APScheduler): vencidos, retiros y reservas vencidas
│   ├── config/                    # settings.py, security.py
│   ├── controllers/               # un router por módulo (sede, socio, usuario, catalogo, prestamo, remito,
│   │   │                          #   reserva, devolucion, pago, reporte, auth, version)
│   │   ├── dependencies.py        # raíz de composición: sesión, Unit of Work, servicios, usuario actual, permisos
│   │   └── manejo_errores.py      # excepciones de negocio → HTTP
│   ├── dtos/
│   │   ├── request/               # *_request.py
│   │   └── response/              # *_response.py (esquemas por rol) y autoria.py
│   ├── services/                  # un servicio por proceso: sede, socio, usuario, auth, catalogo, prestamo,
│   │   │                          #   remito, reserva, devolucion, pago, parametro
│   │   ├── cola_reservas.py       # asigna un ejemplar liberado a la cola de reservas
│   │   ├── situacion_socio.py     # reevalúa la habilitación del socio
│   │   ├── comprobante_pago.py    # arma el comprobante PDF de un pago
│   │   ├── verificadores_baja_sede.py  # estrategias de impedimentos de baja de sede
│   │   └── reports/               # R1 a R6 (reporte_service.py, resultados.py)
│   ├── models/                    # entidades de dominio: sede.py, socio.py, libro.py, ejemplar.py, prestamo.py,
│   │   │                          #   remito.py, reserva.py, devolucion.py, pago.py, incidencia.py, ...
│   │   ├── states/                # estados de remito, préstamo, ejemplar, reserva
│   │   ├── policies/              # plazos, multas, elección de sede origen, verificación de baja de sede
│   │   └── factories/             # PrestamoFactory
│   ├── repositories/
│   │   ├── interfaces/            # puertos por agregado (Protocol)
│   │   ├── impl/                  # implementaciones SQLAlchemy (con el mapeo ORM <-> entidad)
│   │   └── unit_of_work.py
│   ├── db/
│   │   ├── base.py                # Base declarativa y convención de nombres de restricciones
│   │   ├── session.py             # engine y sesión
│   │   ├── models/                # modelos ORM (tablas)
│   │   ├── seed.py                # datos de demostración (solo desarrollo y test)
│   │   ├── seed_demo.py           # reloj de demostración y servicios para el seed
│   │   └── seed_historia.py       # 90 días de historia contados con los casos de uso
│   ├── exceptions/                # errores de negocio con código
│   └── utils/                     # texto, reloj, pdf, version
├── alembic/                       # migraciones (0000 a 0017)
├── scripts/                       # trazabilidad de criterios y diccionario de datos
├── tests/                         # estructura completa en 07-testing-y-calidad.md
│   ├── unit/                      # models y políticas, sin base
│   ├── services/                  # casos de uso con repositorios en memoria
│   ├── integration/               # repositorios y restricciones sobre PostgreSQL
│   ├── controllers/               # endpoints con TestClient
│   ├── contract/                  # contrato de los verificadores de baja de sede
│   ├── fakes/                     # repositorios, reloj y verificadores en memoria
│   └── factories/                 # fábricas de datos de prueba
└── pyproject.toml
```

## Entidades de dominio y modelos del ORM

**Decisión T1 (confirmada).** Se mantienen separadas:

- Las **entidades de dominio** (`app/models/`) son clases Python comunes con comportamiento (`prestamo.entregar(...)`, `remito.despachar(...)`). No conocen la base.
- Los **modelos del ORM** (`app/db/models/`) describen tablas y columnas. Cada repositorio convierte entre ambos con sus funciones de mapeo (por ejemplo, `_multa_a_dominio` en `repositories/impl/devolucion_repository.py`).

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
                     │ el repositorio guarda los movimientos pendientes de la entidad (historial)
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
- **Bloqueo pesimista** (`SELECT ... FOR UPDATE`) sobre la entidad que cambia de estado (ejemplar, préstamo, remito, reserva, multa, pago, socio), para que dos operaciones simultáneas no apliquen la misma transición; `FOR SHARE` sobre la sede que se usa como origen o destino, y `SKIP LOCKED` al elegir un ejemplar disponible.
- **Respaldo en la base**: índices únicos parciales y restricciones `CHECK` (ver [Modelo de datos](04-modelo-de-datos.md)); si el código fallara, la base igualmente rechaza el estado inválido.
- **Versionado optimista** (`version`) en sede, libro y ejemplar: la edición manda la versión leída y, si cambió, responde `409 CONFLICTO_DE_VERSION`. El remito también tiene `version`, que cuenta sus transiciones.

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
| `LibroNoEncontrado` / `EjemplarNoEncontrado` | `LIBRO_NO_ENCONTRADO` / `EJEMPLAR_NO_ENCONTRADO` | 404 |
| `LibroDuplicado` / `EjemplarCodigoDuplicado` | `LIBRO_DUPLICADO` / `EJEMPLAR_CODIGO_DUPLICADO` | 409 |
| `LibroConEjemplares` | `LIBRO_CON_EJEMPLARES` | 409 |
| `CategoriaInvalida` | `CATEGORIA_INVALIDA` | 422 |
| `PrestamoNoEncontrado` / `RemitoNoEncontrado` | `PRESTAMO_NO_ENCONTRADO` / `REMITO_NO_ENCONTRADO` | 404 |
| `LibroYaPrestado` | `LIBRO_REPETIDO` | 409 |
| `RenovacionNoPermitida` | `RENOVACION_NO_PERMITIDA` | 409 |
| `EjemplarNoRecibido` | `EJEMPLAR_NO_RECIBIDO` | 409 |
| `PlazoDeTransitoVigente` | `PLAZO_DE_TRANSITO_VIGENTE` | 409 |
| `RemitoInvalido` | `REMITO_INVALIDO` | 422 |
| `ReservaNoEncontrada` | `RESERVA_NO_ENCONTRADA` | 404 |
| `LibroSinEjemplares` | `LIBRO_SIN_EJEMPLARES` | 409 |
| `UsuarioNoEncontrado` | `USUARIO_NO_ENCONTRADO` | 404 |
| `ExcepcionHorarioNoEncontrada` | `EXCEPCION_HORARIO_NO_ENCONTRADA` | 404 |
| `UsuarioYaEnBaja` / `UsuarioYaActivo` | `USUARIO_YA_EN_BAJA` / `USUARIO_YA_ACTIVO` | 409 |
| `SocioNoReactivable` | `SOCIO_NO_REACTIVABLE` | 409 |
| `SolicitudYaPendiente` / `SinSolicitudPendiente` | `SOLICITUD_YA_PENDIENTE` / `SIN_SOLICITUD_PENDIENTE` | 409 |
| `EjemplarNoRecuperable` | `EJEMPLAR_NO_RECUPERABLE` | 409 |
| `SinEjemplaresDisponibles` | `SIN_EJEMPLARES_DISPONIBLES` | 409 |
| `DisponibilidadCambiada` | `DISPONIBILIDAD_CAMBIADA` | 409 |
| `MultaNoEncontrada` / `PagoNoEncontrado` | `MULTA_NO_ENCONTRADA` / `PAGO_NO_ENCONTRADO` | 404 |

El catálogo completo vive en `exceptions/errores.py`; el HTTP sale de la clase base (`controllers/manejo_errores.py`): `EntidadNoEncontrada` 404, `ErrorDeValidacion` 422, `ReglaDeNegocioViolada` 409, `PermisoDenegado` 403, `CredencialesInvalidas` y `TokenInvalido` 401, y cualquier otro `ErrorDeNegocio` 400. Los errores de forma (campo faltante, tipo inválido) los devuelve FastAPI con 422 y el mismo formato de respuesta. Formato en [API REST](06-api.md#errores).

## Seguridad

- Contraseñas con hash Argon2id (`config/security.py`); nunca se guardan ni se registran en claro.
- JWT con vencimiento corto (60 min); el token incluye `sub`, `rol` y `sede_id`, pero el usuario se **recarga de la base en cada solicitud** (`RF-ACC-08`, `RF-ACC-10`).
- Autorización por **permiso**: el dominio define el mapa rol → permisos (`Permiso` y `ROL_PERMISOS` en `models/usuario.py`); cada endpoint declara con `requiere(Permiso.X)` lo que exige. Además, el servicio verifica la sede con `usuario.opera_en(sede_id)`: el bibliotecario opera solo sobre **su** sede (`RF-ACC-04`) y el administrador, que tiene los permisos completos, sobre cualquiera (`RF-ACC-13`). En una operación nueva, `usuario.sede_de_operacion(sede_id, campo)` devuelve la sede del bibliotecario o exige la que indica el administrador (`422` si falta).
- El DTO de respuesta se elige según el rol o el permiso de quien consulta (sede: completo, básico o público; socio, libro, préstamo, reserva, devolución, multa y pago: personal o propio), de modo que un campo no autorizado **nunca se serializa**: no se «oculta» después.
- El socio accede solo a sus propios datos (`RF-ACC-05`): el filtro se aplica en el servicio, no en el cliente.
- Secretos y credenciales solo por variables de entorno; `.env` está en `.gitignore` y existe un `.env.example` sin valores reales.
- CORS restringido al origen del frontend.
- Las escrituras registran usuario y momento (`RF-ACC-07`): columnas de auditoría o el historial de la entidad. Los cambios de parámetros quedan en `historial_parametro` (solo inserción).

## Configuración

Variables de entorno leídas con `pydantic-settings`:

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | Conexión a PostgreSQL |
| `DATABASE_URL_TEST` | Base de las pruebas (opcional; por defecto, la de `DATABASE_URL` con sufijo `_test`) |
| `SECRET_KEY` | Firma de los JWT |
| `ACCESS_TOKEN_MINUTES` | Duración del token |
| `CORS_ORIGINS` | Orígenes permitidos |
| `TZ_NEGOCIO` | Zona horaria para plazos y horarios de sede (`America/Argentina/Cordoba`) |
| `ENTORNO` | `desarrollo`, `test` o `produccion`; el seed solo corre en los dos primeros |
| `SEED_PASSWORD` | Contraseña de los usuarios de demostración (solo seed) |
| `LOG_LEVEL` | Nivel del registro de la aplicación (`INFO` por defecto) |

Los parámetros de negocio (plazos, límites, monto de multa) **no** son variables de entorno sino filas de la tabla `parametro`, editables por el administrador sin redesplegar.

## Observabilidad

Registro estructurado con **identificador de solicitud** (`app/utils/registro.py`):

- Un middleware HTTP toma el `X-Request-ID` que manda el cliente (si tiene hasta 64 caracteres `A-Za-z0-9._-`) o genera uno (uuid4), y lo devuelve en el encabezado `X-Request-ID` de la respuesta.
- Durante la solicitud el identificador vive en un `ContextVar`; `FiltroDeSolicitud` lo agrega a **cada línea de log** del logger `app` (también las de los servicios, de `controllers/manejo_errores.py` o de un endpoint sincrónico, que corre en otro hilo con el contexto copiado).
- Al terminar, el logger `app.solicitud` deja una línea por solicitud con método, ruta, estado, duración y el id del usuario autenticado (`usuario_actual` lo deja en `request.state`); nunca datos personales ni el token:

```text
2026-11-15 18:04:12,345 INFO app.solicitud [3f2a9c…] GET /api/v1/libros 200 12.4 ms usuario=7
```

`configurar_registro` aplica el formato al crear la aplicación (nivel `LOG_LEVEL`, `INFO` por defecto) y no toca los loggers de uvicorn. Además, `controllers/manejo_errores.py` registra los errores inesperados (500) y `tareas.py` el resultado de cada tarea periódica. La trazabilidad del negocio no depende de los logs: los cambios de estado de remito, préstamo, ejemplar y reserva, los eventos de sede y socio y los cambios de parámetros quedan en sus tablas de historial (solo inserción).
