# 04. Préstamos

Origen: [negocio/04-prestamos.md](../negocio/04-prestamos.md). Proceso obligatorio 4 (y consulta de disponibilidad, proceso 6, en [Catálogo](03-catalogo.md)).

> Hay dos caminos, habilitados por permiso: el **bibliotecario** registra el préstamo en el mostrador en nombre del socio, eligiendo el ejemplar (CU-PRE-01 y 02), y el **socio** lo pide para sí desde su cuenta, eligiendo el libro: el sistema decide el tipo y el ejemplar (CU-PRE-00).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-PRE-01 | El sistema debe permitir al bibliotecario registrar una solicitud de préstamo de un ejemplar para un socio, local (origen = destino) o interbibliotecario (origen ≠ destino). | Obligatorio |
| RF-PRE-02 | El préstamo debe referenciar un único ejemplar. Si el socio se lleva varios libros, se registra un préstamo por ejemplar. | Obligatorio |
| RF-PRE-03 | El sistema debe rechazar el préstamo de un ejemplar que no esté `Disponible`. | Obligatorio |
| RF-PRE-04 | El sistema debe rechazar el préstamo a un socio `Inhabilitado`. | Obligatorio |
| RF-PRE-05 | El sistema debe rechazar el préstamo de un ejemplar que no pertenezca a la sede origen del préstamo. | Obligatorio |
| RF-PRE-06 | El sistema debe rechazar préstamos con una sede en `Baja` como origen o destino. | Obligatorio |
| RF-PRE-07 | El sistema debe rechazar el préstamo que supere el máximo de préstamos simultáneos del socio, o que repita un libro que el socio ya tiene prestado. | Obligatorio |
| RF-PRE-08 | Al registrar un préstamo válido, el sistema debe apartar el ejemplar para que no pueda pedirlo otro socio. | Obligatorio |
| RF-PRE-09 | El préstamo debe iniciar al **entregar** el ejemplar al socio: calculando la fecha de vencimiento (plazo local o interbibliotecario) y pasando el ejemplar a `Prestado`. En el interbibliotecario, el tiempo de traslado no consume el plazo. | Obligatorio |
| RF-PRE-10 | Los préstamos interbibliotecarios deben generar el envío con remito (ver [Remitos](05-remitos.md)) y pasar a `En envío`. | Obligatorio |
| RF-PRE-11 | El sistema debe gestionar el ciclo de vida del préstamo: `Solicitado → En envío → Activo → Devuelto`, con `Vencido` y `Cancelado`, sin transiciones inválidas, y registrar cada cambio. | Obligatorio |
| RF-PRE-12 | El sistema debe detectar los préstamos cuya fecha de vencimiento pasó sin devolución y marcarlos `Vencido`. | Obligatorio |
| RF-PRE-13 | El sistema debe permitir cancelar un préstamo antes de la entrega, liberando el ejemplar. | Obligatorio |
| RF-PRE-14 | El sistema debe permitir renovar un préstamo `Activo` hasta el máximo configurado, si no está vencido y no hay reservas pendientes sobre el libro. | Obligatorio |
| RF-PRE-15 | El sistema debe permitir consultar el estado y el historial de un préstamo, con el estado del remito en los interbibliotecarios. | Obligatorio |
| RF-PRE-16 | El sistema debe permitir al socio pedir un préstamo **para sí** indicando el libro y la sede de retiro (por defecto, su sede de alta). El sistema elige el ejemplar: si hay `Disponible` en la sede de retiro, el préstamo es local; si no, es interbibliotecario desde la sede activa con más disponibles (con empate, la de menor id). | Obligatorio |
| RF-PRE-17 | Antes de confirmar, el sistema debe mostrar al socio la propuesta (tipo, sede origen y destino, plazo) sin apartar nada. Si al confirmar la sede origen cambió, debe rechazar e informar la nueva propuesta. | Obligatorio |
| RF-PRE-18 | El sistema debe validar las reglas del socio (habilitado, máximo de préstamos, libro repetido) antes de evaluar la disponibilidad. | Obligatorio |
| RF-PRE-19 | Si ninguna sede activa tiene ejemplares disponibles del libro, el sistema debe rechazar la solicitud sin crear nada y ofrecer una reserva. | Obligatorio |
| RF-PRE-20 | Un préstamo sin entregar debe tener un plazo de retiro (parámetro, 3 días): el local desde la solicitud y el interbibliotecario desde la llegada a la sede destino. Vencido, el sistema debe cancelarlo: el local libera el ejemplar y el interbibliotecario vuelve a su sede con un remito de retorno. | Obligatorio |
| RF-PRE-21 | El socio debe poder cancelar sus propios préstamos mientras estén `Solicitado`. | Obligatorio |
| RF-PRE-22 | El socio debe ver sus préstamos sin la identidad del personal: el autor de cada movimiento se muestra como «Vos», «Personal de la biblioteca» o «Sistema». | Obligatorio |

