# 03. Catálogo: libros y ejemplares

Origen: [negocio/03-catalogo.md](../negocio/03-catalogo.md). Proceso obligatorio 3 (la consulta de disponibilidad es el proceso 6).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-CAT-01 | El sistema debe permitir al administrador dar de alta y modificar libros con ISBN, título, autores, editorial, año, categoría y tipo de material. | Obligatorio |
| RF-CAT-02 | El sistema debe evitar libros duplicados por ISBN; sin ISBN, por la combinación título, autor, editorial y año. | Obligatorio |
| RF-CAT-03 | El sistema debe permitir dar de alta ejemplares con código de inventario único en toda la red, asociados a un libro y a una sede propietaria activa. | Obligatorio |
| RF-CAT-04 | El sistema debe permitir al bibliotecario administrar los ejemplares de su sede, y al administrador los de cualquier sede. | Obligatorio |
| RF-CAT-05 | Cada ejemplar debe tener estado físico (`Nuevo`, `Bueno`, `Regular`, `Dañado`), estado de disponibilidad (`Disponible`, `Reservado`, `Prestado`, `En tránsito`, `Baja`) y sede propietaria y actual. | Obligatorio |
| RF-CAT-06 | El sistema debe registrar en un historial cada cambio de estado de un ejemplar. | Obligatorio |
| RF-CAT-07 | El sistema debe permitir dar de baja lógica a un ejemplar `Disponible` y sin reserva asignada, registrando motivo y fecha. | Obligatorio |
| RF-CAT-08 | El sistema no debe permitir eliminar un libro que tenga ejemplares. | Obligatorio |
| RF-CAT-09 | El sistema debe permitir consultar la disponibilidad por libro, con detalle por sede (totales, disponibles, prestados, reservados y en tránsito), y buscar por título, autor, ISBN o categoría. | Obligatorio |
| RF-CAT-10 | La consulta de catálogo debe incluir las sedes activas de toda la red; los ejemplares de sedes en `Baja` no se ofrecen. | Obligatorio |
| RF-CAT-11 | El sistema debe permitir trasladar un ejemplar a otra sede (cambio de sede propietaria) mediante remito de traslado. | Obligatorio |

## Casos de uso

### CU-CAT-01. Dar de alta un libro

- **Actor:** Administrador.
- **Flujo normal:** ingresa los datos del libro; el sistema valida y lo crea.
- **Flujos alternativos:**
  - **A1:** ISBN ya existente; rechaza e indica el libro existente.
  - **A2:** sin ISBN y con la misma combinación título, autor, editorial y año; rechaza.
  - **A3:** ISBN con formato inválido; rechaza.
  - **A4:** falta título o autor; rechaza.

### CU-CAT-02. Dar de alta un ejemplar

- **Actor:** Bibliotecario (su sede), Administrador.
- **Precondición:** el libro existe.
- **Flujo normal:**
  1. Selecciona el libro e ingresa código de inventario y estado físico.
  2. El sistema asigna la sede del bibliotecario como propietaria y actual.
  3. Crea el ejemplar `Disponible` y registra el primer movimiento en su historial.
- **Flujos alternativos:**
  - **A1 (paso 1): código ya existente en la red.** Rechaza.
  - **A2 (paso 2): sede propietaria en `Baja`.** Rechaza.
  - **A3 (paso 1): libro inexistente.** El sistema ofrece crearlo (si es administrador).
  - **A4 (paso 2): bibliotecario intenta cargar para otra sede.** Rechaza.

### CU-CAT-03. Modificar un ejemplar

- **Actor:** Bibliotecario (su sede), Administrador.
- **Flujo normal:** edita el estado físico u observaciones; el sistema guarda y registra el cambio.
- **Flujos alternativos:**
  - **A1:** no se edita directamente el estado de disponibilidad: lo cambian los procesos de préstamo, envío y devolución.
  - **A2:** cambiar el código a uno existente; rechaza.

### CU-CAT-04. Dar de baja un ejemplar

