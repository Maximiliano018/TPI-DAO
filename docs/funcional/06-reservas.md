# 06. Reservas

Origen: [negocio/06-reservas.md](../negocio/06-reservas.md). Proceso obligatorio 7.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-RES-01 | El sistema debe permitir al socio (solo para sí) y al bibliotecario (en nombre del socio) reservar un libro sin ejemplares disponibles en la red. Si hay disponibles en la sede de retiro corresponde un préstamo local; si hay en otra sede activa, un préstamo entre sedes. | Obligatorio |
| RF-RES-02 | La reserva debe ser sobre el libro (cualquier ejemplar) y registrar socio, libro, sede de retiro, fecha y hora, y estado. | Obligatorio |
| RF-RES-03 | El sistema debe rechazar la reserva de un socio `Inhabilitado`. | Obligatorio |
| RF-RES-04 | El sistema debe rechazar la reserva con una sede de retiro en `Baja`. | Obligatorio |
| RF-RES-05 | El sistema debe rechazar una segunda reserva activa del mismo libro por el mismo socio y limitar las reservas activas por socio al máximo configurado (3). | Obligatorio |
| RF-RES-06 | La cola de reservas de cada libro debe ordenarse por fecha y hora (FIFO). | Obligatorio |
| RF-RES-07 | Al quedar disponible un ejemplar, el sistema debe asignarlo a la primera reserva elegible de la cola: la reserva pasa a `Disponible para retiro` y el ejemplar a `Reservado`. Es elegible el socio habilitado que puede recibir otro préstamo (no llegó al máximo ni tiene en curso el mismo libro); los demás siguen esperando en su lugar. | Obligatorio |
| RF-RES-08 | Si el ejemplar asignado está en una sede distinta de la de retiro, la reserva debe cumplirse con un préstamo interbibliotecario. | Obligatorio |
| RF-RES-09 | La reserva `Disponible para retiro` debe vencer a los 3 días; al vencer pasa a `Vencida` y el ejemplar se asigna a la siguiente reserva. | Obligatorio |
| RF-RES-10 | El sistema debe permitir cancelar una reserva `Pendiente` o `Disponible para retiro`, con un motivo opcional. | Obligatorio |
| RF-RES-11 | Al entregar el ejemplar reservado en la sede de retiro, la reserva debe pasar a `Cumplida` y generar el préstamo. En el caso entre sedes (RF-RES-08), la reserva se cumple al generarse el préstamo interbibliotecario. | Obligatorio |
| RF-RES-12 | El sistema debe permitir consultar la cola de un libro en orden de llegada (personal), las reservas por sede de retiro (personal) y las reservas propias (socio). | Obligatorio |
| RF-RES-13 | Al dar de alta un ejemplar, el sistema debe ofrecerlo a la cola de reservas del libro como a un ejemplar liberado. | Obligatorio |
| RF-RES-14 | Lo que hace la cola automáticamente (asignar, generar el préstamo entre sedes, vencer y cancelar) debe registrarse a nombre del sistema, no de quien liberó el ejemplar. | Obligatorio |
| RF-RES-15 | Una reserva solo la cancela el socio (la propia), el bibliotecario de la sede de retiro o el administrador (que opera en cualquier sede, RF-ACC-13). Un socio no puede reservar a nombre de otro. | Obligatorio |
| RF-RES-16 | El sistema debe registrar quién hizo la reserva y el historial de solo inserción de cada cambio de estado (fecha, autor y motivo). El socio ve como autor «Vos», «Personal de la biblioteca» o «Sistema». | Obligatorio |
| RF-RES-17 | Si el libro se queda sin ejemplares activos en la red y no hay un extravío sin resolver, el sistema debe cancelar sus reservas pendientes con el motivo «El libro ya no tiene ejemplares en la red». | Obligatorio |

## Casos de uso

### CU-RES-01. Reservar un libro

- **Actores:** Socio, Bibliotecario. El administrador puede hacerlo en cualquier sede (RF-ACC-13).
- **Flujo normal:**
  1. Busca el libro y comprueba que no hay ejemplares disponibles en la red.
  2. Elige la sede de retiro y confirma.
  3. El sistema valida las reglas.
  4. Crea la reserva `Pendiente` con fecha y hora, y informa la posición en la cola.
- **Flujos alternativos:**
  - **A1 (paso 1): hay ejemplares disponibles en la sede de retiro.** El sistema indica que corresponde un préstamo y no permite reservar.
  - **A2 (paso 3): socio inhabilitado o dado de baja.** Rechaza.
  - **A3 (paso 3): sede de retiro en `Baja`.** Rechaza.
  - **A4 (paso 3): reserva duplicada o máximo alcanzado.** Rechaza.
  - **A5 (paso 3): el libro no tiene ejemplares activos en la red.** Rechaza.
  - **A6 (paso 3): un socio indica otro socio.** Rechaza (403).
  - **A7 (paso 1): hay ejemplares disponibles en otra sede.** El sistema indica que corresponde un préstamo entre sedes y no permite reservar. La ficha del libro solo ofrece «Reservar» cuando no hay disponibles en la red.

### CU-RES-02. Asignar un ejemplar liberado

- **Actor:** Sistema.
- **Disparador:** un ejemplar pasa a `Disponible` (alta, devolución, anulación de un envío, cancelación de un préstamo, reparación, recuperación, retorno, o una reserva vencida o cancelada).
- **Flujo normal:**
  1. Busca la primera reserva `Pendiente` del libro, en orden FIFO, de un socio habilitado que puede recibir otro préstamo y con sede de retiro activa.
  2. Si el ejemplar está en la sede de retiro: reserva `Disponible para retiro`, ejemplar `Reservado`, con la fecha de vencimiento del retiro.
  3. Si está en otra sede: crea el préstamo interbibliotecario hacia la sede de retiro, a nombre del sistema (el ejemplar queda `Apartado`), y la reserva pasa directamente a `Cumplida`: sigue como préstamo.
