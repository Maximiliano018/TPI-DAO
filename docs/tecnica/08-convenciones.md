# 08. Convenciones de desarrollo

Complementa `CONTRIBUTING.md` (ramas, commits y PR). Acá se fijan estilo de código, clean code y documentación del código.

## Idioma

| Elemento | Idioma |
|----------|--------|
| Documentación, mensajes de error, comentarios, mensajes de commit | Español |
| Nombres del dominio (clases, métodos y campos del negocio) | Español sin tildes ni eñe: `Prestamo`, `Ejemplar`, `sede_origen`, `dias_atraso` |
| Términos técnicos | Inglés convencional: `Repository`, `Service`, `Factory`, `UnitOfWork` |

Es la propuesta **T2**. El criterio es que quien lea el código y la documentación de negocio vea las mismas palabras.

## Python

- **Estilo:** PEP 8 aplicado por ruff (línea máxima 100). No se discute el formato: lo resuelve la herramienta.
- **Tipos:** anotaciones en todas las firmas públicas; `mypy` estricto en `domain/` y `application/`.
- **Nombres:** `snake_case` para funciones y variables, `PascalCase` para clases, `MAYUSCULAS` para constantes.
- **Importaciones:** solo en la parte superior, agrupadas (estándar, terceros, propias). `domain/` no importa de `api`, `application` ni `infrastructure`.
- **Excepciones:** se lanzan excepciones de dominio con código; no se usa `except Exception` salvo en el borde de la API.
- **Dinero y fechas:** `Decimal` para dinero, nunca `float`; reloj inyectado, nunca `date.today()` en el dominio.

### Documentación de métodos

Docstrings en español con formato Google, en todo módulo, clase y método público:

```python
def despachar(self, usuario: Usuario) -> None:
    """Despacha el remito hacia la sede destino.

    Pasa el remito a ``Despachado`` y los ejemplares a ``En tránsito``.

    Args:
        usuario: Bibliotecario de la sede origen que realiza el despacho.

    Raises:
        TransicionInvalida: Si el remito no está ``Empaquetado``.
        PermisoDenegado: Si el usuario no pertenece a la sede origen.
    """
```

Se documenta el **qué y el porqué**, no el cómo evidente. Los comentarios explican decisiones no obvias; si hace falta un comentario para entender una línea, se mejora el nombre o se extrae una función.

## Clean code

| Principio | Cómo se aplica |
|-----------|----------------|
| Nombres que revelan intención | `fecha_vencimiento`, no `fv`; `esta_activa()`, no `check()` |
| Funciones pequeñas | Una sola responsabilidad; si necesita «y» para describirse, se divide |
| Pocos parámetros | Hasta tres; más se agrupan en un objeto de valor o un DTO |
| Sin números ni textos mágicos | Constantes con nombre o parámetros de negocio de la tabla `parametro` |
| Sin duplicación (DRY) | Se extrae a partir de la tercera repetición, no antes |
| Retornos tempranos | Las guardas al inicio evitan anidar |
| Sin código muerto ni comentado | Para eso está git |
| Tell, don't ask | `ejemplar.prestar()` en lugar de leer su estado y decidir afuera |
| Mínimo conocimiento (Ley de Demeter) | Sin cadenas largas `a.b.c.d` |
| Efectos explícitos | Las funciones de consulta no modifican; las que modifican, lo dicen en el nombre |

### SOLID aplicado

- **S:** un servicio por proceso; una clase por estado.
- **O:** nuevas políticas de multa o plazo sin modificar las existentes (Strategy).
- **L:** cualquier implementación de un repositorio o política es intercambiable.
- **I:** interfaces de repositorio pequeñas y específicas por agregado.
- **D:** el dominio define las interfaces; infraestructura las implementa.

## Capas: qué va dónde

- Una regla de negocio en un router o un componente React es un defecto: va al dominio.
- Un router no consulta la base: llama a un servicio.
- Un servicio no devuelve modelos del ORM: devuelve entidades o DTO.
- Las entidades de dominio no importan Pydantic ni SQLAlchemy.

## API

- Rutas en plural y en español; acciones de estado como `POST /recurso/{id}/accion`.
- Los esquemas de entrada y salida son clases Pydantic distintas de las entidades.
- Los errores usan siempre el formato y los códigos de [API REST](06-api.md#errores).
- Todo endpoint documentado (`summary`, `response_model`, `responses`, ejemplos).

## JavaScript y React

- **Estilo:** ESLint (reglas de React, hooks y accesibilidad) + Prettier, aplicados en pre-commit.
- **Nombres:** componentes en `PascalCase`, hooks `useAlgo`, funciones y variables en `camelCase`, constantes en `MAYUSCULAS`.
- **Componentes:** funcionales, pequeños y con una responsabilidad; la lógica de datos va en hooks, no dentro del JSX.
- **Archivos:** un componente por archivo, con su prueba y estilos al lado.
- **Documentación:** JSDoc con tipos en funciones, hooks y componentes compartidos (`@param`, `@returns`), porque no hay TypeScript.
- **Sin reglas de negocio** en el frontend: valida formato y obligatoriedad, y deja que el backend decida; muestra los errores por su `codigo`.
- **Accesibilidad:** HTML semántico, etiquetas en todos los campos, foco visible, contraste AA ([Guía de estilos](10-guia-de-estilos.md)).

## Base de datos y migraciones

- Una migración de Alembic por cambio de modelo, con nombre descriptivo, revisada en el PR.
- Nunca se edita una migración ya mergeada: se agrega otra.
- Las restricciones de negocio críticas (únicos parciales, `CHECK`) se crean en migraciones, no solo en el código.
- Nombres de tablas y columnas en español, minúsculas y con guion bajo.

## Git y revisión

Rige `CONTRIBUTING.md`: ramas con prefijo, commits convencionales en español, un PR por tema, una aprobación y squash merge. Además:

- Un PR de código incluye sus pruebas y la documentación afectada.
- Si cambia una regla, se actualiza primero `docs/negocio` y `docs/funcional`; el código sigue a la documentación.
- Lista de revisión: ¿hay pruebas que fallarían sin este cambio?, ¿la regla está en el dominio?, ¿los nombres se entienden sin comentario?, ¿se documentaron los endpoints?, ¿sin secretos ni archivos de más?

## Seguridad en el código

- Consultas siempre parametrizadas (el ORM lo hace; no se arma SQL con texto concatenado).
- Entradas validadas con Pydantic; nada de `eval` ni deserialización insegura.
- Ningún secreto en el repositorio; `.env.example` sin valores reales.
- Registros sin contraseñas, tokens ni datos personales innecesarios.
- Dependencias actualizadas con Dependabot (ya configurado).
