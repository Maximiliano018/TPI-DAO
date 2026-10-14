# 05. Remitos y envíos entre sedes

Proceso obligatorio 5 del enunciado. La consigna indica que el ciclo de vida del remito **se evalúa críticamente**, por lo que este es el documento más importante para revisar. Las definiciones fueron confirmadas por Maxi; los puntos marcados como *A consultar* siguen abiertos con la cátedra.

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
| Responsables | Quien empaqueta, despacha y recibe |
| Observaciones | Texto libre |

**Detalle del remito:** una línea por ejemplar enviado, con su préstamo asociado, el estado físico al salir y el estado físico al llegar.

**Historial de estados (`MovimientoRemito`):** una entrada por cada cambio de estado, con estado anterior, estado nuevo, fecha y hora, responsable y observación. Es la base de la trazabilidad y de los reportes de tránsito.

## ¿Un remito por préstamo o con detalle de ejemplares?

**Un remito con detalle de ejemplares.** Un envío puede agrupar varios ejemplares que van de la misma sede origen a la misma sede destino. Es lo habitual en logística real, evita un papel por libro y no complica el caso simple (un remito con una sola línea). Cada línea del detalle apunta a su préstamo.

> **A consultar con la cátedra.** Si se prefiere simplicidad, la alternativa es un remito por préstamo (relación 1 a 1), con la misma estructura pero siempre con una sola línea.

## ¿Un remito debe ir asociado a un préstamo?

Cada línea del detalle se asocia a un préstamo, excepto los remitos de **traslado** (cambio de sede propietaria de un ejemplar o preparación de una baja de sede), que no tienen préstamo.

## ¿Un remito para la ida y la vuelta?

**Dos remitos distintos.** La ida (origen → destino) y la vuelta (destino → origen) son envíos independientes, con su propio ciclo de vida, responsables y tiempos. El préstamo guarda ambos. Así se miden por separado el tránsito de ida y el de retorno, y se puede dar una incidencia en uno sin alterar el otro.

## Ciclo de vida del remito

```
Generado ──▶ Empaquetado ──▶ Despachado ──▶ En tránsito ──▶ Recibido
   │              │              │               │
   │              │              │               ├──▶ Extraviado
   └──▶ Anulado   └──▶ Anulado   │               └──▶ Recibido con incidencia (Dañado / Destruido)
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
| `Dañado` | Llegó con daño reparable | Ejemplar a revisión |
| `Destruido` | Llegó inutilizable | Baja del ejemplar |
| `Anulado` | Cancelado antes de salir | El ejemplar vuelve a `Disponible` |

`Dañado` y `Destruido` se registran en la **revisión de recepción** (proceso opcional del enunciado); se incluyen porque el ciclo se evalúa críticamente y es más sencillo diseñarlos desde el inicio.

*Nota de diseño:* `Despachado` y `En tránsito` pueden fusionarse si el equipo concluye que no aportan información distinta. Se mantienen separados porque permiten medir el tiempo entre «sale de la sede» y «está viajando», pero es una decisión a confirmar.

### Reglas del ciclo

- Las transiciones válidas son solo las del diagrama: **sin saltos ni retrocesos**.
- Cada transición registra un `MovimientoRemito` (fecha y hora, responsable).
- Estados **finales**: `Recibido`, `Extraviado`, `Dañado`, `Destruido` y `Anulado`.
- Un remito `Despachado` ya no se puede anular.
- La anulación solo es posible antes del despacho.

## ¿Quién gestiona los remitos? ¿Quién puede crear, operar y consultar?

| Acción | Quién |
|--------|-------|
| Generar y empaquetar | Bibliotecario de la **sede origen** |
| Despachar | Bibliotecario de la sede origen |
| Marcar en tránsito | Bibliotecario de la sede origen (o automático al despachar) |
| Recibir y verificar | Bibliotecario de la **sede destino** |
| Registrar incidencia | Bibliotecario de la sede destino |
| Anular | Bibliotecario de la sede origen, antes del despacho |
| Consultar | Bibliotecarios de las dos sedes involucradas; el Administrador ve todos; el socio ve el estado del remito de su propio préstamo |

## Casos de uso y flujos

1. **Generar remito** a partir de uno o más préstamos aprobados con mismo origen y destino.
2. **Empaquetar y despachar.**
3. **Seguimiento** del estado y del historial.
4. **Recepción:** el destino verifica contenido y estado físico, y confirma por línea.
5. **Incidencia:** extravío (vencido el plazo máximo de tránsito), daño o destrucción.
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
- Número de remito único.

## Parámetros a tener en cuenta

Plazo máximo de tránsito antes de considerar extravío, y plazo de préstamo interbibliotecario (cuenta desde la entrega al socio).