## Casos de uso

### CU-PRE-00. Pedir un préstamo (socio)

- **Actor:** Socio (permiso `PRESTAMO_SOLICITAR_PROPIO`).
- **Flujo normal:**
  1. Desde la ficha de un libro, el socio elige «Pedir préstamo».
  2. El sistema propone la sede de retiro (su sede de alta); el socio puede elegir otra sede activa.
  3. El sistema valida al socio y arma la propuesta: local si hay disponibles en la sede de retiro; si no, interbibliotecario desde la sede con más disponibles.
  4. El socio ve el tipo, las sedes y los plazos, y confirma.
  5. El sistema vuelve a asignar el ejemplar dentro de la misma operación, crea el préstamo `Solicitado` a nombre del socio de la sesión y aparta el ejemplar. Un local queda con fecha límite de retiro.
- **Flujos alternativos:**
  - **A1 (paso 3): socio inhabilitado, máximo alcanzado o libro repetido.** Rechaza e informa el motivo, sin evaluar la disponibilidad.
  - **A2 (paso 3): sin disponibles en la red.** Rechaza y ofrece reservar (CU-RES-01).
  - **A3 (paso 5): la sede origen cambió por otra operación.** Rechaza e informa la nueva propuesta para que la confirme.
  - **A4: pedido a nombre de otro socio.** Rechaza por falta de permiso.
- **Postcondición:** préstamo `Solicitado` del tipo que eligió el sistema, o sin cambios.

### CU-PRE-01. Registrar un préstamo local

- **Actor:** Bibliotecario.
- **Precondición:** el socio existe y el bibliotecario está en una sede activa.
- **Flujo normal:**
  1. Identifica al socio y busca el libro.
  2. Elige un ejemplar `Disponible` de su propia sede (origen = destino).
  3. El sistema valida todas las reglas.
  4. Registra el préstamo `Solicitado` y aparta el ejemplar.
  5. El bibliotecario entrega el ejemplar y confirma.
  6. El sistema pasa el préstamo a `Activo`, el ejemplar a `Prestado` y calcula el vencimiento.
- **Flujos alternativos:**
  - **A1 (paso 3): socio inhabilitado.** Rechaza e informa el motivo.
  - **A2 (paso 3): máximo de préstamos alcanzado o libro repetido.** Rechaza.
  - **A3 (paso 2): sin ejemplares disponibles en la sede.** Ofrece préstamo interbibliotecario (CU-PRE-02) o reserva (CU-RES-01).
  - **A4 (paso 3): ejemplar no disponible por otra operación simultánea.** Rechaza y pide elegir otro.
  - **A5 (paso 5): el socio no retira el ejemplar.** El bibliotecario cancela (CU-PRE-05) o, vencido el plazo de retiro, el sistema lo cancela solo (CU-PRE-07); el ejemplar vuelve a `Disponible`.
- **Postcondición:** préstamo `Activo` con vencimiento; ejemplar `Prestado`.

### CU-PRE-02. Registrar un préstamo interbibliotecario

- **Actor:** Bibliotecario de la sede destino (donde está el socio).
- **Flujo normal:**
  1. Identifica al socio y al libro; el sistema no encuentra disponibles en la sede, pero sí en otra sede activa.
  2. Elige un ejemplar `Disponible` de la sede origen.
  3. El sistema valida las reglas, incluidas ambas sedes activas y la pertenencia del ejemplar a la sede origen.
  4. Registra el préstamo `Solicitado` y aparta el ejemplar.
  5. La sede origen prepara el envío (CU-REM-01) y el préstamo pasa a `En envío`.
  6. La sede destino recibe el remito (CU-REM-04).
  7. El bibliotecario destino entrega el ejemplar al socio; el sistema pasa el préstamo a `Activo`, el ejemplar a `Prestado` y calcula el vencimiento con el plazo interbibliotecario desde esa entrega.
- **Flujos alternativos:**
  - **A1 (paso 3): sede origen o destino en `Baja`.** Rechaza.
  - **A2 (paso 3): ejemplar de otra sede distinta de la origen.** Rechaza.
  - **A3 (paso 3): socio inhabilitado, máximo alcanzado o ejemplar no disponible.** Rechaza (mismos criterios que CU-PRE-01).
  - **A4 (pasos 5-6): el remito se anula antes del despacho.** El préstamo pasa a `Cancelado` y el ejemplar vuelve a `Disponible`.
  - **A5 (paso 6): el remito termina `Extraviado`, `Dañado` o `Destruido`.** El préstamo pasa a `Cancelado`, se registra la incidencia sobre el ejemplar (ver [Remitos](05-remitos.md)) y se informa al socio.
  - **A6 (paso 7): el socio no retira.** El bibliotecario cancela; el ejemplar vuelve a la sede origen por remito de retorno.
