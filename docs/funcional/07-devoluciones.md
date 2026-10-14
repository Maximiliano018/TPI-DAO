# 07. Devoluciones y multas

Origen: [negocio/07-devoluciones.md](../negocio/07-devoluciones.md). Proceso obligatorio 8.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-DEV-01 | El sistema debe permitir al bibliotecario registrar la devolución de un préstamo `Activo` o `Vencido`, con fecha y hora, estado físico recibido (`Bueno`, `Regular`, `Dañado`, `Extraviado`) y observaciones. | Obligatorio |
| RF-DEV-02 | La devolución debe registrarse en la sede destino del préstamo. | Obligatorio |
| RF-DEV-03 | La fecha de devolución no puede ser anterior al inicio del préstamo ni futura. | Obligatorio |
| RF-DEV-04 | Una devolución es fuera de término cuando la fecha supera el vencimiento; el día de vencimiento es el último día válido. | Obligatorio |
| RF-DEV-05 | Si es fuera de término, el sistema debe generar una multa de días de atraso × monto por día ($200, configurable), mediante una política de cálculo intercambiable, en estado `Pendiente`. | Obligatorio |
| RF-DEV-06 | El sistema debe permitir marcar una multa como `Saldada` (sin gestionar el cobro). | Obligatorio |
| RF-DEV-07 | Al devolver, el préstamo debe pasar a `Devuelto` y el sistema debe reevaluar al socio (rehabilitar si ya no tiene causas de inhabilitación). | Obligatorio |
| RF-DEV-08 | En una devolución local, el ejemplar debe quedar `Disponible` en la misma sede si el estado físico lo permite. | Obligatorio |
| RF-DEV-09 | En una devolución interbibliotecaria, el sistema debe generar el remito de retorno hacia la sede propietaria y dejar el ejemplar `En tránsito` al despacharse. | Obligatorio |
| RF-DEV-10 | Según el estado recibido: `Bueno` o `Regular` actualizan el estado físico; `Dañado` deja el ejemplar en revisión, no disponible; `Extraviado` lo pasa a `Baja` con incidencia. | Obligatorio |
| RF-DEV-11 | Al liberarse el ejemplar, el sistema debe revisar la cola de reservas del libro (ver [Reservas](06-reservas.md)). | Obligatorio |
| RF-DEV-12 | El sistema debe registrar una incidencia asociada al socio ante daño o extravío, sin penalización económica. | Opcional |
| RF-DEV-13 | El sistema debe permitir consultar devoluciones y multas por préstamo y por socio. | Obligatorio |

## Casos de uso

### CU-DEV-01. Registrar una devolución en término

- **Actor:** Bibliotecario de la sede destino.
- **Flujo normal:**
  1. Identifica el préstamo `Activo` (por socio, ejemplar o número).
  2. Registra fecha, estado físico `Bueno` o `Regular` y observaciones.
  3. El sistema verifica que no esté vencido.
  4. Pasa el préstamo a `Devuelto`.
  5. En un préstamo local, el ejemplar queda `Disponible`; en uno interbibliotecario se genera el retorno (CU-DEV-04).
  6. El sistema revisa las reservas del libro y reevalúa al socio.
- **Flujos alternativos:**
  - **A1 (paso 1): préstamo ya `Devuelto` o `Cancelado`.** Rechaza.
  - **A2 (paso 1): sede distinta del destino.** Rechaza e indica la sede correcta.
  - **A3 (paso 2): fecha futura o anterior al inicio.** Rechaza.
  - **A4 (paso 5): el libro tiene reservas.** El ejemplar se asigna a la primera (CU-RES-02) en lugar de quedar `Disponible`.

### CU-DEV-02. Registrar una devolución fuera de término

- **Actor:** Bibliotecario.
- **Flujo normal:**
  1. Igual a CU-DEV-01 hasta el paso 3, pero el préstamo está `Vencido` o la fecha supera el vencimiento.
  2. El sistema calcula los días de atraso y la multa.
  3. Crea la multa `Pendiente` y pasa el préstamo a `Devuelto`.
  4. El socio sigue inhabilitado mientras la multa esté pendiente.
- **Flujos alternativos:**
  - **A1:** devolución el día del vencimiento; sin multa.
  - **A2:** la multa tiene un tope configurado; se aplica el tope.
  - **A3:** la política de cálculo cambió; se usa la vigente al devolver.

### CU-DEV-03. Registrar una devolución con daño o extravío

- **Actor:** Bibliotecario.
- **Flujo normal:**
  1. Registra la devolución con estado `Dañado` y observaciones.
  2. El sistema deja el ejemplar en revisión, no disponible, y registra la incidencia.
  3. Si hay atraso, se genera además la multa (CU-DEV-02).
