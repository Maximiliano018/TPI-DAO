# 07. Registro de devoluciones

Proceso obligatorio 8 del enunciado.

## ¿Cómo se define una devolución y qué datos se modelan?

Una **devolución** es el registro de que el socio entrega un ejemplar prestado y de en qué estado lo hace.

| Campo | Detalle |
|-------|---------|
| Préstamo | Préstamo que se cierra |
| Fecha y hora | |
| Sede de devolución | Debe coincidir con la sede destino del préstamo |
| Estado físico recibido | `Bueno`, `Regular`, `Dañado`, `Extraviado` |
| Observaciones | |
| Días de atraso | Calculado |
| Multas generadas | Por atraso, y por daño o extravío; cada una si corresponde |
| Registrado por | Bibliotecario |
| Registrada en | Cuándo se cargó en el sistema (difiere de la fecha si es retroactiva) |
| Motivo de la fecha | Obligatorio si la fecha es anterior al día en que se registra |

## ¿Aplica a préstamos entre sedes y locales?

A ambos.

- **Local:** el ejemplar vuelve a `Disponible` en la misma sede.
- **Interbibliotecario:** el socio devuelve en la sede destino; el ejemplar queda `Apartado` y se genera el **remito de retorno** hacia la sede propietaria (pasa a `En tránsito` cuando se despacha). El préstamo queda `Devuelto` al registrar la devolución del socio. El retorno del ejemplar sigue su propio ciclo de remito.

## ¿Quién registra una devolución?

El **Bibliotecario** de la sede donde se devuelve, o el **Administrador** (opera en cualquier sede).

## ¿Cuándo es fuera de término?

Cuando la fecha de devolución es posterior a la **fecha de vencimiento** del préstamo. El plazo se cuenta en días corridos. El día de vencimiento es el último día válido.

## ¿Cómo se aplica la multa?