- **Actor:** Bibliotecario (su sede), Administrador.
- **Flujo normal:** selecciona el ejemplar, ingresa motivo; el sistema verifica que esté `Disponible` y sin reserva, y lo pasa a `Baja`.
- **Flujos alternativos:**
  - **A1:** está `Prestado`, `En tránsito` o `Reservado`; bloquea la baja e indica el motivo.
  - **A2:** la baja por extravío o destrucción se genera como resultado del cierre de un envío o una devolución (ver [Remitos](05-remitos.md) y [Devoluciones](07-devoluciones.md)).

### CU-CAT-05. Consultar disponibilidad

- **Actores:** todos los roles.
- **Flujo normal:**
  1. Ingresa un criterio (título, autor, ISBN o categoría).
  2. El sistema lista los libros coincidentes.
  3. Al abrir un libro, muestra por sede activa: ejemplares totales, disponibles, prestados, reservados y en tránsito.
- **Flujos alternativos:**
  - **A1:** sin coincidencias; informa que no hay resultados.
  - **A2:** el libro no tiene disponibles en ninguna sede; el sistema ofrece reservar (ver [Reservas](06-reservas.md)).
  - **A3:** hay disponibles solo en otra sede; el sistema señala que, al solicitarlo, se tramitará como préstamo interbibliotecario (ver [Préstamos](04-prestamos.md), CU-PRE-00).
  - **A4:** el estado físico detallado y el historial se muestran solo al personal.

### CU-CAT-06. Trasladar un ejemplar a otra sede

- **Actor:** Bibliotecario de la sede origen, Administrador.
- **Flujo normal:** selecciona el ejemplar y la sede destino; el sistema genera un remito de traslado (ver [Remitos](05-remitos.md)); al recibirse, cambia la sede propietaria.
- **Flujos alternativos:**
  - **A1:** ejemplar no `Disponible`; rechaza.
  - **A2:** sede destino en `Baja`; rechaza.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-CAT-01 | RF-CAT-02 | **Dado** un libro con ISBN X, **cuando** se da de alta otro con ISBN X, **entonces** se rechaza. |
| CA-CAT-02 | RF-CAT-03 | **Dado** un ejemplar con código C1 en cualquier sede, **cuando** se da de alta otro con C1, **entonces** se rechaza. |
| CA-CAT-03 | RF-CAT-03 | **Dado** dos ejemplares del mismo libro con códigos distintos, **cuando** se registran, **entonces** ambos se aceptan. |
| CA-CAT-04 | RF-CAT-03 | **Dado** una sede en `Baja`, **cuando** se intenta dar de alta un ejemplar en ella, **entonces** se rechaza. |
| CA-CAT-05 | RF-CAT-04 | **Dado** un bibliotecario de la sede A, **cuando** intenta modificar un ejemplar de la sede B, **entonces** se rechaza. |
| CA-CAT-06 | RF-CAT-06 | **Dado** un ejemplar, **cuando** cambia su estado, **entonces** el historial registra estado anterior, nuevo, fecha y usuario. |
| CA-CAT-07 | RF-CAT-07 | **Dado** un ejemplar `Prestado`, **cuando** se pide su baja, **entonces** se bloquea. |
| CA-CAT-08 | RF-CAT-07 | **Dado** un ejemplar `Disponible` sin reserva, **cuando** se da de baja con motivo, **entonces** pasa a `Baja` y deja de contarse como disponible. |
| CA-CAT-09 | RF-CAT-08 | **Dado** un libro con ejemplares, **cuando** se intenta eliminarlo, **entonces** se rechaza. |
| CA-CAT-10 | RF-CAT-09 | **Dado** un libro con 3 ejemplares en la sede A (1 disponible, 1 prestado, 1 en tránsito), **cuando** se consulta, **entonces** el detalle de A muestra 3 totales, 1 disponible, 1 prestado y 1 en tránsito. |
| CA-CAT-11 | RF-CAT-10 | **Dado** un libro con ejemplares disponibles solo en una sede en `Baja`, **cuando** se consulta, **entonces** figura sin disponibilidad. |
| CA-CAT-12 | RF-CAT-11 | **Dado** un traslado recibido, **cuando** se cierra el remito, **entonces** la sede propietaria del ejemplar es la de destino. |
