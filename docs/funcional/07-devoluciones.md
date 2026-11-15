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
| RF-DEV-12 | El sistema debe registrar una incidencia asociada al socio ante daño o extravío (la multa, si corresponde, la define RF-DEV-23). | Opcional |
| RF-DEV-13 | El sistema debe permitir consultar devoluciones y multas por préstamo y por socio; el personal busca las multas de un socio desde la página de multas o desde su ficha. | Obligatorio |
| RF-DEV-14 | Una devolución con fecha anterior al día en que se registra debe exigir un motivo (de 5 a 300 caracteres) y dejar en el historial del préstamo la fecha de devolución, la de registro y el motivo. | Obligatorio |
| RF-DEV-15 | El sistema debe permitir configurar un tope de multa por préstamo (0 = sin tope); la política de cálculo lo aplica. | Opcional |
| RF-DEV-16 | El socio debe ver sus devoluciones y multas sin la identidad del personal que las registró o saldó; el personal sí la ve. | Obligatorio |
| RF-DEV-17 | Al saldar una multa en el mostrador, el personal debe registrar el medio de pago (efectivo, débito, crédito o transferencia) y, opcionalmente, el comprobante. | Opcional |
| RF-DEV-18 | El socio debe poder pagar en línea sus multas pendientes en un checkout simulado de tres pasos (forma de pago: tarjeta de crédito, de débito o dinero en cuenta; datos; resultado); si ya tiene un pago en curso, lo retoma. De la tarjeta solo se envían los últimos 4 dígitos. No hay cobro real. | Opcional |
| RF-DEV-19 | Al aprobar el pago en línea, la multa queda saldada y el socio se reevalúa. | Opcional |
| RF-DEV-20 | Un pago en línea rechazado deja la multa pendiente y permite reintentar; cobrar en el mostrador cancela el pago en línea en curso, que ya no se puede aprobar. | Opcional |
| RF-DEV-21 | El socio solo inicia y paga pagos de sus multas; el personal no inicia pagos en línea. | Opcional |
| RF-DEV-22 | Todo pago aprobado (de mostrador o en línea) debe tener un comprobante descargable en PDF; el socio descarga los suyos y el personal, cualquiera. | Opcional |
| RF-DEV-23 | Al registrar una devolución `Dañado` o `Extraviado`, el sistema debe generar una multa por daño o por extravío con el monto fijo configurado (`multa_por_danio`, `multa_por_extravio`; 0 = no se cobra), además de la de atraso si la hay. Un préstamo tiene a lo sumo una multa de cada tipo; el tope por préstamo se aplica solo a la de atraso. | Opcional |
| RF-DEV-24 | La multa por daño o extravío se paga, inhabilita y rehabilita al socio igual que la de atraso; las fichas, la lista de multas, el reporte R4 y el comprobante muestran su concepto (atraso, daño o extravío). | Opcional |

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
  - **A3b (paso 2): fecha anterior a hoy (lo devolvió antes y se registra ahora).** Exige el motivo; el historial guarda las dos fechas. El diálogo avisa el atraso y la multa antes de confirmar.
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
  - **A2:** la multa tiene un tope configurado (`multa_tope_por_prestamo`); se aplica el tope.
  - **A3:** la política de cálculo cambió; se usa la vigente al devolver.

### CU-DEV-03. Registrar una devolución con daño o extravío

- **Actor:** Bibliotecario.
- **Flujo normal:**
  1. Registra la devolución con estado `Dañado` y observaciones.
  2. El sistema deja el ejemplar en revisión, no disponible, y registra la incidencia.
  3. Si el monto por daño está configurado, genera la multa por daño (RF-DEV-23) y el socio queda inhabilitado hasta pagarla.
  4. Si hay atraso, se genera además la multa por atraso (CU-DEV-02).
- **Flujos alternativos:**
  - **A1:** estado `Extraviado` (el socio no puede entregarlo); el préstamo se cierra como `Devuelto` con incidencia, el ejemplar pasa a `Baja` y, si el monto está configurado, se genera la multa por extravío.
  - **A4:** el monto por daño o extravío es 0 (valor inicial); queda solo la incidencia, sin multa.
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
- **Flujo normal:** busca al socio (en la página de multas o desde su ficha, «Ver las multas del socio»), selecciona la multa `Pendiente`, elige el medio de pago (y el comprobante, si hay) y registra el cobro; la multa queda `Saldada` y el sistema reevalúa su habilitación.
- **Flujos alternativos:**
  - **A1:** la multa ya está saldada; informa.
  - **A2:** el socio tiene otras causas de inhabilitación; sigue inhabilitado.
  - **A3:** el socio había iniciado un pago en línea; se cancela.

### CU-DEV-07. Pagar una multa en línea (simulado)

