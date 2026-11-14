# 05. Remitos y envíos entre sedes

Proceso obligatorio 5 del enunciado. La consigna indica que el ciclo de vida del remito **se evalúa críticamente**, por lo que este es el documento más importante para revisar.

## ¿Cómo se define un remito y qué datos se modelan?

Un **remito** es el comprobante de un envío de ejemplares entre dos sedes. Acompaña el material físico y permite seguirlo durante todo el trayecto.

**Remito (cabecera):**

| Campo | Detalle |
|-------|---------|
| Número de remito | Único, correlativo |
| Sede origen | Quien envía |
| Sede destino | Quien recibe |
| Motivo | `Envío por préstamo` / `Retorno por devolución` / `Traslado` |
| Estado actual | Ver ciclo de vida |
| Fechas | Generación, despacho y recepción |
| Responsables | Quien empaqueta, despacha y recibe (salen del historial de estados: cada movimiento guarda su responsable) |
| Observaciones | Texto libre |

**Detalle del remito:** una línea por ejemplar enviado, con su préstamo asociado, el estado físico al salir y el estado físico al llegar.

**Historial de estados (`MovimientoRemito`):** una entrada por cada cambio de estado, con estado anterior, estado nuevo, fecha y hora, responsable y observación. Es la base de la trazabilidad y de los reportes de tránsito.

## ¿Un remito por préstamo o con detalle de ejemplares?

**Un remito con detalle de ejemplares.** Un envío puede agrupar varios ejemplares que van de la misma sede origen a la misma sede destino. Es lo habitual en logística real, evita un papel por libro y no complica el caso simple (un remito con una sola línea). Cada línea del detalle apunta a su préstamo.

Un envío de un solo ejemplar es el caso simple: un remito con una única línea de detalle.

## ¿Un remito debe ir asociado a un préstamo?

Cada línea del detalle se asocia a un préstamo, excepto los remitos de **traslado** (cambio de sede propietaria de un ejemplar o preparación de una baja de sede), que no tienen préstamo.

## ¿Un remito para la ida y la vuelta?

**Dos remitos distintos.** La ida (origen → destino) y la vuelta (destino → origen) son envíos independientes, con su propio ciclo de vida, responsables y tiempos. El préstamo guarda ambos. Así se miden por separado el tránsito de ida y el de retorno, y se puede dar una incidencia en uno sin alterar el otro.

## Ciclo de vida del remito

```
Generado ──▶ Empaquetado ──▶ Despachado ──▶ En tránsito ──▶ Recibido
   │              │              │               │
   │              │              │               ├──▶ Extraviado
   └──▶ Anulado   └──▶ Anulado   │               └──▶ Recibido con incidencia (Dañado / Destruido / Incompleto)
                                 └──▶ Extraviado
```

| Estado | Significado | Efecto en el ejemplar |
|--------|-------------|------------------------|
| `Generado` | Se creó el remito con su detalle | Sigue en la sede origen, apartado |
| `Empaquetado` | Preparado físicamente | Sigue en la sede origen |
| `Despachado` | Salió de la sede origen | `En tránsito` |
| `En tránsito` | Viajando hacia la sede destino | `En tránsito` |
| `Recibido` | La sede destino lo recibió y verificó | `Disponible` o `Prestado` en destino, según el motivo |
| `Extraviado` | No llegó en un plazo máximo; se da por perdido | Se evalúa baja del ejemplar |
| `Dañado` | Llegó con daño reparable | Ejemplar a revisión en su sede propietaria: si era un envío, vuelve con un remito de retorno; si era un traslado, la revisa la nueva propietaria |
| `Destruido` | Llegó inutilizable | Baja del ejemplar |
| `Incompleto` | Llegó, pero faltaba al menos un ejemplar | Los que llegaron se reciben normalmente; cada faltante se da de baja por extravío |
| `Anulado` | Cancelado antes de salir | El ejemplar vuelve a `Disponible` |

**La revisión y la reparación las hace la sede dueña del ejemplar.** Si un envío por préstamo llega dañado, la sede destino no lo repara: el préstamo se cancela y el ejemplar vuelve a su sede con un remito de retorno, igual que cuando el socio lo devuelve dañado en otra sede.

## ¿Quién es responsable de una incidencia?

