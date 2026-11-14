# 03. Catálogo: libros y ejemplares

Origen: [negocio/03-catalogo.md](../negocio/03-catalogo.md). Proceso obligatorio 3 (la consulta de disponibilidad es el proceso 6).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-CAT-01 | El sistema debe permitir al administrador dar de alta y modificar libros con ISBN, título, autores, editorial, año, categoría y tipo de material. La modificación usa control de versión para no pisar cambios de otra persona. | Obligatorio |
| RF-CAT-02 | El sistema debe evitar libros duplicados por ISBN; sin ISBN, por la combinación título, autor, editorial y año. | Obligatorio |
| RF-CAT-03 | El sistema debe permitir dar de alta ejemplares con código de inventario único en toda la red, asociados a un libro y a una sede propietaria activa. | Obligatorio |
| RF-CAT-04 | El sistema debe permitir al bibliotecario administrar los ejemplares de su sede, y al administrador los de cualquier sede. | Obligatorio |
| RF-CAT-05 | Cada ejemplar debe tener estado físico (`Nuevo`, `Bueno`, `Regular`, `Dañado`), estado de disponibilidad (`Disponible`, `Apartado`, `Reservado`, `Prestado`, `En tránsito`, `En revisión`, `Baja`) y sede propietaria y actual. | Obligatorio |
| RF-CAT-06 | El sistema debe registrar en el historial del ejemplar cada cambio de estado de disponibilidad, de estado físico, de observaciones y de sede (donde está y a cuál pertenece), con fecha y responsable. | Obligatorio |
| RF-CAT-07 | El sistema debe permitir dar de baja lógica a un ejemplar `Disponible` (sin reserva asignada) o `En revisión`, registrando motivo y fecha. Un ejemplar dado de baja no se edita. | Obligatorio |
| RF-CAT-08 | El sistema no debe permitir eliminar un libro que tenga ejemplares, aunque estén dados de baja. | Obligatorio |
| RF-CAT-09 | El sistema debe permitir consultar la disponibilidad por libro, con detalle por sede (totales, disponibles, prestados, reservados y en tránsito), y buscar por título, autor, ISBN (con 6 dígitos o más), categoría o tipo de material. | Obligatorio |
| RF-CAT-10 | La consulta de catálogo debe incluir las sedes activas de toda la red; los ejemplares de sedes en `Baja` no se ofrecen. | Obligatorio |
| RF-CAT-11 | El sistema debe permitir trasladar un ejemplar a otra sede (cambio de sede propietaria) mediante remito de traslado. | Obligatorio |
| RF-CAT-12 | Cada rol debe ver del catálogo solo lo que le corresponde: la auditoría del libro (quién lo cargó y lo modificó) solo el administrador; el estado físico, el historial y la gestión de ejemplares, solo el personal. | Obligatorio |
| RF-CAT-13 | El sistema debe permitir a la sede propietaria recuperar un ejemplar dado de baja por extravío que apareció: vuelve a `Disponible` en su sede (o a `En revisión` si llegó dañado) y la incidencia queda resuelta. Una baja por destrucción o daño irreparable es definitiva. | Obligatorio |

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
  - **A3 (paso 1): libro inexistente.** El libro se busca en todo el catálogo (título, autor o ISBN); si no está, el sistema ofrece crearlo (si es administrador).
  - **A4 (paso 2): bibliotecario intenta cargar para otra sede.** Rechaza.

### CU-CAT-03. Modificar un ejemplar

- **Actor:** Bibliotecario (su sede), Administrador.
- **Flujo normal:** edita el estado físico u observaciones; el sistema guarda y registra el cambio en el historial (valor anterior y nuevo, fecha y responsable).
- **Flujos alternativos:**
  - **A1:** no se edita directamente el estado de disponibilidad: lo cambian los procesos de préstamo, envío y devolución.
  - **A2:** el código de inventario no se modifica después del alta.
  - **A3:** el ejemplar está dado de baja; rechaza.
  - **A4:** otra persona lo modificó mientras tanto; rechaza y pide recargar.

### CU-CAT-04. Dar de baja un ejemplar