- **Actor:** Socio.
- **Flujo normal:**
  1. En «Mis multas», elige «Pagar en línea» en una multa `Pendiente`.
  2. El sistema crea el pago pendiente (o retoma el que estaba en curso) y abre el checkout simulado.
  3. Elige la forma de pago (tarjeta de crédito, de débito o dinero en cuenta).
  4. Con tarjeta, completa número, titular, vencimiento y código; el sistema los valida en el navegador y envía solo los últimos 4 dígitos.
  5. Confirma: la multa queda saldada, el sistema reevalúa al socio y muestra el número de comprobante.
  6. Descarga el comprobante en PDF (también desde «Mis multas»).
- **Flujos alternativos:**
  - **A1 (paso 4): datos de tarjeta inválidos.** Se indican sin enviar nada.
  - **A2 (paso 5): la tarjeta se rechaza (la de prueba terminada en 0002).** La multa sigue pendiente; «Intentar de nuevo» inicia otro pago.
  - **A3 (paso 5): mientras tanto se le cobró en el mostrador.** El pago en línea está cancelado y no se puede pagar.

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
| CA-DEV-17 | RF-DEV-14 | **Dado** un préstamo vencido, **cuando** se registra la devolución con una fecha anterior a hoy sin motivo, **entonces** se rechaza; con motivo se acepta y el historial muestra las dos fechas y el motivo. |
| CA-DEV-18 | RF-DEV-15 | **Dado** un tope de $500, **cuando** se devuelve con 5 días de atraso a $200 por día, **entonces** la multa es de $500. |
| CA-DEV-19 | RF-DEV-16 | **Dado** una devolución con multa saldada, **cuando** el socio la consulta, **entonces** no ve quién la registró ni quién la saldó; el personal sí. |
| CA-DEV-20 | RF-DEV-13 | **Dado** un socio elegido en la página de multas, **cuando** el personal la consulta, **entonces** ve solo las multas de ese socio. |
| CA-DEV-21 | RF-DEV-17 | **Dado** una multa pendiente, **cuando** el bibliotecario la cobra con débito y un comprobante, **entonces** queda saldada con ese medio; el socio ve el medio pero no el comprobante ni quién cobró. |
| CA-DEV-22 | RF-DEV-18 | **Dado** una multa pendiente propia, **cuando** el socio inicia el pago en línea, **entonces** queda un pago pendiente por el monto de la multa; otro pedido retoma el mismo pago. |
| CA-DEV-23 | RF-DEV-19 | **Dado** un pago en línea pendiente, **cuando** el socio paga con una tarjeta válida, **entonces** la multa queda saldada y el socio se reevalúa. |
| CA-DEV-24 | RF-DEV-20 | **Dado** un pago en línea pendiente, **cuando** el socio paga con la tarjeta de prueba rechazada, **entonces** la multa sigue pendiente y puede iniciar otro pago. |
| CA-DEV-25 | RF-DEV-20 | **Dado** un pago en línea en curso, **cuando** el bibliotecario cobra la multa en el mostrador, **entonces** el pago en línea queda cancelado y no se puede aprobar. |
| CA-DEV-26 | RF-DEV-21 | **Dado** un bibliotecario, o la multa o el pago de otro socio, **cuando** se intenta pagar en línea, **entonces** se rechaza. |
| CA-DEV-27 | RF-DEV-22 | **Dado** un pago aprobado, **cuando** el socio o el personal descargan el comprobante, **entonces** reciben un PDF con su número, socio, concepto, medio y total; un pago no aprobado no tiene comprobante. |
| CA-DEV-28 | RF-DEV-18 | **Dado** el checkout simulado, **cuando** el socio paga con tarjeta, **entonces** al servidor llegan solo los últimos 4 dígitos (un número completo se rechaza); con dinero en cuenta no se pide tarjeta. |
| CA-DEV-29 | RF-DEV-23 | **Dado** una multa por daño de $3.000, **cuando** se registra una devolución `Dañado` en término, **entonces** se genera una multa por daño de $3.000, sin días de atraso, y el socio queda inhabilitado. |
| CA-DEV-30 | RF-DEV-23 | **Dado** una multa por extravío de $15.000, **cuando** se registra una devolución `Extraviado`, **entonces** se genera una multa por extravío de $15.000. |
| CA-DEV-31 | RF-DEV-23 | **Dado** el monto por daño en 0, o una devolución `Regular` o `Bueno`, **cuando** se registra, **entonces** no se genera multa por daño. |
| CA-DEV-32 | RF-DEV-23 | **Dado** un tope de $500 y una devolución dañada con 5 días de atraso, **cuando** se registra, **entonces** hay dos multas (atraso de $500 y daño entero), el socio se rehabilita solo al pagar las dos, y un préstamo no puede tener dos multas del mismo tipo. |
| CA-DEV-33 | RF-DEV-24 | **Dado** una multa por daño o extravío, **cuando** el socio la paga en línea o el personal consulta R4, **entonces** el pago se aprueba como el de atraso y el comprobante y el reporte muestran su concepto. |
