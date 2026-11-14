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
| Registrada por | El socio o el bibliotecario que la cargó en su nombre |
| Historial | Cada cambio de estado con fecha, autor y motivo |

La reserva es **sobre el libro** (cualquier ejemplar), no sobre un ejemplar concreto. Al liberarse un ejemplar, el sistema se lo asigna a la primera reserva de la cola.

## ¿Qué usuarios pueden reservar?

El **Socio** (por sí mismo, nunca a nombre de otro) y el **Bibliotecario** (en nombre del socio).

**Cancelar** la puede el socio (la propia) o el bibliotecario de la **sede de retiro**, que es quien la entrega. El administrador consulta las reservas pero no las opera.

## ¿Se puede reservar un ejemplar de otra sede?

**Sí.** El socio elige la sede de retiro. Si el ejemplar liberado está en otra sede, la reserva se cumple con un préstamo interbibliotecario hacia la sede de retiro: la reserva pasa directo a `Cumplida` y sigue el préstamo.

Pero si **ya hay** un ejemplar disponible en otra sede, no se reserva: se pide como préstamo entre sedes. La reserva es para esperar un libro que no está disponible en ninguna sede de la red.

## Política de la cola

- Orden **FIFO** por fecha y hora de reserva.
- Cuando se libera un ejemplar, o se da de alta uno nuevo, la primera reserva elegible pasa a `Disponible para retiro` y el ejemplar a `Reservado`.
- Es elegible el socio habilitado que podría retirarlo: si ya tiene el máximo de préstamos o un préstamo en curso del mismo libro, se lo saltea y sigue esperando en su lugar.
- La reserva tiene una **vigencia de retiro** (parámetro, valor 3 días). Si vence, pasa a `Vencida` y el ejemplar se asigna a la siguiente reserva.
- Una reserva `Disponible para retiro` se transforma en préstamo al entregarse (queda `Cumplida`).
- Lo que hace la cola (asignar, generar el préstamo entre sedes, vencer, cancelar) lo registra el **sistema**, aunque lo haya disparado un bibliotecario o un socio al liberar el ejemplar.

## Ciclo de vida

```
Pendiente ──▶ Disponible para retiro ──▶ Cumplida
   │   │               │
   │   │               └──▶ Vencida
   │   └──▶ Cumplida (ejemplar asignado desde otra sede: préstamo entre sedes)
   └──▶ Cancelada (también desde «Disponible para retiro»)
```

## Validaciones y reglas

- Solo se reserva un libro que **no tiene ejemplares disponibles en la red**: si hay en la sede de retiro corresponde un préstamo local, y si hay en otra sede, un préstamo entre sedes.
- No reservar a un socio `Inhabilitado`. *(enunciado)*
- No reservar con destino a una sede en `Baja`. *(enunciado)*
- Un socio no puede tener dos reservas activas del mismo libro.
- Máximo de reservas activas por socio (parámetro, valor 3).
- Si el socio queda inhabilitado, sus reservas pendientes se mantienen pero no pueden cumplirse hasta que se rehabilite.
- Si el libro se queda **sin ejemplares activos** en la red (se dio de baja o se destruyó el último), las reservas pendientes se cancelan con el motivo «El libro ya no tiene ejemplares en la red». Si alguno está extraviado sin resolver, siguen esperando: puede aparecer y recuperarse.

## Parámetros

Vigencia de retiro, máximo de reservas por socio.

## Casos de uso y flujos

1. **Reservar:** el socio consulta, ve que no hay disponibilidad y reserva.
2. **Cancelar** una reserva.
3. **Asignación automática** al liberarse un ejemplar o darse de alta uno nuevo.
4. **Retiro:** se convierte en préstamo.
5. **Vencimiento** de una reserva no retirada.
6. **Consulta** de la cola de un libro en orden de llegada (personal, en la ficha del libro), de las reservas de su sede (bibliotecario) y de las propias (socio), con el historial de cada una.
