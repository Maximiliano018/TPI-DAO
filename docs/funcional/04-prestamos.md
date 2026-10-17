# 04. Préstamos

Origen: [negocio/04-prestamos.md](../negocio/04-prestamos.md). Proceso obligatorio 4 (y consulta de disponibilidad, proceso 6, en [Catálogo](03-catalogo.md)).

> La solicitud la inicia el **bibliotecario** en nombre del socio o el **socio** por sí mismo (este último, solo para préstamos interbibliotecarios). En ambos casos el usuario inicia un único flujo, «Solicitar un préstamo» (CU-PRE-00), y el **sistema determina** si es local (CU-PRE-01) o interbibliotecario (CU-PRE-02).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-PRE-01 | El sistema debe permitir iniciar una única «solicitud de préstamo» indicando el socio y el libro. El usuario no elige el tipo (local, con origen = destino, o interbibliotecario, con origen ≠ destino) ni el ejemplar. | Obligatorio |
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
| RF-PRE-16 | El sistema debe determinar el tipo de préstamo y asignar el ejemplar según la disponibilidad. Si hay ejemplares `Disponible` del libro en la sede destino, el préstamo es local y se asigna cualquiera de ellos. Si no, el préstamo es interbibliotecario: la sede origen es la sede activa con más ejemplares disponibles del libro (con empate, la de menor id) y se asigna uno de sus ejemplares. | Obligatorio |
| RF-PRE-17 | La sede destino debe ser la asignada al bibliotecario, sin poder cambiarla, o la sede del socio cuando solicita el socio. En ese caso se propone por defecto y el socio puede cambiarla por otra sede activa antes de confirmar. | Obligatorio |
| RF-PRE-18 | Si el socio solicita un préstamo y el sistema determina que es local, debe rechazar la solicitud e indicar que se acerque al mostrador de la sede. El préstamo local solicitado por el socio queda para un evolutivo. | Obligatorio |
| RF-PRE-19 | Si el libro no tiene ejemplares disponibles en ninguna sede activa, el sistema debe rechazar la solicitud y ofrecer una reserva con retiro en la sede destino. | Obligatorio |

## Casos de uso

### CU-PRE-00. Solicitar un préstamo

- **Actores:** Bibliotecario (en nombre del socio), Socio (por sí mismo).
- **Precondición:** el socio existe y el usuario inició sesión.
- **Flujo normal:**
  1. El usuario inicia «Solicitar préstamo». El bibliotecario identifica al socio; si el actor es el socio, se toma de su sesión.
  2. El sistema propone la sede destino. Para el bibliotecario es la sede de su usuario y no se puede cambiar. Para el socio es la sede del socio, y puede cambiarla por otra sede activa.
  3. El usuario busca y elige el libro.
  4. El sistema valida que el socio esté habilitado, que no haya alcanzado el máximo de préstamos y que no tenga otro préstamo abierto del mismo libro. Valida además que la sede destino esté activa.
  5. El sistema consulta la disponibilidad del libro por sede y determina el tipo:
     - **a.** Si hay ejemplares `Disponible` en la sede destino, el préstamo es **local** y asigna cualquiera de ellos.
     - **b.** Si no, el préstamo es **interbibliotecario**: elige como origen la sede activa con más ejemplares disponibles del libro (con empate, la de menor id) y asigna uno de sus ejemplares.
  6. El sistema muestra un resumen con el tipo, la sede origen, la sede destino y el plazo, y el usuario confirma.
  7. Al confirmar, el sistema vuelve a hacer la asignación dentro de la misma operación y continúa en CU-PRE-01 (local) o CU-PRE-02 (interbibliotecario).
- **Flujos alternativos:**
  - **A1 (paso 4): socio inhabilitado, máximo alcanzado o libro repetido.** Rechaza e informa el motivo, sin evaluar la disponibilidad.
  - **A2 (paso 4): sede destino en `Baja`.** Rechaza. Al socio no se le ofrecen sedes en `Baja`.
  - **A3 (paso 5): sin ejemplares disponibles en ninguna sede activa.** Rechaza y ofrece reservar el libro con retiro en la sede destino (CU-RES-01).
  - **A4 (paso 5a): el actor es el socio y corresponde un préstamo local.** Rechaza y muestra el cartel: «Hay ejemplares disponibles en la sede {sede}. Acercate al mostrador para solicitar el préstamo». El socio puede elegir otra sede destino (vuelve al paso 2).
  - **A5 (paso 7): el ejemplar asignado dejó de estar disponible por una operación simultánea.** El sistema determina de nuevo el tipo con la disponibilidad actual. Si el resultado cambió (otro tipo u otra sede origen), vuelve al paso 6 para que el usuario confirme.
- **Postcondición:** préstamo `Solicitado` del tipo determinado por el sistema, con el ejemplar apartado; o solicitud rechazada sin cambios.

### CU-PRE-01. Registrar un préstamo local

- **Actor:** Bibliotecario.
- **Precondición:** CU-PRE-00 determinó un préstamo local y asignó un ejemplar `Disponible` de la sede del bibliotecario (origen = destino).
- **Flujo normal:**
  1. El sistema valida todas las reglas.
  2. Registra el préstamo `Solicitado` y aparta el ejemplar.
  3. El bibliotecario entrega el ejemplar y confirma.
  4. El sistema pasa el préstamo a `Activo`, el ejemplar a `Prestado` y calcula el vencimiento.
- **Flujos alternativos:**
  - **A1 (paso 3): el socio no retira el ejemplar.** El bibliotecario cancela (CU-PRE-05) y el ejemplar vuelve a `Disponible`.
