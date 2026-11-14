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
| Estado de disponibilidad | `Disponible`, `Apartado`, `Reservado`, `Prestado`, `En tránsito`, `En revisión`, `Baja` |
| Fecha de alta y de baja, motivo de baja | |

Dos estados se agregaron al diseñar el flujo:
- **`Apartado`**: retenido para un movimiento pendiente, como un préstamo solicitado o un ejemplar que espera volver a su sede.
- **`En revisión`**: devuelto o recibido dañado, a la espera de que su sede decida si lo repara o lo da de baja.

El detalle está en [máquinas de estado](../tecnica/03-maquinas-de-estado.md#ejemplar).

## ¿Quién administra libros y ejemplares?

- **Libros:** el Administrador (el catálogo es común a la red).
- **Ejemplares:** el Bibliotecario da de alta y modifica los ejemplares de **su sede**; el Administrador gestiona los de cualquier sede.

## ¿Quién puede ver esta información?

Todos los roles ven el catálogo y la disponibilidad. El estado físico detallado y el historial del ejemplar son solo para el personal. Quién cargó o modificó un libro (la auditoría) lo ve solo el administrador, que es quien administra el catálogo.

## ¿Se puede dar de baja un ejemplar? ¿Bajo qué condiciones?

**Sí, baja lógica**, solo si el ejemplar está `Disponible` (sin reservas asignadas) o `En revisión` (daño irreparable). Motivos: destrucción, extravío, daño irreparable, depuración del catálogo. Un ejemplar `Prestado`, `Apartado`, `Reservado` o `En tránsito` no se puede dar de baja: primero debe completarse el flujo, y si hay una incidencia (extravío, daño) la baja es el resultado del cierre del envío o de la devolución. Un ejemplar dado de baja ya no se edita: queda como historial. La única excepción es un **extravío** que se resuelve: si el ejemplar aparece, la sede propietaria lo recupera (vuelve a `Disponible`, o a `En revisión` si llegó dañado) y la incidencia queda resuelta.

## ¿Cómo evitamos duplicados?

- **Libro:** ISBN único; si no tiene ISBN, combinación título + autor + editorial + año.
- **Ejemplar:** código de inventario único en toda la red. Dos ejemplares del mismo libro son legítimos si tienen códigos distintos. El código no se modifica después del alta.

## ¿Cómo se consulta la disponibilidad?

Un ejemplar está disponible solo si su estado es `Disponible`. La disponibilidad de un **libro** es el conteo de sus ejemplares disponibles, por sede y total en la red. Búsqueda por título, autor, ISBN o categoría (y tipo de material). Un número corto (por ejemplo, «1984») se busca en el título; el ISBN se compara recién con 6 dígitos o más, para no traer cualquier libro cuyo ISBN lo contenga. El resultado muestra, por sede: ejemplares totales, disponibles, prestados, en tránsito y reservados.

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
- Todo cambio del ejemplar queda en su historial con fecha y responsable:
  - su disponibilidad;
  - su estado físico y sus observaciones;
  - la sede donde está y la sede a la que pertenece.
- La revisión y la reparación de un ejemplar dañado las hace su sede propietaria. Un ejemplar que llega dañado a otra sede vuelve a la suya con un remito de retorno (ver [Remitos](05-remitos.md)).
- Si dos personas editan el mismo libro o ejemplar a la vez, gana la primera; la segunda recibe un aviso para recargar y no pisa el cambio.