- **Flujos alternativos:**
  - **A1 (paso 1): el primero de la cola está inhabilitado o dado de baja, o ya tiene el máximo de préstamos o el mismo libro en curso.** Se salta a la siguiente reserva elegible; la primera se mantiene.
  - **A2 (paso 1): no hay reservas.** El ejemplar queda `Disponible`.
  - **A3 (paso 1): la sede de retiro está en `Baja`.** La reserva se cancela y se pasa a la siguiente.
- **Autor:** todo lo que hace este caso de uso queda a nombre del sistema (RF-RES-14).

### CU-RES-03. Retirar un ejemplar reservado

- **Actor:** Bibliotecario de la sede de retiro. El administrador puede hacerlo en cualquier sede (RF-ACC-13).
- **Flujo normal:** identifica al socio, entrega el ejemplar reservado; el sistema pasa la reserva a `Cumplida` y crea el préstamo `Activo`.
- **Flujos alternativos:**
  - **A1:** el socio quedó inhabilitado; la entrega se rechaza hasta que se rehabilite (si la reserva vence antes, aplica CU-RES-04).
  - **A2:** la reserva está vencida; rechaza.
  - **A3:** un bibliotecario de otra sede; rechaza.

### CU-RES-04. Vencer una reserva no retirada

- **Actor:** Sistema (tarea diaria a las 00:05 y al iniciar el sistema); el administrador también puede ejecutarla.
- **Flujo normal:** pasada la vigencia, la reserva pasa a `Vencida`, el ejemplar queda libre y se vuelve a ejecutar la asignación (CU-RES-02).

### CU-RES-05. Cancelar una reserva

- **Actores:** Socio (propia), Bibliotecario (de la sede de retiro). El administrador puede hacerlo en cualquier sede (RF-ACC-13).
- **Flujo normal:** selecciona la reserva, indica un motivo opcional y confirma; pasa a `Cancelada` y el motivo queda en el historial.
- **Flujos alternativos:**
  - **A1:** la reserva estaba `Disponible para retiro`; el ejemplar se libera y se reasigna (CU-RES-02).
  - **A2:** la reserva ya está `Cumplida` o `Vencida`; no se puede cancelar.
  - **A3:** un socio intenta cancelar la de otro; rechaza (no la ve).
  - **A4:** un bibliotecario de otra sede intenta cancelarla; rechaza (403). El administrador sí puede.

### CU-RES-06. Consultar reservas

- **Actores:** Socio (propias), Bibliotecario y Administrador (cola por libro).
- **Flujo normal:** ve estado, posición en la cola, vencimiento de retiro e historial. El personal ve la cola de cada libro en su ficha y filtra el listado por sede de retiro (el bibliotecario ve por defecto la suya).

### CU-RES-07. Cancelar las reservas de un libro sin ejemplares

- **Actor:** Sistema.
- **Disparador:** se da de baja (o se recibe destruido) un ejemplar.
- **Flujo normal:** si el libro no tiene ejemplares activos en la red, cancela sus reservas pendientes con el motivo «El libro ya no tiene ejemplares en la red».
- **Flujos alternativos:**
  - **A1:** queda algún ejemplar activo o un extravío sin resolver; las reservas siguen esperando.

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
| CA-RES-14 | RF-RES-01 | **Dado** un libro sin disponibles en la sede de retiro pero con disponibles en otra sede activa, **cuando** se intenta reservar, **entonces** se rechaza indicando que corresponde un préstamo entre sedes. |
| CA-RES-15 | RF-RES-13 | **Dado** una reserva pendiente de un libro, **cuando** se da de alta un ejemplar en la sede de retiro, **entonces** queda `Reservado` y la reserva `Disponible para retiro`. |
| CA-RES-16 | RF-RES-14 | **Dado** que un socio cancela su reserva ya asignada, **cuando** el ejemplar pasa a la siguiente reserva, **entonces** la asignación y el préstamo que genera figuran a nombre del sistema. |
| CA-RES-17 | RF-RES-15 | **Dado** una reserva que se retira en la sede B, **cuando** intenta cancelarla un bibliotecario de otra sede, **entonces** se rechaza; el de la sede B o el administrador la cancelan. |
| CA-RES-18 | RF-RES-15 | **Dado** un socio, **cuando** reserva indicando otro socio, **entonces** se rechaza. |
| CA-RES-19 | RF-RES-16 | **Dado** una reserva registrada por un bibliotecario y cancelada por el socio, **cuando** se consulta, **entonces** muestra quién la registró y cada cambio con su autor y motivo. |
| CA-RES-20 | RF-RES-07 | **Dado** que el primero de la cola ya tiene el máximo de préstamos, **cuando** se libera un ejemplar, **entonces** se asigna al siguiente y el primero conserva su lugar. |
| CA-RES-21 | RF-RES-17 | **Dado** un libro con reservas pendientes y un único ejemplar, **cuando** ese ejemplar se da de baja, **entonces** las reservas se cancelan a nombre del sistema; con un extravío sin resolver, siguen esperando. |
| CA-RES-22 | RF-RES-12 | **Dado** varias reservas pendientes de un libro, **cuando** el personal consulta la cola, **entonces** las ve en orden de llegada y puede filtrarlas por sede de retiro. |
