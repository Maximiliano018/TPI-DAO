# 07. Testing y calidad

## Objetivos

1. Comprobar que cada **criterio de aceptación** de [`docs/funcional/`](../funcional/) se cumple.
2. Proteger las reglas de negocio y las máquinas de estado frente a cambios.
3. Mantener un ciclo de desarrollo rápido: la mayoría de las pruebas no necesitan base de datos.

## Pirámide de pruebas (backend)

| Nivel | Qué prueba | Dependencias | Carpeta | Proporción aproximada |
|-------|------------|--------------|---------|-----------------------|
| Unitarias de dominio | Entidades, estados, políticas, factory, objetos de valor | Ninguna | `tests/unit/` | 60 % |
| De servicios | Casos de uso completos con repositorios en memoria | Repositorios en memoria | `tests/services/` | 20 % |
| De integración | Repositorios, restricciones, índices parciales, bloqueos y migraciones | PostgreSQL | `tests/integration/` | 10 % |
| De API | Endpoints, autorización por rol, formato de errores, registro por solicitud | `TestClient` + PostgreSQL | `tests/controllers/` | 10 % |
| De contrato | Que cada módulo cumpla lo que el resto espera (verificadores de baja de sede) y que toda la API esté documentada en OpenAPI | Según el caso | `tests/contract/` | puntual |

Herramientas: **pytest**, **pytest-cov**, **httpx/TestClient**, **factory_boy** (datos de prueba) y un **reloj inyectable** (`Reloj`) para fechas: las pruebas de API reemplazan el reloj con `app.dependency_overrides`. `freezegun` está instalado pero ninguna prueba lo usa.

### Reglas

- El dominio **no** usa mocks de la base: se prueba con objetos reales y repositorios en memoria.
- Las pruebas de integración corren contra **PostgreSQL** (servicio en CI y contenedor local de `docker-compose`); no se reemplazan por SQLite porque los índices parciales y los bloqueos de fila se comportan distinto.
- Cada prueba es independiente: crea sus datos y no depende del orden.
- El tiempo es una dependencia inyectada (`Reloj`); ningún test usa la fecha real.
- Nombres descriptivos: `test_no_se_presta_un_ejemplar_prestado`, no `test_1`.
- Patrón **Dado / Cuando / Entonces** (Arrange / Act / Assert) con una sola razón de falla por prueba.

## Estructura de las pruebas

### Backend

```
backend/tests/
├── conftest.py              # fixtures globales (reloj) y marcado automático de `integration`
├── base_datos.py            # base de prueba (`<nombre>_test`), migraciones una vez por sesión,
│                            #   transacción revertida por prueba
├── unit/                    # dominio puro; una carpeta por módulo (sede/, socio/, catalogo/, prestamos/, ...)
├── services/                # casos de uso con repositorios y verificadores en memoria
├── integration/             # PostgreSQL real: repositorios, restricciones, concurrencia
├── controllers/             # HTTP: autorización por rol, formato de errores, esquemas
│   └── conftest.py          # TestClient, reloj de pruebas, usuarios de cada rol, `autenticar(usuario)`
├── contract/                # contrato de los verificadores de baja de sede
├── fakes/                   # repositorios en memoria, UnitOfWorkEnMemoria, RelojFijo, VerificadorFalso
└── factories/               # SedeFactory, UsuarioFactory, ... (factory_boy) y datos del ORM
```

Un archivo de pruebas por unidad probada, con el mismo nombre que el módulo (`test_sede.py`, `test_sede_service.py`).

### Frontend

```
frontend/src/**/<Componente>.test.jsx   # pruebas junto al componente
frontend/tests/
├── setup.js                 # jest-dom, jest-axe, servidor MSW
├── servidor.js              # servidor MSW con los handlers por defecto
├── handlers.js              # responder(), registrar(), error() y sesionDe(): handlers por prueba
├── datos.js                 # datos de ejemplo con el formato de la API (sede, socio, préstamo, multa, pago…)
└── render.jsx               # renderizarApp(ruta, { conSesion }): app completa con router, query y sesión
```

## Base de datos en las pruebas

| Tema | Decisión |
|------|----------|
| Motor | PostgreSQL 16 (servicio en CI; `docker compose up -d db` local). **Sin SQLite** |
| Base de prueba | Una base distinta de la de desarrollo, creada si no existe (`tests/base_datos.py`): `DATABASE_URL_TEST` si está definida; si no, la de `DATABASE_URL` con sufijo `_test` (`tpi_dao_test`) |
| Esquema | Se aplica con `alembic upgrade head` **una vez por sesión de pruebas**; así las migraciones se prueban de verdad |
| Aislamiento | Cada prueba corre dentro de una transacción que se revierte al terminar (savepoint). Las pruebas de concurrencia, que necesitan transacciones reales, usan un marcador `@pytest.mark.concurrencia` y limpian con `TRUNCATE ... CASCADE` |
| Datos | Cada prueba crea lo que necesita con las fábricas; el seed de demostración no se usa |
| Reloj | `RelojFijo` o `RelojDePruebas` inyectado; ninguna prueba usa la fecha real |