- **Actor:** Bibliotecario (su sede), Administrador.
- **Flujo normal:** selecciona el ejemplar, ingresa motivo; el sistema verifica que esté `Disponible` (sin reserva) o `En revisión`, y lo pasa a `Baja`.
- **Flujos alternativos:**
  - **A1:** está `Prestado`, `Apartado`, `En tránsito` o `Reservado`; bloquea la baja e indica el motivo.
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
  - **A3:** no hay disponibles en la sede del usuario pero sí en otra; el sistema señala que se puede pedir como préstamo interbibliotecario.
  - **A4:** el estado físico detallado y el historial se muestran solo al personal; la auditoría del libro, solo al administrador.

### CU-CAT-06. Trasladar un ejemplar a otra sede

- **Actor:** Bibliotecario de la sede origen, Administrador.
- **Flujo normal:** selecciona el ejemplar y la sede destino; el sistema genera un remito de traslado (ver [Remitos](05-remitos.md)); al recibirse, cambia la sede propietaria.
- **Flujos alternativos:**
  - **A1:** ejemplar no `Disponible`; rechaza.
  - **A2:** sede destino en `Baja`; rechaza.

### CU-CAT-07. Recuperar un ejemplar extraviado

- **Actor:** Bibliotecario de la sede propietaria, Administrador.
- **Precondición:** el ejemplar está en `Baja` por un extravío (remito extraviado, faltante o devolución extraviada) cuya incidencia no se resolvió.
- **Flujo normal:** indica el estado físico y dónde apareció; el ejemplar vuelve a `Disponible` en su sede propietaria, queda en su historial, la incidencia se marca resuelta y se ofrece a la cola de reservas.
- **Flujos alternativos:**
  - **A1:** llegó dañado; queda `En revisión`.
  - **A2:** la baja no fue por extravío (destrucción, daño irreparable, depuración); rechaza.
  - **A3:** los préstamos cancelados por el extravío no se reabren.

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
| CA-CAT-13 | RF-CAT-06 | **Dado** un ejemplar `Bueno`, **cuando** se modifica a `Regular` con una observación, **entonces** el historial registra un movimiento de modificación con el valor anterior y nuevo de cada campo, la fecha y el usuario. |
| CA-CAT-14 | RF-CAT-06 | **Dado** un ejemplar que llega a otra sede con un remito, **cuando** se recibe, **entonces** el historial registra la sede donde estaba y la nueva (por nombre), el estado físico verificado y, en un traslado, el cambio de sede propietaria. |
| CA-CAT-15 | RF-CAT-07 | **Dado** un ejemplar en `Baja`, **cuando** se intenta modificar su estado físico, **entonces** se rechaza. |
| CA-CAT-16 | RF-CAT-08 | **Dado** un libro cuyos ejemplares están todos dados de baja, **cuando** el administrador lo consulta, **entonces** figura como no eliminable y la eliminación se rechaza. |
| CA-CAT-17 | RF-CAT-12 | **Dado** un libro, **cuando** lo consulta un bibliotecario o un socio, **entonces** la respuesta no incluye quién lo cargó ni quién lo modificó; el administrador sí lo ve. |
| CA-CAT-18 | RF-CAT-09 | **Dado** un libro cuyo ISBN contiene «07», **cuando** se busca «07», **entonces** no aparece (el ISBN se compara con 6 dígitos o más). |
| CA-CAT-19 | RF-CAT-01 | **Dado** un libro modificado por otra persona, **cuando** se guarda con una versión anterior, **entonces** se rechaza con conflicto de versión. |
| CA-CAT-20 | RF-CAT-13 | **Dado** un ejemplar dado de baja por faltante en un remito, **cuando** la sede propietaria lo recupera, **entonces** queda `Disponible` en su sede, sin datos de baja, con el movimiento «Recuperado» y la incidencia resuelta; otra sede no puede hacerlo. |
| CA-CAT-21 | RF-CAT-13 | **Dado** un ejemplar dado de baja por destrucción, **cuando** se intenta recuperar, **entonces** se rechaza. |
