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
| De API | Endpoints, autorización por rol, formato de errores, contrato OpenAPI | `TestClient` + PostgreSQL | `tests/api/` | 10 % |

Herramientas: **pytest**, **pytest-cov**, **httpx/TestClient**, **factory_boy** (datos de prueba) y **freezegun** o un reloj inyectable para fechas.

### Reglas

- El dominio **no** usa mocks de la base: se prueba con objetos reales y repositorios en memoria.
- Las pruebas de integración corren contra **PostgreSQL** (servicio en CI y en `docker-compose`); no se reemplazan por SQLite porque los índices parciales y los bloqueos de fila se comportan distinto.
- Cada prueba es independiente: crea sus datos y no depende del orden.
- El tiempo es una dependencia inyectada (`Reloj`); ningún test usa la fecha real.
- Nombres descriptivos: `test_no_se_presta_un_ejemplar_prestado`, no `test_1`.
- Patrón **Dado / Cuando / Entonces** (Arrange / Act / Assert) con una sola razón de falla por prueba.

## Trazabilidad con los criterios de aceptación

Cada criterio `CA-XXX-nn` tiene al menos una prueba que lo cubre. La prueba lo declara en su nombre o con un marcador, así se puede listar la cobertura funcional:

```python
@pytest.mark.ca("CA-PRE-23")
def test_sin_disponibles_en_la_red_se_rechaza(servicio_prestamos, libro_sin_disponibles, socio):
    with pytest.raises(SinDisponibilidad):
        servicio_prestamos.registrar(socio_id=socio.id, libro_id=libro_sin_disponibles.id)
```

| Documento funcional | Dónde se prueba principalmente |
|---------------------|--------------------------------|
| Acceso y roles | API (autorización) |
| Sedes, socios, catálogo | Unitarias + servicios; restricciones de unicidad en integración |
| Préstamos | Unitarias (estado, factory, plazos, criterio de sede origen) + servicios (reglas, determinación del tipo) + integración (índice de préstamo abierto, `SKIP LOCKED`) |
| Remitos | Unitarias de State (una por transición válida e inválida) + servicios |
| Reservas | Servicios (cola FIFO, asignación, vencimiento) |
| Devoluciones y multas | Unitarias de la política de multa + servicios |
| Reportes | Integración (consultas agregadas con datos conocidos) |

Un script de CI compara los `CA` de la documentación con los marcadores del código y avisa de criterios sin prueba.

## Casos de prueba imprescindibles

- **State del remito:** todas las transiciones válidas y todas las inválidas (matriz estado × operación).
- **Concurrencia:** dos solicitudes simultáneas por el último ejemplar disponible de una sede; solo una obtiene el préstamo local y la otra se vuelve a evaluar (`CA-PRE-07`, `CA-PRE-28`).
- **Determinación del tipo:** local si hay disponibles en la sede destino; interbibliotecario con la sede de más disponibles; empate por menor id; sedes en `Baja` excluidas; sin disponibilidad, rechazo con oferta de reserva; socio con disponibles en su sede, rechazo (`CA-PRE-19` a `CA-PRE-24`).
- **Vencimiento:** el día de vencimiento no es vencido; el siguiente sí (`CA-PRE-13`, `CA-PRE-14`, `CA-DEV-05`).
- **Multa:** cálculo con atraso de uno, cinco y cero días; cambio de monto en la configuración (`CA-DEV-06`, `CA-DEV-07`).
- **Cascada de efectos:** devolver libera el ejemplar, asigna la primera reserva y reevalúa al socio (`CA-DEV-15`, `CA-SOC-07`).
- **Baja de sede:** bloqueada por cada tipo de actividad pendiente (`CA-SED-05` a `CA-SED-07`).
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
| `domain/` | 90 % de líneas, 100 % de transiciones de estado |
| `application/` | 85 % |
| Backend en total | 80 % |
| Frontend | 70 %, priorizando formularios y flujos críticos |

La cobertura es un piso, no un objetivo: se revisa que las pruebas verifiquen comportamiento y no solo ejecuten líneas.

## Análisis estático y formato

| Herramienta | Uso |
|-------------|-----|
| ruff | Lint y formato del backend (reemplaza flake8, isort y black) |
| mypy (estricto en `domain/` y `application/`) | Tipos del backend |
| ESLint + Prettier | Lint y formato del frontend |
| pre-commit | Ejecuta ruff, ESLint y detección de secretos antes de cada commit |
| gitleaks | Ya activo en el repositorio |

## Integración continua

Se suma un workflow de GitHub Actions que corre en cada PR:

1. Backend: instalar, `ruff check`, `ruff format --check`, `mypy`, `pytest --cov` con PostgreSQL como servicio.
2. Frontend: instalar, `eslint`, `vitest run`.
3. Verificación de trazabilidad de criterios de aceptación.
4. Verificación de que las migraciones de Alembic aplican sobre una base vacía y que no quedan cambios de modelo sin migración.

El PR no se mergea con la integración continua en rojo, de acuerdo con `CONTRIBUTING.md`.

## Datos de prueba

- `factory_boy` define fábricas de dominio (`SedeFactory`, `SocioFactory`, `EjemplarFactory`…) con valores válidos por defecto, y cada test sobrescribe solo lo que importa.
- Los datos de demostración (`seed`) son distintos de los de prueba y no se usan en tests.