## Autenticación en las pruebas

- Las pruebas de servicio construyen el `Usuario` de dominio directamente (`UsuarioFactory(rol=Rol.ADMIN)`), sin token.
- Las pruebas de API usan `autenticar(usuario)`, que emite un token real con la clave de prueba, así se ejercita toda la cadena de seguridad.
- Las pruebas de API de cada módulo verifican los permisos por rol (administrador, bibliotecario de la sede, de otra sede, socio) y la autenticación (sin token, token vencido, usuario dado de baja).

## Marcadores

| Marcador | Uso |
|----------|-----|
| `@pytest.mark.ca("CA-SED-05")` | Declara el criterio de aceptación que la prueba cubre (puede recibir varios) |
| `@pytest.mark.integration` | Necesita PostgreSQL (lo agrega `conftest.py` a lo que está en `tests/integration/` o usa la base) |
| `@pytest.mark.concurrencia` | Transacciones reales y varios hilos |

`pytest -m "not integration"` corre la parte rápida (sin base) en el ciclo de desarrollo; CI corre todo.

## Comandos

Están en `CLAUDE.md` (sección Comandos).

| Acción | Backend | Frontend |
|--------|---------|----------|
| Pruebas rápidas | `pytest -m "not integration"` | `npm test` |
| Pruebas completas con cobertura | `pytest --cov=app` (falla por debajo del 90 %) | `npm run test:coverage` (falla por debajo de los mínimos de `vite.config.js`) |
| Lint y formato | `ruff check . && ruff format --check .` | `npm run lint && npm run format:check` |
| Tipos | `mypy app/models app/services` | — |
| Trazabilidad de criterios | `python scripts/verificar_trazabilidad_ca.py --prefijos SED,ACC,SOC,CAT,PRE,REM,RES,DEV,REP --estricto` | — |
| Diccionario de datos | `python scripts/generar_diccionario_datos.py --verificar` | — |

## Convenciones de nombre y forma

- Archivos `test_<modulo>.py`; funciones `test_<comportamiento_esperado>` en español, sin tildes: `test_la_baja_se_bloquea_con_un_bibliotecario_asignado`.
- Cada prueba verifica **una** regla. Si necesita «y» para describirse, se divide.
- Estructura Dado / Cuando / Entonces con una línea en blanco entre bloques.
- Los datos relevantes para la prueba se escriben en la prueba; lo irrelevante lo completa la fábrica.
- Una prueba de error verifica el **código** (`SEDE_EN_BAJA`) y, en API, también el estado HTTP; no el texto del mensaje, salvo la prueba específica del mensaje.
- Prohibido: `sleep`, orden entre pruebas, datos compartidos entre pruebas, fecha real, red externa.

## Cómo se decide el nivel de cada criterio

| Tipo de criterio | Nivel | Ejemplo |
|------------------|-------|---------|
| Regla de una entidad (valida, transiciona, calcula) | Unitaria de dominio | `CA-SED-28` cierre posterior a la apertura |
| Caso de uso que coordina varias entidades o repositorios | Servicio | `CA-SED-22` baja tras resolver impedimentos |
| Restricción o garantía de la base, bloqueos | Integración | `CA-SED-04` solapamiento (exclusión), `CA-SED-42` concurrencia |
| Permiso, formato de respuesta, códigos HTTP | API | `CA-SED-11`, `CA-SED-37`, `CA-SED-44`, `CA-SED-45`, `CA-SED-46` |
| Lo que ve y hace el usuario | Frontend (componente) | confirmación de baja, mensaje de impedimentos |
| Flujo completo entre capas | Extremo a extremo (opcional) | login → alta de sede → baja bloqueada |

Un criterio puede tener pruebas en más de un nivel; el marcador `ca` se repite en cada una.

### Plan de pruebas de sedes y acceso (histórico: primera iteración)

Plan con el que se probó el primer módulo; los siguientes siguieron el mismo criterio por nivel.

