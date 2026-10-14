# Guía de contribución

Proyecto académico (UTN FRC 2026). Estas reglas buscan un historial limpio y revisiones simples.

## Ramas

- `main`: siempre estable. **No se commitea directo**; todo entra por Pull Request.
- Ramas de trabajo, creadas desde `main` y con vida corta:

| Prefijo | Uso | Ejemplo |
|---------|-----|---------|
| `feature/` | Funcionalidad nueva | `feature/abm-socios` |
| `fix/` | Corrección de errores | `fix/validacion-dni` |
| `docs/` | Documentación | `docs/diagrama-clases` |
| `refactor/` | Cambios internos sin alterar comportamiento | `refactor/repositorio-sedes` |
| `chore/` | Configuración, dependencias, CI | `chore/actualizar-deps` |

Nombres en minúsculas, con guiones, sin espacios ni tildes.

## Commits

Mensajes en español, en imperativo y de hasta ~72 caracteres en la primera línea, con prefijo [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/):

```
feat: agregar ABM de socios
fix: corregir cálculo de fecha de devolución
docs: actualizar análisis del dominio
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

## Pull Requests

1. Un PR por tema; chico y enfocado.
2. Completar la plantilla del PR y vincular el issue (`Closes #n`).
3. Abrir como **borrador** si todavía no está listo.
4. Requiere **1 aprobación** y checks en verde (ver `CODEOWNERS`).
5. Resolver todas las conversaciones antes de mergear.
6. Merge con **Squash and merge**; se borra la rama al mergear.

## Aprobadores y contribuyentes

- Aprobadores: ver [`.github/CODEOWNERS`](.github/CODEOWNERS).
- Nadie aprueba su propio PR.
- Los integrantes del equipo se agregan como colaboradores con rol *Write*.

## Agentes de IA

Se permite el uso de agentes (por ej. Claude Code). Siguen las mismas reglas que cualquier contribuyente: trabajan en ramas propias, abren PR y requieren revisión humana. Ver [`CLAUDE.md`](CLAUDE.md).

## Seguridad

Nunca commitear credenciales, tokens ni archivos `.env`. Ver [`SECURITY.md`](SECURITY.md).
