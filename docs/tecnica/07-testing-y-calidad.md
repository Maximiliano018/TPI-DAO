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
| De API | Endpoints, autorización por rol, formato de errores, contrato OpenAPI | `TestClient` + PostgreSQL | `tests/controllers/` | 10 % |
| De contrato entre módulos | Que cada módulo cumpla lo que el resto espera (verificadores de baja, esquema OpenAPI) | Según el caso | `tests/contract/` | puntual |

Herramientas: **pytest**, **pytest-cov**, **httpx/TestClient**, **factory_boy** (datos de prueba) y un **reloj inyectable** (`Reloj`) para fechas; `freezegun` solo en pruebas de borde (API) donde no se puede inyectar.

### Reglas

- El dominio **no** usa mocks de la base: se prueba con objetos reales y repositorios en memoria.
- Las pruebas de integración corren contra **PostgreSQL** (servicio en CI y en `docker-compose`); no se reemplazan por SQLite porque los índices parciales y los bloqueos de fila se comportan distinto.
- Cada prueba es independiente: crea sus datos y no depende del orden.
- El tiempo es una dependencia inyectada (`Reloj`); ningún test usa la fecha real.
- Nombres descriptivos: `test_no_se_presta_un_ejemplar_prestado`, no `test_1`.
- Patrón **Dado / Cuando / Entonces** (Arrange / Act / Assert) con una sola razón de falla por prueba.

## Estructura de las pruebas

### Backend

```
backend/tests/
├── conftest.py              # fixtures globales: reloj, settings de prueba, marcador `ca`
├── unit/                    # dominio puro; una carpeta por agregado (sede/, usuario/, ...)
├── services/                # casos de uso con repositorios y verificadores en memoria
├── integration/             # PostgreSQL real: repositorios, restricciones, bloqueos, migraciones
│   └── conftest.py          # base de prueba, sesión por test, migraciones aplicadas una vez
├── controllers/             # HTTP: autorización por rol, formato de errores, esquemas
│   └── conftest.py          # TestClient, usuarios de cada rol, `autenticar(usuario)`
├── contract/                # contratos entre módulos y con OpenAPI
├── fakes/                   # RepositorioSedesEnMemoria, VerificadorBajaFalso, RelojFijo
└── factories/               # SedeFactory, UsuarioFactory, ... (factory_boy)
```

Un archivo de pruebas por unidad probada, con el mismo nombre que el módulo (`test_sede.py`, `test_sede_service.py`).

### Frontend

```
frontend/src/**/<Componente>.test.jsx   # pruebas junto al componente
frontend/tests/
├── setup.js                 # jest-dom, jest-axe, servidor MSW
├── render.jsx               # renderConProveedores(ui, { usuario, ruta }): router, query y sesión
└── mocks/                   # handlers de MSW por feature (sedes.js, auth.js) y datos de ejemplo
```

## Base de datos en las pruebas

| Tema | Decisión |
|------|----------|
| Motor | PostgreSQL 16 (servicio en CI; `docker compose up -d db` local). **Sin SQLite** |
| Base de prueba | Una base distinta de la de desarrollo (`tpi_dao_test`), creada si no existe por el fixture de sesión; la URL sale de `DATABASE_URL_TEST` |
| Esquema | Se aplica con `alembic upgrade head` **una vez por sesión de pruebas**; así las migraciones se prueban de verdad |
| Aislamiento | Cada prueba corre dentro de una transacción que se revierte al terminar (savepoint). Las pruebas de concurrencia, que necesitan transacciones reales, usan un marcador `@pytest.mark.concurrencia` y limpian con `TRUNCATE ... CASCADE` |
| Datos | Cada prueba crea lo que necesita con las fábricas; el seed de demostración no se usa |
| Reloj | `RelojFijo` inyectado; ninguna prueba usa la fecha real |

## Autenticación en las pruebas

- Las pruebas de servicio construyen el `Usuario` de dominio directamente (`UsuarioFactory(rol=Rol.ADMIN)`), sin token.
- Las pruebas de API usan `autenticar(usuario)`, que emite un token real con la clave de prueba, así se ejercita toda la cadena de seguridad.
- Cada endpoint tiene una prueba parametrizada **rol × endpoint** (matriz de permisos): administrador, bibliotecario de la sede, bibliotecario de otra sede, socio, sin token y token vencido.

## Marcadores

| Marcador | Uso |
|----------|-----|
| `@pytest.mark.ca("CA-SED-05")` | Declara el criterio de aceptación que la prueba cubre (puede recibir varios) |
| `@pytest.mark.integration` | Necesita PostgreSQL (se aplica solo por carpeta) |
| `@pytest.mark.concurrencia` | Transacciones reales y varios hilos |

`pytest -m "not integration"` corre la parte rápida (sin base) en el ciclo de desarrollo; CI corre todo.

## Comandos

Se documentan en `CLAUDE.md` y en el README del backend y del frontend cuando existan.