- **Flujos alternativos:**
  - **A1:** estado `Extraviado` (el socio no puede entregarlo); el préstamo se cierra como `Devuelto` con incidencia, el ejemplar pasa a `Baja`.
  - **A2:** observaciones vacías; rechaza (el daño o extravío exige descripción).
  - **A3:** el ejemplar en revisión se repara; el bibliotecario lo pasa a `Disponible` actualizando el estado físico; si no, se da de baja.

### CU-DEV-04. Devolver un préstamo interbibliotecario

- **Actor:** Bibliotecario de la sede destino.
- **Flujo normal:**
  1. Registra la devolución del socio (CU-DEV-01/02/03).
  2. El sistema genera un remito de retorno `Generado` hacia la sede propietaria (ver [Remitos](05-remitos.md)).
  3. Se empaqueta, despacha y recibe en la sede propietaria; el ejemplar queda `Disponible` allí.
- **Flujos alternativos:**
  - **A1 (paso 2): la sede propietaria está en `Baja`.** No ocurre: la baja se bloqueó por el préstamo activo.
  - **A2 (paso 3): el remito de retorno se extravía o llega destruido.** Se registra la incidencia; el préstamo ya estaba `Devuelto` y no se reabre ni se penaliza al socio.

### CU-DEV-05. Saldar una multa

- **Actor:** Bibliotecario, Administrador.
- **Flujo normal:** busca al socio, selecciona la multa `Pendiente` y la marca `Saldada`; el sistema reevalúa su habilitación.
- **Flujos alternativos:**
  - **A1:** la multa ya está saldada; informa.
  - **A2:** el socio tiene otras causas de inhabilitación; sigue inhabilitado.

### CU-DEV-06. Consultar devoluciones y multas

- **Actores:** Bibliotecario, Administrador, Socio (propias).
- **Flujo normal:** ve devoluciones, días de atraso, estado físico, multas y su estado.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-DEV-01 | RF-DEV-01 | **Dado** un préstamo `Activo`, **cuando** se registra la devolución, **entonces** pasa a `Devuelto` con fecha, hora, usuario y estado físico. |
| CA-DEV-02 | RF-DEV-01 | **Dado** un préstamo `Devuelto`, **cuando** se intenta devolver otra vez, **entonces** se rechaza. |
| CA-DEV-03 | RF-DEV-02 | **Dado** un préstamo con destino en la sede B, **cuando** se registra en la sede A, **entonces** se rechaza. |
| CA-DEV-04 | RF-DEV-03 | **Dado** una fecha de devolución futura, **cuando** se registra, **entonces** se rechaza. |
| CA-DEV-05 | RF-DEV-04 | **Dado** un préstamo que vence el día D, **cuando** se devuelve el día D, **entonces** no hay multa. |
| CA-DEV-06 | RF-DEV-05 | **Dado** un préstamo que vencía el día D, **cuando** se devuelve el día D+5, **entonces** se genera una multa de 5 × $200 = $1.000 en `Pendiente`. |
| CA-DEV-07 | RF-DEV-05 | **Dado** un cambio del monto por día en la configuración, **cuando** se calcula una multa nueva, **entonces** se usa el monto vigente. |
| CA-DEV-08 | RF-DEV-07 | **Dado** un socio inhabilitado solo por un préstamo vencido, **cuando** lo devuelve sin atraso y sin multa, **entonces** vuelve a `Habilitado`. |
| CA-DEV-09 | RF-DEV-07 | **Dado** un socio con multa pendiente, **cuando** devuelve el material, **entonces** sigue `Inhabilitado`. |
| CA-DEV-10 | RF-DEV-06 | **Dado** una multa `Pendiente` que era la única causa, **cuando** se marca `Saldada`, **entonces** el socio se rehabilita. |
| CA-DEV-11 | RF-DEV-08 | **Dado** una devolución local con estado `Bueno`, **cuando** se registra, **entonces** el ejemplar queda `Disponible` en la misma sede. |
| CA-DEV-12 | RF-DEV-09 | **Dado** una devolución interbibliotecaria, **cuando** se registra, **entonces** existe un remito de retorno distinto del de ida, con destino en la sede propietaria. |
| CA-DEV-13 | RF-DEV-10 | **Dado** una devolución con estado `Dañado`, **cuando** se registra, **entonces** el ejemplar no queda `Disponible` y se registra la incidencia. |
| CA-DEV-14 | RF-DEV-10 | **Dado** una devolución `Extraviado`, **cuando** se registra, **entonces** el ejemplar pasa a `Baja`. |
| CA-DEV-15 | RF-DEV-11 | **Dado** un libro con una reserva pendiente, **cuando** se devuelve un ejemplar, **entonces** se asigna a esa reserva. |
| CA-DEV-16 | RF-DEV-13 | **Dado** un socio, **cuando** consulta sus multas, **entonces** ve solo las propias con su estado. |
