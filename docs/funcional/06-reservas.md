# 06. Reservas

Origen: [negocio/06-reservas.md](../negocio/06-reservas.md). Proceso obligatorio 7.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-RES-01 | El sistema debe permitir al socio y al bibliotecario (en nombre del socio) reservar un libro sin ejemplares disponibles en la sede de retiro elegida. | Obligatorio |
| RF-RES-02 | La reserva debe ser sobre el libro (cualquier ejemplar) y registrar socio, libro, sede de retiro, fecha y hora, y estado. | Obligatorio |
| RF-RES-03 | El sistema debe rechazar la reserva de un socio `Inhabilitado`. | Obligatorio |
| RF-RES-04 | El sistema debe rechazar la reserva con una sede de retiro en `Baja`. | Obligatorio |
| RF-RES-05 | El sistema debe rechazar una segunda reserva activa del mismo libro por el mismo socio y limitar las reservas activas por socio al máximo configurado (3). | Obligatorio |
| RF-RES-06 | La cola de reservas de cada libro debe ordenarse por fecha y hora (FIFO). | Obligatorio |
| RF-RES-07 | Al quedar disponible un ejemplar, el sistema debe asignarlo a la primera reserva elegible de la cola: la reserva pasa a `Disponible para retiro` y el ejemplar a `Reservado`. | Obligatorio |
| RF-RES-08 | Si el ejemplar asignado está en una sede distinta de la de retiro, la reserva debe cumplirse con un préstamo interbibliotecario. | Obligatorio |
| RF-RES-09 | La reserva `Disponible para retiro` debe vencer a los 3 días; al vencer pasa a `Vencida` y el ejemplar se asigna a la siguiente reserva. | Obligatorio |
| RF-RES-10 | El sistema debe permitir cancelar una reserva `Pendiente` o `Disponible para retiro`. | Obligatorio |
| RF-RES-11 | Al entregar el ejemplar reservado, la reserva debe pasar a `Cumplida` y generar el préstamo. | Obligatorio |
| RF-RES-12 | El sistema debe permitir consultar la cola de un libro (personal) y las reservas propias (socio). | Obligatorio |

## Casos de uso

### CU-RES-01. Reservar un libro

- **Actores:** Socio, Bibliotecario.
- **Flujo normal:**
  1. Busca el libro y comprueba que no hay ejemplares disponibles en la sede de retiro.
  2. Elige la sede de retiro y confirma.
  3. El sistema valida las reglas.
  4. Crea la reserva `Pendiente` con fecha y hora, y informa la posición en la cola.
- **Flujos alternativos:**
  - **A1 (paso 1): hay ejemplares disponibles en la sede de retiro.** El sistema indica que corresponde un préstamo y no permite reservar.
  - **A2 (paso 3): socio inhabilitado.** Rechaza.
  - **A3 (paso 3): sede de retiro en `Baja`.** Rechaza.
  - **A4 (paso 3): reserva duplicada o máximo alcanzado.** Rechaza.
  - **A5 (paso 3): el libro no tiene ejemplares activos en la red.** Rechaza.

### CU-RES-02. Asignar un ejemplar liberado

- **Actor:** Sistema.
- **Disparador:** un ejemplar pasa a `Disponible` (devolución, anulación de un envío, baja de una reserva vencida).
- **Flujo normal:**
  1. Busca la primera reserva `Pendiente` del libro, en orden FIFO, de un socio habilitado y con sede de retiro activa.
  2. Asigna el ejemplar: reserva `Disponible para retiro`, ejemplar `Reservado`; fija la fecha de vencimiento del retiro.
  3. Si el ejemplar está en otra sede, inicia el préstamo interbibliotecario hacia la sede de retiro.
- **Flujos alternativos:**
  - **A1 (paso 1): el primero de la cola está inhabilitado.** Se salta a la siguiente reserva elegible; la primera se mantiene.
  - **A2 (paso 1): no hay reservas.** El ejemplar queda `Disponible`.
  - **A3 (paso 1): la sede de retiro está en `Baja`.** La reserva se cancela y se pasa a la siguiente.

