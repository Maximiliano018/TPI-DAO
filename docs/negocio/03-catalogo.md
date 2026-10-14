# 03. Catálogo: libros y ejemplares

Proceso obligatorio 3 del enunciado.

## ¿Qué datos se modelan?

**Libro** (la obra, común a toda la red):

| Campo | Detalle |
|-------|---------|
| ISBN | Único |
| Título | Obligatorio |
| Autor(es) | Uno o más |
| Editorial, año de edición | |
| Categoría o género | Para búsquedas y recomendaciones futuras |
| Tipo de material | Libro u otro material de consulta |

**Ejemplar** (la copia física):

| Campo | Detalle |
|-------|---------|
| Código de inventario | Único en toda la red |
| Libro | Referencia al libro |
| Sede propietaria | Sede a la que pertenece |
| Sede actual | Dónde está físicamente (distinta de la propietaria si está en tránsito o prestado a otra sede) |
| Estado físico | `Nuevo`, `Bueno`, `Regular`, `Dañado` |
| Estado de disponibilidad | `Disponible`, `Reservado`, `Prestado`, `En tránsito`, `Baja` |
| Fecha de alta y de baja, motivo de baja | |

## ¿Quién administra libros y ejemplares?

- **Libros:** el Administrador (el catálogo es común a la red).
- **Ejemplares:** el Bibliotecario da de alta y modifica los ejemplares de **su sede**; el Administrador gestiona los de cualquier sede.

## ¿Quién puede ver esta información?

Todos los roles ven el catálogo y la disponibilidad. El estado físico detallado y el historial del ejemplar son solo para el personal.

## ¿Se puede dar de baja un ejemplar? ¿Bajo qué condiciones?

**Sí, baja lógica**, solo si el ejemplar está `Disponible` y sin reservas asignadas. Motivos: destrucción, extravío, daño irreparable, depuración del catálogo. Un ejemplar `Prestado` o `En tránsito` no se puede dar de baja: primero debe completarse el flujo, y si hay una incidencia (extravío, daño) la baja es el resultado del cierre del envío o de la devolución.

## ¿Cómo evitamos duplicados?

- **Libro:** ISBN único; si no tiene ISBN, combinación título + autor + editorial + año.
- **Ejemplar:** código de inventario único en toda la red. Dos ejemplares del mismo libro son legítimos si tienen códigos distintos.

## ¿Cómo se consulta la disponibilidad?

Un ejemplar está disponible solo si su estado es `Disponible`. La disponibilidad de un **libro** es el conteo de sus ejemplares disponibles, por sede y total en la red. Búsqueda por título, autor, ISBN o categoría. El resultado muestra, por sede: ejemplares totales, disponibles, prestados, en tránsito y reservados.

## ¿Es posible consultar libros y ejemplares de otras sedes?

**Sí.** Es el punto de partida del préstamo interbibliotecario. Se muestran todas las sedes **activas**; las sedes en baja no ofrecen ejemplares.

## Casos de uso y flujos

1. Alta de libro (con validación de ISBN).
2. Alta de ejemplar asociado a un libro y a una sede.
3. Modificación de datos y estado físico.
4. Baja de ejemplar.
5. Consulta de disponibilidad por libro y por sede.
6. Traslado definitivo de un ejemplar a otra sede (cambia la sede propietaria; requiere remito).

## Validaciones y reglas

- Un ejemplar siempre pertenece a una sede activa.
- No se prestan ejemplares que no estén `Disponible` (regla del enunciado).
- No se prestan ejemplares que no pertenezcan a la sede origen del préstamo (regla del enunciado).
- Un libro no se elimina si tiene ejemplares.
- Todo cambio de estado del ejemplar queda en su historial.