- **Postcondición:** préstamo `Activo` con remito de ida asociado.

### CU-PRE-03. Renovar un préstamo

- **Actor:** Bibliotecario.
- **Flujo normal:** selecciona el préstamo `Activo`; el sistema valida y extiende el vencimiento con un nuevo plazo, sumando una renovación.
- **Flujos alternativos:**
  - **A1:** préstamo `Vencido`; rechaza.
  - **A2:** hay reservas pendientes del libro; rechaza.
  - **A3:** alcanzó el máximo de renovaciones; rechaza.

### CU-PRE-04. Detectar préstamos vencidos

- **Actor:** Sistema (proceso periódico o al consultar).
- **Flujo normal:**
  1. El sistema identifica préstamos `Activo` con vencimiento anterior a hoy.
  2. Los pasa a `Vencido` y registra el cambio.
  3. Inhabilita al socio (ver [Socios](02-socios.md), CU-SOC-03).
- **Flujo alternativo A1:** el socio devuelve el mismo día del vencimiento; no se considera vencido.

### CU-PRE-05. Cancelar un préstamo

- **Actores:** Bibliotecario (de la sede origen o destino), Socio (los propios, solo `Solicitado`).
- **Flujo normal:** selecciona un préstamo `Solicitado`, confirma; pasa a `Cancelado` y el ejemplar vuelve a `Disponible`.
- **Flujos alternativos:**
  - **A0:** el socio intenta cancelar un préstamo que ya salió de la sede origen; se rechaza (lo maneja el personal). Un préstamo ajeno responde como inexistente.
  - **A1:** préstamo `En envío` con remito ya despachado; no se cancela, se espera la recepción y se devuelve.
  - **A2:** préstamo `Activo` o posterior; no se puede cancelar, solo devolver.

### CU-PRE-07. Cancelar préstamos no retirados

- **Actor:** Sistema (tarea diaria); el administrador también puede ejecutarla.
- **Flujo normal:** busca los préstamos `Solicitado` o `En envío` cuya fecha límite de retiro pasó y los cancela. Un local libera el ejemplar y lo ofrece a la cola de reservas; un interbibliotecario que ya llegó vuelve a su sede con un remito de retorno. El historial lo registra como «Sistema».

### CU-PRE-06. Consultar un préstamo