| Criterios | Nivel principal | Notas |
|-----------|-----------------|-------|
| `CA-SED-01`, `02`, `12`, `13`, `14`, `26` a `28`, `34` a `36`, `38` a `40` | Unitaria + servicio | Reglas de la entidad y del servicio con repositorio en memoria |
| `CA-SED-03` | Servicio + API | Flujo de advertencia y confirmación de dirección duplicada |
| `CA-SED-04` | Unitaria + integración | Dominio y exclusión `btree_gist` |
| `CA-SED-05` a `07`, `16` a `23` | Servicio con verificadores falsos; integración para el verificador de usuarios | Cada tipo de impedimento y su combinación; `CA-SED-07` verifica que no cambia ningún estado |
| `CA-SED-08` a `10`, `15`, `47` | Unitaria + servicio | Baja, reactivación, edición bloqueada, repetición |
| `CA-SED-09`, `24`, `25` | Servicio | Contrato `validar_operativa` / `obtener_para_operar` |
| `CA-SED-11`, `37`, `43` a `46` | API | Visibilidad por rol, paginación, 404 del socio |
| `CA-SED-29` a `33` | Unitaria + servicio + API | Excepciones y `abierta_ahora` con reloj fijo |
| `CA-SED-41`, `42` | Integración (`concurrencia`) | Dos transacciones reales |
| `CA-ACC-01` a `13` | API + servicio | Matriz rol × endpoint, token vencido, usuario dado de baja |

### Pruebas de contrato

`tests/contract/test_verificadores_baja_sede.py`: cada `TipoImpedimento` tiene un verificador registrado o figura en `TIPOS_PENDIENTES_DE_MODULO`; la lista de pendientes solo puede achicarse y hoy está vacía. `tests/contract/test_openapi.py`: recorre `app.openapi()` y exige en cada endpoint `summary`, `description` (su docstring) y `tags`; una respuesta exitosa con esquema (salvo `204` y archivos); y los errores que puede dar documentados: `401` en las rutas protegidas, `403` en las que exigen un permiso que algún rol no tiene, `404` en las que reciben un identificador y `422` en las que reciben parámetros o cuerpo.

## Definición de terminado de un PR de código

1. Cada criterio de aceptación que toca tiene prueba con su marcador `ca`.
2. Pruebas que fallarían sin el cambio (no solo líneas cubiertas).
3. `ruff`, `mypy` y las pruebas en verde localmente y en CI.
4. Cobertura sin bajar de los mínimos que controla CI (backend 90 %; frontend 88 % de líneas).
5. Migraciones aplicables sobre una base vacía y sin diferencias contra el modelo.
6. Documentación (`docs/`) y ejemplos de la API al día.
7. Sin secretos ni datos de demostración en las pruebas.

## Trazabilidad con los criterios de aceptación

Cada criterio `CA-XXX-nn` tiene al menos una prueba que lo cubre. La prueba lo declara en su nombre o con un marcador, así se puede listar la cobertura funcional:

```python
@pytest.mark.ca("CA-PRE-01")
def test_no_se_presta_un_ejemplar_prestado(servicio_prestamos, ejemplar_prestado, socio):
    with pytest.raises(EjemplarNoDisponible):
        servicio_prestamos.registrar(socio_id=socio.id, ejemplar_id=ejemplar_prestado.id)
```

| Documento funcional | Dónde se prueba principalmente |
|---------------------|--------------------------------|
| Acceso y roles | API (autorización) + servicios |
| Sedes, socios, catálogo | Unitarias + servicios; restricciones de unicidad en integración; ver el plan de sedes arriba |
| Préstamos | Unitarias (estado, factory, plazos) + servicios (reglas) + integración (índice de préstamo abierto) |
| Remitos | Unitarias de State (una por transición válida e inválida) + servicios |
| Reservas | Servicios (cola FIFO, asignación, vencimiento) |
| Devoluciones y multas | Unitarias de la política de multa + servicios |
| Reportes | Integración (consultas agregadas con datos conocidos) |

Un script de CI compara los `CA` de la documentación con los marcadores del código y avisa de criterios sin prueba.

## Casos de prueba imprescindibles

- **State del remito:** todas las transiciones válidas y todas las inválidas (matriz estado × operación).
- **Concurrencia:** dos solicitudes simultáneas sobre el mismo ejemplar; solo una prospera (`CA-PRE-01`, `CA-PRE-07`).
- **Vencimiento:** el día de vencimiento no es vencido; el siguiente sí (`CA-PRE-13`, `CA-PRE-14`, `CA-DEV-05`).
- **Multa:** cálculo con atraso de uno, cinco y cero días; cambio de monto en la configuración (`CA-DEV-06`, `CA-DEV-07`).
- **Cascada de efectos:** devolver libera el ejemplar, asigna la primera reserva y reevalúa al socio (`CA-DEV-15`, `CA-SOC-07`).
- **Baja de sede:** bloqueada por cada tipo de actividad pendiente y por sus combinaciones (`CA-SED-05` a `07`, `16` a `23`) y serializada frente a operaciones concurrentes (`CA-SED-42`).
- **Autorización:** cada endpoint rechaza los roles no permitidos y las sedes ajenas.

## Calidad de la API

