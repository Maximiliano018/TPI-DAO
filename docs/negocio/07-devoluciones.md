# 07. Registro de devoluciones

Proceso obligatorio 8 del enunciado. Las definiciones fueron confirmadas por Maxi; los puntos marcados como *A consultar* siguen abiertos con la cátedra.

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
| Multa generada | Si corresponde |
| Registrado por | Bibliotecario |

## ¿Aplica a préstamos entre sedes y locales?

A ambos.

- **Local:** el ejemplar vuelve a `Disponible` en la misma sede.
- **Interbibliotecario:** el socio devuelve en la sede destino; el ejemplar queda `En tránsito` de vuelta y se genera el **remito de retorno** hacia la sede propietaria. El préstamo queda `Devuelto` al registrar la devolución del socio. El retorno del ejemplar sigue su propio ciclo de remito.

## ¿Quién registra una devolución?

El **Bibliotecario** de la sede donde se devuelve. El administrador la consulta.

## ¿Cuándo es fuera de término?

Cuando la fecha de devolución es posterior a la **fecha de vencimiento** del préstamo. El plazo se cuenta en días corridos. El día de vencimiento es el último día válido.

## ¿Cómo se aplica la multa?

`multa = días de atraso × monto por día`, con un monto fijo configurable. Se implementa como política intercambiable (patrón Strategy), de modo que se pueda cambiar la regla sin tocar el resto del código.

- La multa nace al registrar la devolución tardía.
- Estados: `Pendiente`, `Saldada`.
- Una multa `Pendiente` inhabilita al socio. El sistema solo marca la multa como saldada; el cobro real está fuera del alcance.
- Opcional: tope máximo de multa por préstamo.

## ¿Qué pasa si se devuelve en mal estado?

El bibliotecario registra el estado físico y las observaciones.

| Estado recibido | Efecto |
|-----------------|--------|
| `Bueno` / `Regular` | El ejemplar vuelve a estar disponible (actualiza su estado físico) |
| `Dañado` | El ejemplar pasa a revisión; no está disponible hasta decidir si se repara o se da de baja |
| `Extraviado` | Ejemplar en `Baja` con incidencia registrada |

*La penalización económica al socio por daño o extravío queda fuera del alcance obligatorio.* Se deja registrada la incidencia asociada al socio por si se decide aplicarla más adelante.

## Validaciones y reglas

- Solo se devuelve un préstamo en estado `Activo` o `Vencido`.
- La devolución se registra en la sede destino del préstamo.
- La fecha de devolución no puede ser anterior a la de inicio ni futura.
- Al devolver, el sistema vuelve a evaluar al socio: si no le quedan vencidos ni multas pendientes, se rehabilita.
- Al liberarse el ejemplar, se revisa la cola de reservas del libro (ver [Reservas](06-reservas.md)).

## Casos de uso y flujos

1. **Devolución en término.**
2. **Devolución tardía** con generación de multa.
3. **Devolución con daño o extravío.**
4. **Devolución de préstamo interbibliotecario** con remito de retorno.
5. **Saldar una multa.**
6. **Asignación del ejemplar liberado** a la primera reserva.