- **En un envío, la sede origen**: empaqueta, despacha y custodia el material hasta que la sede destino lo recibe. En un retorno, la sede origen es la que recibió la devolución y lo manda de vuelta. La persona que lo despachó queda en el historial del remito, y quien registró la incidencia, en la incidencia.
- **El socio nunca es responsable de lo que pasa en un envío**: no tenía el ejemplar. Las incidencias de devolución (el socio devuelve dañado o lo perdió) sí quedan a su nombre.

## ¿Y si falta un ejemplar al recibir?

Al verificar, la sede destino marca la línea como **«No llegó»**, con una observación. Ese ejemplar se da de baja por extravío con incidencia a cargo de la sede origen y, si era un envío, su préstamo se cancela. El resto del remito se recibe normalmente y el remito queda `Incompleto`. Si no llegó ninguno, el remito no se recibe: sigue en tránsito hasta que pueda marcarse `Extraviado`.

## ¿Y si un extraviado aparece después?

La sede propietaria lo **recupera**: vuelve a `Disponible` en su sede (o a `En revisión` si llegó dañado), queda en su historial y la incidencia de extravío queda **resuelta** (no se borra). Los préstamos que se cancelaron no se reabren.

`Dañado` y `Destruido` se registran en la **revisión de recepción** (proceso opcional del enunciado); se incluyen porque el ciclo se evalúa críticamente y es más sencillo diseñarlos desde el inicio.

*Nota de diseño:* `Despachado` y `En tránsito` se mantienen separados: permiten medir el tiempo entre «sale de la sede» y «está viajando». El paso a `En tránsito` lo marca la sede origen; si no lo hizo, el sistema lo completa al recibir y lo deja registrado.

### Reglas del ciclo

- Las transiciones válidas son solo las del diagrama: **sin saltos ni retrocesos**.
- Cada transición registra un `MovimientoRemito` (fecha y hora, responsable).
- Estados **finales**: `Recibido`, `Extraviado`, `Dañado`, `Destruido`, `Incompleto` y `Anulado`.
- Un remito `Despachado` ya no se puede anular.
- La anulación solo es posible antes del despacho.

## ¿Quién gestiona los remitos? ¿Quién puede crear, operar y consultar?

| Acción | Quién |
|--------|-------|
| Generar y empaquetar | Bibliotecario de la **sede origen** |
| Despachar | Bibliotecario de la sede origen |
| Marcar en tránsito | Bibliotecario de la sede origen (si no lo hace, el sistema lo completa al recibir) |
| Recibir y verificar | Bibliotecario de la **sede destino** |
| Registrar incidencia | Bibliotecario de la sede destino |
| Anular | Bibliotecario de la sede origen, antes del despacho |
| Consultar | Bibliotecarios de las dos sedes involucradas; el Administrador ve todos; el socio ve el estado del remito de su propio préstamo |

## Casos de uso y flujos

1. **Generar remito** a partir de uno o más préstamos aprobados con mismo origen y destino.
2. **Empaquetar y despachar.**
3. **Seguimiento** del estado y del historial.
4. **Recepción:** el destino verifica contenido y estado físico, y confirma por línea.
5. **Incidencia:** extravío (vencido el plazo máximo de tránsito, o un ejemplar que no llegó), daño o destrucción.
8. **Recuperación** de un ejemplar extraviado que aparece después (ver [Catálogo](03-catalogo.md)).
6. **Anulación** antes del despacho.
7. **Remito de retorno** al registrar la devolución en una sede distinta de la propietaria.

## Validaciones y reglas

- Mantener la trazabilidad en todo el trayecto. *(enunciado)*
- No iniciar envíos hacia o desde una sede en `Baja`. *(enunciado)*
- Solo se pueden incluir ejemplares que pertenezcan a la sede origen del remito, o que estén en ella para el retorno.
- Todos los ejemplares de un remito comparten origen y destino.
- Un ejemplar no puede estar en dos remitos abiertos a la vez.
- No se puede recibir un remito en una sede distinta del destino.
- Plazo máximo de tránsito (parámetro, valor 7 días): vencido, se puede marcar `Extraviado`.
- Plazo de despacho (parámetro, valor 3 días desde la generación): vencido sin despachar, el remito figura **atrasado** para que la sede origen lo despache o lo anule.
- Número de remito único.

## Parámetros a tener en cuenta

Plazo máximo de tránsito antes de considerar extravío, plazo de despacho antes de marcar el remito como atrasado, y plazo de préstamo interbibliotecario (cuenta desde la entrega al socio).