### CU-RES-03. Retirar un ejemplar reservado

- **Actor:** Bibliotecario.
- **Flujo normal:** identifica al socio, entrega el ejemplar reservado; el sistema pasa la reserva a `Cumplida` y crea el préstamo `Activo`.
- **Flujos alternativos:**
  - **A1:** el socio quedó inhabilitado; la entrega se rechaza hasta que se rehabilite (si la reserva vence antes, aplica CU-RES-04).
  - **A2:** la reserva está vencida; rechaza.

### CU-RES-04. Vencer una reserva no retirada

- **Actor:** Sistema.
- **Flujo normal:** pasada la vigencia, la reserva pasa a `Vencida`, el ejemplar queda libre y se vuelve a ejecutar la asignación (CU-RES-02).

### CU-RES-05. Cancelar una reserva

- **Actores:** Socio (propia), Bibliotecario.
- **Flujo normal:** selecciona la reserva y confirma; pasa a `Cancelada`.
- **Flujos alternativos:**
  - **A1:** la reserva estaba `Disponible para retiro`; el ejemplar se libera y se reasigna (CU-RES-02).
  - **A2:** la reserva ya está `Cumplida` o `Vencida`; no se puede cancelar.
  - **A3:** un socio intenta cancelar la de otro; rechaza.

### CU-RES-06. Consultar reservas

- **Actores:** Socio (propias), Bibliotecario y Administrador (cola por libro).
- **Flujo normal:** ve estado, posición en la cola y vencimiento de retiro.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-RES-01 | RF-RES-01 | **Dado** un libro con ejemplares disponibles en la sede de retiro, **cuando** se intenta reservar, **entonces** se rechaza indicando que corresponde un préstamo. |
| CA-RES-02 | RF-RES-03 | **Dado** un socio `Inhabilitado`, **cuando** intenta reservar, **entonces** se rechaza. |
| CA-RES-03 | RF-RES-04 | **Dado** una sede de retiro en `Baja`, **cuando** se reserva, **entonces** se rechaza. |
| CA-RES-04 | RF-RES-05 | **Dado** una reserva activa del libro X del socio, **cuando** reserva X nuevamente, **entonces** se rechaza. |
| CA-RES-05 | RF-RES-05 | **Dado** un socio con 3 reservas activas, **cuando** hace una cuarta, **entonces** se rechaza. |
| CA-RES-06 | RF-RES-06 | **Dado** tres reservas del mismo libro creadas en orden A, B, C, **cuando** se libera un ejemplar, **entonces** se asigna a A. |
| CA-RES-07 | RF-RES-07 | **Dado** un ejemplar liberado, **cuando** se asigna, **entonces** la reserva queda `Disponible para retiro` y el ejemplar `Reservado`. |
| CA-RES-08 | RF-RES-07 | **Dado** que la primera reserva es de un socio inhabilitado, **cuando** se libera un ejemplar, **entonces** se asigna a la siguiente elegible. |
| CA-RES-09 | RF-RES-08 | **Dado** un ejemplar liberado en la sede A y una reserva con retiro en B, **cuando** se asigna, **entonces** se inicia un préstamo interbibliotecario hacia B. |
| CA-RES-10 | RF-RES-09 | **Dado** una reserva `Disponible para retiro` con 3 días cumplidos sin retiro, **cuando** corre el vencimiento, **entonces** pasa a `Vencida` y el ejemplar se asigna a la siguiente. |
| CA-RES-11 | RF-RES-10 | **Dado** una reserva `Cumplida`, **cuando** se intenta cancelar, **entonces** se rechaza. |
| CA-RES-12 | RF-RES-11 | **Dado** una reserva `Disponible para retiro`, **cuando** se entrega el ejemplar, **entonces** la reserva queda `Cumplida` y existe un préstamo `Activo`. |
| CA-RES-13 | RF-RES-12 | **Dado** un socio, **cuando** consulta reservas, **entonces** ve solo las propias con su posición en la cola. |