Una devolución puede generar hasta **dos multas**, una de cada tipo: por **atraso** y por **daño o extravío** (ver [¿Qué pasa si se devuelve en mal estado?](#qué-pasa-si-se-devuelve-en-mal-estado)). Un préstamo nunca tiene dos multas del mismo tipo.

**Por atraso:** `multa = días de atraso × monto por día`, con un monto fijo configurable (valor inicial: $200 por día de atraso, ver [parámetros globales](00-contexto-y-actores.md#parámetros-globales-configurables)). Se implementa como política intercambiable (patrón Strategy), de modo que se pueda cambiar la regla sin tocar el resto del código.

- La multa nace al registrar la devolución tardía.
- Estados: `Pendiente`, `Saldada`.
- Una multa `Pendiente` inhabilita al socio hasta que se paga (ver [¿Cómo se paga una multa?](#cómo-se-paga-una-multa)).
- **Tope por préstamo** configurable (parámetro, valor inicial 0 = sin tope): si se configura, la multa por atraso no lo supera. La de daño o extravío no tiene tope (ya es un monto fijo).
- El socio ve sus multas y sus devoluciones sin la identidad del personal que las registró o saldó (ve «Personal de la biblioteca», como en el resto del sistema); el personal sí la ve.
- El personal busca las multas de un socio desde la página de multas o desde su ficha.

## ¿Qué pasa si se devuelve en mal estado?

El bibliotecario registra el estado físico y las observaciones.

| Estado recibido | Efecto |
|-----------------|--------|
| `Bueno` / `Regular` | El ejemplar vuelve a estar disponible (actualiza su estado físico); en un préstamo entre sedes, vuelve a su sede con el remito de retorno |
| `Dañado` | Préstamo local: el ejemplar pasa a `En revisión`, no disponible hasta que su sede lo repare o lo dé de baja. Entre sedes: queda `Apartado`, vuelve con el remito de retorno y pasa a `En revisión` al llegar a su sede propietaria. En los dos casos, incidencia de daño a nombre del socio |
| `Extraviado` | Ejemplar en `Baja` con incidencia de extravío a nombre del socio. Si aparece después, la sede propietaria lo recupera y la incidencia queda resuelta |

**Multa por daño o extravío** (extensión opcional): además de la incidencia, una devolución `Dañado` genera una **multa por daño** y una `Extraviado`, una **multa por extravío** (la reposición del ejemplar). Reglas:

- **Monto fijo configurable** por cada caso (parámetros `multa_por_danio` y `multa_por_extravio`). El valor inicial es **0 = no se cobra**: el administrador lo activa cargando un monto. Es otra política intercambiable (Strategy): podría pasar a depender del valor de reposición del libro sin tocar la devolución.
- **Nace al registrar la devolución**, cuando el socio está en el mostrador y el daño ya quedó descrito en las observaciones (obligatorias). No depende de que después el ejemplar se repare o se dé de baja.
- `Regular` es desgaste normal y **no genera multa**: lo que distingue un caso del otro es el criterio del bibliotecario al elegir `Regular` o `Dañado`.
- Se suma a la de atraso si la hubo (un préstamo devuelto tarde y dañado tiene dos multas). Se paga igual que cualquier multa (en el mostrador o en línea) y también **inhabilita al socio** hasta que la paga: con dos multas, se rehabilita al pagar las dos.
- En un préstamo entre sedes la genera la sede destino al recibir la devolución, como la de atraso; la sede propietaria después revisa el ejemplar.

Las incidencias de un envío (remito), en cambio, no son del socio: quedan a cargo de la sede origen y nunca generan multa (ver [Remitos](05-remitos.md#quién-es-responsable-de-una-incidencia)).

## ¿Cómo se paga una multa?

De dos formas; en ambas la multa queda `Saldada` con **un** pago aprobado y el socio se reevalúa (si era su única causa, se rehabilita).

| Forma | Quién | Cómo |
|-------|-------|------|
| **En el mostrador** | Bibliotecario (o administrador) de cualquier sede | Cobra y registra el **medio**: efectivo, débito, crédito o transferencia, con un comprobante opcional (cupón u operación) |
| **En línea (simulado)** | El propio socio, solo sus multas | Desde «Mis multas» va a un checkout simulado: elige tarjeta de crédito, de débito o dinero en cuenta, completa los datos y confirma. Es una demostración: **no hay cobro real** ni pasarela externa, y de la tarjeta solo se guardan los últimos 4 dígitos |

- Mientras el pago en línea no se aprueba, la multa sigue `Pendiente`.
- Todo pago aprobado (de mostrador o en línea) tiene su **comprobante en PDF**, que el socio descarga desde «Mis multas» y el personal desde la página de multas.
- Un pago rechazado deja la multa pendiente; el socio puede intentarlo de nuevo. Para la demo, la tarjeta de prueba terminada en `0002` simula un rechazo; cualquier otra se aprueba.
- Si el socio inició un pago en línea y se le cobra en el mostrador, el pago en línea se cancela y ya no se puede aprobar (ver [técnica/12](../tecnica/12-pago-de-multas.md)).
- El socio ve el medio con que se pagó su multa y descarga el comprobante en PDF, pero no ve quién la cobró ni el número de cupón u operación del cobro en el mostrador.

## Validaciones y reglas

- Solo se devuelve un préstamo en estado `Activo` o `Vencido`.
- La devolución se registra en la sede destino del préstamo.
- La fecha de devolución no puede ser anterior a la de inicio ni futura.
- **Fecha retroactiva:** si el socio lo devolvió antes y se registra después, se puede indicar la fecha real, pero hace falta un **motivo** (de 5 a 300 caracteres): la fecha cambia el atraso y puede evitar la multa. El historial del préstamo deja las dos fechas («Devuelto el 10/11/2026 (registrado el 14/11/2026): motivo»). Una hora anterior del mismo día no necesita motivo.
- Al devolver, el sistema vuelve a evaluar al socio: si no le quedan vencidos ni multas pendientes, se rehabilita.
- Al liberarse el ejemplar, se revisa la cola de reservas del libro (ver [Reservas](06-reservas.md)).

## Casos de uso y flujos

1. **Devolución en término.**
2. **Devolución tardía** con generación de multa.
3. **Devolución con daño o extravío**, con su multa si el monto está configurado.
4. **Devolución de préstamo interbibliotecario** con remito de retorno.
5. **Saldar una multa** en el mostrador, con su medio de pago.
5b. **Pagar una multa en línea** (el socio, simulado).
6. **Asignación del ejemplar liberado** a la primera reserva.