| Acción | Backend | Frontend |
|--------|---------|----------|
| Pruebas rápidas | `pytest -m "not integration"` | `npm test` |
| Pruebas completas con cobertura | `pytest --cov=app` | `npm test -- --coverage` |
| Lint y formato | `ruff check . && ruff format --check .` | `npm run lint && npm run format:check` |
| Tipos | `mypy app/models app/services` | — |
| Trazabilidad de criterios | `python scripts/verificar_trazabilidad_ca.py` | — |

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

### Plan de pruebas de sedes y acceso (esta iteración)

| Criterios | Nivel principal | Notas |
|-----------|-----------------|-------|
| `CA-SED-01`, `02`, `12`, `13`, `14`, `26` a `28`, `34` a `36`, `38` a `40` | Unitaria + servicio | Reglas de la entidad y del servicio con repositorio en memoria |
| `CA-SED-03` | Servicio + API | Flujo de advertencia y confirmación de dirección duplicada |
| `CA-SED-04` | Unitaria + integración | Dominio y exclusión `btree_gist` |
| `CA-SED-05` a `07`, `16` a `23` | Servicio con verificadores falsos; integración para el verificador de usuarios | Cada tipo de impedimento y su combinación; `CA-SED-07` verifica que no cambia ningún estado |
| `CA-SED-08` a `10`, `15`, `47` | Unitaria + servicio | Baja, reactivación, edición bloqueada, repetición |
| `CA-SED-09`, `24`, `25` | Servicio (los consumidores reales llegan con sus módulos) | Contrato `validar_operativa` / `obtener_para_operar` |
| `CA-SED-11`, `37`, `43` a `46` | API | Visibilidad por rol, paginación, 404 del socio |
| `CA-SED-29` a `33` | Unitaria + servicio + API | Excepciones y `abierta_ahora` con reloj fijo |
| `CA-SED-41`, `42` | Integración (`concurrencia`) | Dos transacciones reales |
| `CA-ACC-01` a `13` | API + servicio | Matriz rol × endpoint, token vencido, usuario dado de baja |

### Pruebas de contrato

`tests/contract/test_verificadores_baja_sede.py`: cada `TipoImpedimento` tiene un verificador registrado o figura en `TIPOS_PENDIENTES_DE_MODULO`; la lista de pendientes solo puede achicarse (una segunda prueba compara con el valor del último PR). `tests/contract/test_openapi.py`: todo endpoint documentado, con `summary`, `response_model` y errores.

## Definición de terminado de un PR de código

1. Cada criterio de aceptación que toca tiene prueba con su marcador `ca`.
2. Pruebas que fallarían sin el cambio (no solo líneas cubiertas).
3. `ruff`, `mypy` y las pruebas en verde localmente y en CI.
4. Cobertura sin bajar de los mínimos por capa.
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

- Un test recorre `app.openapi()` y falla si algún endpoint no tiene `summary`, `response_model` o respuestas de error documentadas.
- Tests de contrato: la respuesta real de cada endpoint se valida contra su esquema.
- Los ejemplos de [API REST](06-api.md) se mantienen sincronizados con los `examples` de los esquemas.

## Frontend

| Nivel | Herramienta | Qué cubre |
|-------|-------------|-----------|
| Unitarias | Vitest | Funciones auxiliares, validaciones de formularios, formateo |
| Componentes | React Testing Library | Componentes del design system y pantallas con la API simulada (MSW) |
| Accesibilidad | jest-axe | Sin violaciones automáticas en componentes base y pantallas |
| Extremo a extremo (opcional) | Playwright | Flujo completo: préstamo interbibliotecario de punta a punta |

Se prueba lo que el usuario ve y hace (texto, roles ARIA, interacción), no detalles internos de implementación.

## Cobertura

| Alcance | Mínimo |
|---------|--------|
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
| ESLint + Prettier | Lint y formato del frontend |
| pre-commit | Ejecuta ruff, ESLint y detección de secretos antes de cada commit |
| gitleaks | Ya activo en el repositorio |

## Integración continua

Se suma un workflow de GitHub Actions que corre en cada PR:

1. Backend: instalar, `ruff check`, `ruff format --check`, `mypy`, `pytest --cov` con PostgreSQL 16 como servicio y `DATABASE_URL_TEST`.
2. Frontend: instalar, `eslint`, `prettier --check`, `vitest run --coverage` y el build.
3. Verificación de trazabilidad de criterios de aceptación.
4. Verificación de que las migraciones de Alembic aplican sobre una base vacía y que no quedan cambios de modelo sin migración.

El PR no se mergea con la integración continua en rojo, de acuerdo con `CONTRIBUTING.md`.

## Datos de prueba

- `factory_boy` define fábricas de dominio (`SedeFactory`, `SocioFactory`, `EjemplarFactory`…) con valores válidos por defecto, y cada test sobrescribe solo lo que importa.
- Los datos de demostración (`seed`) son distintos de los de prueba y no se usan en tests.
- Las fábricas devuelven datos válidos por defecto (código, teléfono E.164, localidad existente, al menos una franja), de modo que una prueba solo sobrescribe lo que quiere romper.