- Cada endpoint declara `response_model`, así FastAPI valida la respuesta real contra su esquema.
- `tests/contract/test_openapi.py` falla si algún endpoint queda sin `summary`, descripción, esquema de respuesta o errores documentados (ver [Pruebas de contrato](#pruebas-de-contrato)).
- **Registro por solicitud:** el middleware de `app/main.py` (`app/utils/registro.py`) asigna a cada solicitud un identificador (`X-Request-ID`, el del cliente o uno nuevo), lo devuelve en la respuesta, lo agrega a cada línea de log emitida durante la solicitud y deja una línea final con método, ruta, estado, duración y el id del usuario. Lo verifica `tests/controllers/test_registro_solicitudes.py`. El nivel se configura con `LOG_LEVEL`.
- Los ejemplos de [API REST](06-api.md) se mantienen sincronizados con los `examples` de los esquemas.

## Frontend

| Nivel | Herramienta | Qué cubre |
|-------|-------------|-----------|
| Unitarias | Vitest | Funciones auxiliares, validaciones de formularios, formateo |
| Componentes | React Testing Library | Componentes del design system y pantallas con la API simulada (MSW) |
| Accesibilidad | jest-axe | Sin violaciones automáticas en componentes base y pantallas |
| Extremo a extremo (opcional, no implementado) | Playwright | Flujo completo: préstamo interbibliotecario de punta a punta |

Se prueba lo que el usuario ve y hace (texto, roles ARIA, interacción), no detalles internos de implementación.

## Cobertura

CI **controla** la cobertura con mínimos fijados unos puntos por debajo de la medida, para que una regresión haga fallar el PR:

| Alcance | Medida | Mínimo en CI | Dónde se configura |
|---------|--------|--------------|--------------------|
| Backend (`app/`) | 94 % de sentencias | 90 % | `backend/pyproject.toml`, `[tool.coverage.report] fail_under` (lo aplica `pytest --cov=app`) |
| Frontend (`src/`) | 91 % de líneas y sentencias, 88 % de ramas, 84 % de funciones | 88 %, 85 %, 80 % | `frontend/vite.config.js`, `test.coverage.thresholds` (`npm run test:coverage`, con `@vitest/coverage-v8`) |

Además, por capa se mantienen estas metas (no las controla CI):

| Alcance | Meta |
|---------|------|
| `models/` | 90 % de líneas, 100 % de transiciones de estado |
| `services/` | 85 % |
| Backend en total | 80 % |
| Frontend | 70 %, priorizando formularios y flujos críticos |
| `controllers/` y `repositories/` | Cubiertos por las pruebas de API e integración; sin mínimo propio |

La cobertura es un piso, no un objetivo: se revisa que las pruebas verifiquen comportamiento y no solo ejecuten líneas.

## Análisis estático y formato

| Herramienta | Uso |
|-------------|-----|
| ruff | Lint y formato del backend (reemplaza flake8, isort y black) |
| mypy (estricto en `models/` y `services/`) | Tipos del backend |
| ESLint (reglas de React y hooks) + Prettier | Lint y formato del frontend |
| gitleaks | Detección de secretos en cada PR (workflow propio) |
| pre-commit | **Pendiente**: no hay ganchos locales; los controles corren en CI |

## Integración continua

`.github/workflows/ci.yml` corre en cada PR y en cada push a `main`:

1. **Backend**, con PostgreSQL 16 como servicio y `DATABASE_URL` (las pruebas usan esa base con sufijo `_test`): `pip install -e ".[dev]"`, `ruff check`, `ruff format --check`, `mypy app/models app/services`, `pytest --cov=app --cov-report=term-missing` (falla por debajo del 90 %), `alembic upgrade head` + `alembic check` (las migraciones aplican sobre una base vacía y no quedan cambios de modelo sin migrar) y la trazabilidad estricta de criterios de aceptación.
2. **Frontend**, con la versión de Node de `.nvmrc`: `npm ci`, `npm run lint`, `npm run format:check`, `npm run test:coverage` (pruebas con los mínimos de cobertura) y `npm run build`.

Además corren `gitleaks` (secretos) y `titulo-y-rama` (título de PR convencional y prefijo de rama), en workflows propios.

El PR no se mergea con la integración continua en rojo, de acuerdo con `CONTRIBUTING.md`.

## Datos de prueba

- `factory_boy` define fábricas de dominio (`SedeFactory`, `SocioFactory`, `EjemplarFactory`…) con valores válidos por defecto, y cada test sobrescribe solo lo que importa.
- Los datos de demostración (`seed`) son distintos de los de prueba y no se usan en tests.
- Las fábricas devuelven datos válidos por defecto (código, teléfono E.164, localidad existente, al menos una franja), de modo que una prueba solo sobrescribe lo que quiere romper.