- **Postcondición:** préstamo `Activo` con vencimiento; ejemplar `Prestado`.

### CU-PRE-02. Registrar un préstamo interbibliotecario

- **Actores:** Bibliotecario de la sede destino, Socio.
- **Precondición:** CU-PRE-00 determinó un préstamo interbibliotecario y asignó un ejemplar `Disponible` de la sede origen.
- **Flujo normal:**
  1. El sistema valida las reglas, incluidas ambas sedes activas y la pertenencia del ejemplar a la sede origen.
  2. Registra el préstamo `Solicitado` y aparta el ejemplar.
  3. La sede origen prepara el envío (CU-REM-01) y el préstamo pasa a `En envío`.
  4. La sede destino recibe el remito (CU-REM-04).
  5. El bibliotecario destino entrega el ejemplar al socio; el sistema pasa el préstamo a `Activo`, el ejemplar a `Prestado` y calcula el vencimiento con el plazo interbibliotecario desde esa entrega.
- **Flujos alternativos:**
  - **A1 (paso 1): sede origen o destino en `Baja`.** Rechaza.
  - **A2 (paso 1): ejemplar de otra sede distinta de la origen.** Rechaza (invariante; no debería ocurrir porque el ejemplar lo asigna el sistema).
  - **A3 (paso 1): socio inhabilitado, máximo alcanzado o ejemplar no disponible.** Rechaza con los mismos criterios que CU-PRE-00. Si el ejemplar dejó de estar disponible, aplica CU-PRE-00 A5.
  - **A4 (pasos 3-4): el remito se anula antes del despacho.** El préstamo pasa a `Cancelado` y el ejemplar vuelve a `Disponible`.
  - **A5 (paso 4): el remito termina `Extraviado`, `Dañado` o `Destruido`.** El préstamo pasa a `Cancelado`, se registra la incidencia sobre el ejemplar (ver [Remitos](05-remitos.md)) y se informa al socio.
  - **A6 (paso 5): el socio no retira.** El bibliotecario cancela; el ejemplar vuelve a la sede origen por remito de retorno.
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

- **Actor:** Bibliotecario.
- **Flujo normal:** selecciona un préstamo `Solicitado`, confirma; pasa a `Cancelado` y el ejemplar vuelve a `Disponible`.
- **Flujos alternativos:**
  - **A1:** préstamo `En envío` con remito ya despachado; no se cancela, se espera la recepción y se devuelve.
  - **A2:** préstamo `Activo` o posterior; no se puede cancelar, solo devolver.

### CU-PRE-06. Consultar un préstamo

- **Actores:** Bibliotecario, Administrador, Socio (los propios).
- **Flujo normal:** busca por número, socio o ejemplar; el sistema muestra estado, fechas, historial y remito asociado.
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
| CA-PRE-07 | RF-PRE-08 | **Dado** un préstamo `Solicitado` sobre un ejemplar, **cuando** otro socio solicita el mismo libro, **entonces** el sistema no le asigna ese ejemplar. |
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
| CA-PRE-19 | RF-PRE-16 | **Dado** un libro con un ejemplar `Disponible` en la sede A, **cuando** un bibliotecario de A lo solicita, **entonces** se registra un préstamo local con un ejemplar de A. |
| CA-PRE-20 | RF-PRE-16 | **Dado** un libro sin disponibles en A, con 1 disponible en B y 3 en C, **cuando** un bibliotecario de A lo solicita, **entonces** se registra un préstamo interbibliotecario con origen C y destino A. |
| CA-PRE-21 | RF-PRE-16 | **Dado** un libro sin disponibles en A, con 2 disponibles en la sede de id 2 y 2 en la de id 3, **cuando** se solicita desde A, **entonces** el origen es la sede de id 2. |
| CA-PRE-22 | RF-PRE-16 | **Dado** un libro con disponibles solo en una sede en `Baja`, **cuando** se solicita, **entonces** esa sede no se considera como origen. |
| CA-PRE-23 | RF-PRE-19 | **Dado** un libro sin ejemplares disponibles en ninguna sede activa, **cuando** se solicita, **entonces** se rechaza sin crear el préstamo y se ofrece una reserva con retiro en la sede destino. |
| CA-PRE-24 | RF-PRE-18 | **Dado** un socio con sede A y un libro con disponibles en A, **cuando** el socio lo solicita, **entonces** se rechaza con el mensaje de acercarse al mostrador de A. |
| CA-PRE-25 | RF-PRE-17 | **Dado** un socio con sede A, **cuando** inicia la solicitud, **entonces** la sede destino propuesta es A. |
| CA-PRE-26 | RF-PRE-17 | **Dado** un socio con sede A que cambia la sede destino a B, sin disponibles en B y con disponibles en C, **cuando** confirma, **entonces** se registra un préstamo interbibliotecario de C a B. |
| CA-PRE-27 | RF-PRE-17 | **Dado** un bibliotecario de la sede A, **cuando** registra una solicitud, **entonces** la sede destino es A y no puede cambiarse. |
| CA-PRE-28 | RF-PRE-16 | **Dado** un único ejemplar disponible en A y dos solicitudes simultáneas del libro desde A, **cuando** se confirman, **entonces** solo una obtiene el préstamo local y la otra se vuelve a evaluar: queda interbibliotecaria o sin disponibilidad. |
| CA-PRE-29 | RF-PRE-16 | **Dado** un socio inhabilitado, **cuando** se solicita un préstamo para él, **entonces** se rechaza antes de evaluar la disponibilidad. |
