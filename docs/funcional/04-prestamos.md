# 04. Préstamos

Origen: [negocio/04-prestamos.md](../negocio/04-prestamos.md). Proceso obligatorio 4 (y consulta de disponibilidad, proceso 6, en [Catálogo](03-catalogo.md)).

> **Punto abierto:** si el socio puede pedir el préstamo directamente. Estos casos de uso asumen que lo **registra el bibliotecario en nombre del socio**.

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

## Casos de uso

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
  - **A5 (paso 5): el socio no retira el ejemplar.** El bibliotecario cancela (CU-PRE-05) y el ejemplar vuelve a `Disponible`.
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
