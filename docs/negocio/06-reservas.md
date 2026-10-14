# 06. Gestión de reservas

Proceso obligatorio 7 del enunciado.

## ¿Cómo se define una reserva y qué datos se modelan?

Una **reserva** es un lugar en la cola de espera de un libro que no tiene ejemplares disponibles.

| Campo | Detalle |
|-------|---------|
| Número de reserva | Único |
| Socio | Quien reserva |
| Libro | Obra reservada |
| Sede de retiro | Sede donde el socio quiere retirar |
| Fecha y hora de reserva | Define el orden en la cola |
| Ejemplar asignado | Se completa cuando hay uno disponible |
| Fecha de aviso y de vencimiento | Para el retiro |
| Estado | `Pendiente`, `Disponible para retiro`, `Cumplida`, `Cancelada`, `Vencida` |

La reserva es **sobre el libro** (cualquier ejemplar), no sobre un ejemplar concreto. Al liberarse un ejemplar, el sistema se lo asigna a la primera reserva de la cola.

## ¿Qué usuarios pueden reservar?

El **Socio** (por sí mismo) y el **Bibliotecario** (en nombre del socio).

## ¿Se puede reservar un ejemplar de otra sede?

**Sí.** El socio elige la sede de retiro. Si el ejemplar liberado está en otra sede, la reserva se cumple con un préstamo interbibliotecario hacia la sede de retiro.

## Política de la cola

- Orden **FIFO** por fecha y hora de reserva.
- Cuando se libera un ejemplar, la primera reserva pasa a `Disponible para retiro` y el ejemplar a `Reservado`.
- La reserva tiene una **vigencia de retiro** (parámetro, valor 3 días). Si vence, pasa a `Vencida` y el ejemplar se asigna a la siguiente reserva.
- Una reserva `Disponible para retiro` se transforma en préstamo al entregarse (queda `Cumplida`).

## Ciclo de vida

```
Pendiente ──▶ Disponible para retiro ──▶ Cumplida
   │                   │
   │                   └──▶ Vencida
   └──▶ Cancelada (también desde «Disponible para retiro»)
```

## Validaciones y reglas

- Solo se reserva un libro que **no tiene ejemplares disponibles** en la sede de retiro; si hay disponibles, corresponde un préstamo.
- No reservar a un socio `Inhabilitado`. *(enunciado)*
- No reservar con destino a una sede en `Baja`. *(enunciado)*
- Un socio no puede tener dos reservas activas del mismo libro.
- Máximo de reservas activas por socio (parámetro, valor 3).
- Si el socio queda inhabilitado, sus reservas pendientes se mantienen pero no pueden cumplirse hasta que se rehabilite.

## Parámetros

Vigencia de retiro, máximo de reservas por socio.

## Casos de uso y flujos

1. **Reservar:** el socio consulta, ve que no hay disponibilidad y reserva.
2. **Cancelar** una reserva.
3. **Asignación automática** al liberarse un ejemplar.
4. **Retiro:** se convierte en préstamo.
5. **Vencimiento** de una reserva no retirada.
6. **Consulta** de la cola de un libro (personal) y de las reservas propias (socio).