- **Actores:** Bibliotecario, Administrador, Socio (los propios).
- **Flujo normal:** busca por número, socio o ejemplar; el sistema muestra estado, fechas (incluida la límite de retiro), historial y remito asociado. El socio no ve la identidad del personal.
- **Flujo alternativo A1:** el bibliotecario consulta préstamos de otra sede donde no es origen ni destino; el sistema lo rechaza.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-PRE-01 | RF-PRE-03 | **Dado** un ejemplar `Prestado`, **cuando** se intenta prestar, **entonces** se rechaza. |
| CA-PRE-02 | RF-PRE-04 | **Dado** un socio `Inhabilitado`, **cuando** se registra un préstamo, **entonces** se rechaza. |
| CA-PRE-03 | RF-PRE-05 | **Dado** un ejemplar de la sede B, **cuando** se registra un préstamo con origen A, **entonces** se rechaza. |
| CA-PRE-04 | RF-PRE-06 | **Dado** una sede destino en `Baja`, **cuando** se registra un préstamo, **entonces** se rechaza. |
| CA-PRE-05 | RF-PRE-06 | **Dado** una sede origen en `Baja`, **cuando** se registra un préstamo, **entonces** se rechaza. |
| CA-PRE-06 | RF-PRE-07 | **Dado** un socio con 3 préstamos activos, **cuando** se registra otro, **entonces** se rechaza. |
| CA-PRE-07 | RF-PRE-08 | **Dado** un préstamo `Solicitado` sobre un ejemplar, **cuando** otro socio intenta pedir ese ejemplar, **entonces** se rechaza. |
| CA-PRE-08 | RF-PRE-09 | **Dado** un préstamo local entregado el día D con plazo de 14 días, **cuando** queda `Activo`, **entonces** el vencimiento es D + 14. |
| CA-PRE-09 | RF-PRE-09 | **Dado** un préstamo interbibliotecario, **cuando** el destino entrega el ejemplar el día E, **entonces** el vencimiento es E + 21, sin contar el tiempo de traslado. |
| CA-PRE-10 | RF-PRE-01 | **Dado** un préstamo local, **cuando** se registra, **entonces** sede origen y destino son iguales. |
| CA-PRE-11 | RF-PRE-10 | **Dado** un préstamo interbibliotecario válido, **cuando** se confirma el envío, **entonces** existe un remito asociado y el préstamo está `En envío`. |
| CA-PRE-12 | RF-PRE-11 | **Dado** un préstamo `Devuelto`, **cuando** se intenta pasarlo a `Activo`, **entonces** se rechaza. |
| CA-PRE-13 | RF-PRE-12 | **Dado** un préstamo `Activo` con vencimiento ayer, **cuando** corre la detección, **entonces** pasa a `Vencido` y el socio queda inhabilitado. |
| CA-PRE-14 | RF-PRE-12 | **Dado** un préstamo que vence hoy, **cuando** corre la detección, **entonces** sigue `Activo`. |
| CA-PRE-15 | RF-PRE-13 | **Dado** un préstamo `Solicitado`, **cuando** se cancela, **entonces** el ejemplar vuelve a `Disponible`. |
| CA-PRE-16 | RF-PRE-14 | **Dado** un préstamo vencido, **cuando** se intenta renovar, **entonces** se rechaza. |
| CA-PRE-17 | RF-PRE-14 | **Dado** un libro con reservas pendientes, **cuando** se intenta renovar un préstamo suyo, **entonces** se rechaza. |
| CA-PRE-18 | RF-PRE-11 | **Dado** cualquier cambio de estado del préstamo, **cuando** ocurre, **entonces** se registra fecha, usuario y estado anterior. |
| CA-PRE-19 | RF-PRE-16 | **Dado** un libro con disponibles en la sede de alta del socio, **cuando** el socio lo pide, **entonces** se crea un préstamo local `Solicitado` a su nombre, con un ejemplar de esa sede y fecha límite de retiro hoy + 3. |
| CA-PRE-20 | RF-PRE-16 | **Dado** un libro sin disponibles en la sede de retiro, con 1 en A y 2 en C, **cuando** el socio lo pide, **entonces** se crea un préstamo interbibliotecario con origen C. |
| CA-PRE-21 | RF-PRE-16 | **Dado** un empate de disponibles entre dos sedes, **cuando** el socio pide el libro, **entonces** el origen es la sede de menor id. |
| CA-PRE-22 | RF-PRE-19 | **Dado** un libro sin disponibles en ninguna sede activa, **cuando** el socio lo pide, **entonces** se rechaza sin crear el préstamo y se ofrece reservar. |
| CA-PRE-23 | RF-PRE-18 | **Dado** un socio inhabilitado, **cuando** pide un libro (aunque no haya disponibles), **entonces** se rechaza por su estado. |
| CA-PRE-24 | RF-PRE-16 | **Dado** un socio, **cuando** pide sin indicar sede, **entonces** la sede de retiro es su sede de alta; si elige otra, el préstamo se arma para esa sede. |
| CA-PRE-25 | RF-PRE-20 | **Dado** un préstamo local sin retirar con el plazo vencido, **cuando** corre la tarea diaria, **entonces** queda `Cancelado` por «Sistema» y el ejemplar `Disponible`. |
| CA-PRE-26 | RF-PRE-20 | **Dado** un préstamo interbibliotecario que llegó a destino (con plazo de retiro desde la llegada) y no se retiró a tiempo, **cuando** corre la tarea, **entonces** queda `Cancelado` y se genera el remito de retorno. |
| CA-PRE-27 | RF-PRE-21 | **Dado** un préstamo propio `Solicitado`, **cuando** el socio lo cancela, **entonces** queda `Cancelado` y el ejemplar `Disponible`; uno ajeno no se encuentra y uno `En envío` se rechaza. |
| CA-PRE-28 | RF-PRE-17 | **Dado** una propuesta con origen A, **cuando** al confirmar el último ejemplar de A ya se prestó, **entonces** se rechaza con la nueva propuesta (origen C) y no se crea nada. |
| CA-PRE-29 | RF-PRE-22 | **Dado** un préstamo registrado por el personal, **cuando** el socio lo consulta, **entonces** no ve quién lo registró y el autor de cada movimiento es «Personal de la biblioteca»; el personal sí ve el nombre. |
| CA-PRE-30 | RF-PRE-11 | **Dado** un préstamo activo, vencido o devuelto sin fechas de inicio y vencimiento (o devuelto sin fecha de devolución), **cuando** se guarda, **entonces** la base lo rechaza. |
