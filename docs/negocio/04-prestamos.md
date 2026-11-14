# 04. Solicitudes de préstamo

Proceso obligatorio 4 del enunciado.

## ¿Qué datos se modelan?

| Campo | Detalle |
|-------|---------|
| Número de préstamo | Único |
| Socio | Quien solicita |
| Ejemplar | Copia física prestada |
| Tipo | `Local` / `Interbibliotecario` |
| Sede origen | Donde está el ejemplar |
| Sede destino | Donde el socio retira y devuelve |
| Fecha de solicitud | Alta del préstamo |
| Fecha de inicio | Entrega al socio (ver abajo) |
| Fecha de vencimiento | Inicio + plazo |
| Fecha de devolución | Cuando el socio lo devuelve |
| Cantidad de renovaciones | |
| Estado | Ver ciclo de vida |
| Registrado por | Usuario que lo pidió: el personal (en mostrador) o el propio socio (autogestión) |
| Fecha límite de retiro | Último día para retirarlo en la sede destino |
| Remito de ida y de vuelta | Solo en préstamos interbibliotecarios |

## ¿Cómo se relaciona un préstamo con los ejemplares?

Un préstamo tiene **un ejemplar** (un registro por ejemplar prestado). Si el socio se lleva varios libros, son varios préstamos, cada uno con su estado y vencimiento. Esto simplifica vencimientos, multas y reportes. El límite de préstamos simultáneos se cuenta por socio.

## ¿Cómo determinamos cuándo inicia el préstamo?

- **Local:** inicia cuando el bibliotecario **entrega** el ejemplar al socio.
- **Interbibliotecario:** inicia cuando la sede destino **entrega** el ejemplar al socio, después de recibir el remito. El tiempo de traslado **no consume** el plazo del socio.

Hasta ese momento el préstamo está en estado `Solicitado` o `En envío`, y el ejemplar queda apartado para que nadie más lo pida. Para que un ejemplar no quede apartado para siempre, hay un **plazo de retiro** (ver más abajo).

## ¿Qué usuarios pueden solicitar un préstamo?

Lo deciden los **permisos**, no el rol: dar un permiso a un rol habilita el camino sin cambiar el código.

| Quién | Permiso | Cómo | A nombre de quién |
|-------|---------|------|-------------------|
| **Bibliotecario** | `PRESTAMO_REGISTRAR` | En el mostrador: elige el socio y el **ejemplar** (la copia que el socio tiene en la mano o una de otra sede). El socio retira en la sede del bibliotecario. | Cualquier socio |
| **Socio** | `PRESTAMO_SOLICITAR_PROPIO` | Desde su cuenta: elige el **libro** y la sede donde lo retira; el sistema elige el ejemplar y el tipo. | **Solo él mismo**: el socio sale de su sesión; un pedido a nombre de otro se rechaza |
| **Administrador** | ninguno | No registra préstamos: los consulta. | — |

Estas decisiones salen de una propuesta del equipo (rama `docs/decision-automatica-tipo-prestamo`), actualizada con lo que ya estaba implementado: la elección automática se usa en la autogestión, y el socio también puede pedir préstamos locales.

### Solicitud del socio: el sistema elige el tipo y el ejemplar

1. El socio elige el libro y la **sede de retiro** (se propone su sede de alta; puede elegir otra sede activa).
2. El sistema controla primero al socio (habilitado, sin superar el máximo de préstamos, sin otro préstamo abierto del mismo libro), sin mirar la disponibilidad.
3. Si hay ejemplares `Disponible` del libro **en la sede de retiro**, el préstamo es **local** y queda apartado para que lo retire en el mostrador.
4. Si no, es **interbibliotecario** desde la sede activa con **más** ejemplares disponibles (con empate, la de menor id).
5. Si ninguna sede activa tiene disponibles, se rechaza y se ofrece **reservar**.
6. Antes de confirmar, el socio ve la propuesta (tipo, sedes y plazos). Si al confirmar la disponibilidad cambió, el sistema lo avisa y muestra la nueva propuesta para que la confirme.

### Plazo de retiro y cancelación

- Un préstamo pedido y no entregado tiene **3 días** (parámetro) para retirarse: el local, desde la solicitud; el interbibliotecario, desde que llega a la sede destino. Vencido el plazo, el sistema lo cancela solo: el local libera el ejemplar (y lo ofrece a la cola de reservas) y el interbibliotecario vuelve a su sede con un remito de retorno.
- El socio puede **cancelar su solicitud** mientras está `Solicitado` (antes de que salga de la sede origen). Después, la cancelación la maneja el personal.

## Parámetros

Ver [parámetros globales](00-contexto-y-actores.md#parámetros-globales-configurables): plazo local, plazo interbibliotecario, renovaciones y máximo de préstamos por socio.

## Préstamo local

1. El socio pide un libro en una sede.
2. El bibliotecario busca un ejemplar `Disponible` **de esa sede**.
3. El sistema valida las reglas.
4. Se entrega el ejemplar: préstamo `Activo`, ejemplar `Prestado`, se calcula el vencimiento.

## Préstamo entre sedes

1. El socio pide un libro que no tiene ejemplares disponibles en su sede, pero sí en otra (origen).
2. El bibliotecario elige el ejemplar de la sede origen. Sede destino = sede donde está el socio.
3. El sistema valida las reglas y crea el préstamo `Solicitado`; el ejemplar queda reservado para ese préstamo.
4. La sede origen prepara el envío: se genera el remito (ver [Remitos](05-remitos.md)); el préstamo pasa a `En envío`.
5. La sede destino recibe el ejemplar y lo entrega al socio: préstamo `Activo`, ejemplar `Prestado`.
6. Al terminar, el socio devuelve en la sede destino y el ejemplar vuelve a la sede origen mediante un segundo remito (ver [Devoluciones](07-devoluciones.md)).

## Ciclo de vida del préstamo

```
Solicitado ──▶ En envío ──▶ Activo ──▶ Devuelto
    │              │          │
    │              │          └──▶ Vencido ──▶ Devuelto
    └──────────────┴──▶ Cancelado
```

| Estado | Significado |
|--------|-------------|
| `Solicitado` | Registrado y validado; ejemplar apartado |
| `En envío` | Solo interbibliotecario; el ejemplar viaja a la sede destino |
| `Activo` | El socio lo tiene en su poder |
| `Vencido` | Pasó la fecha de vencimiento sin devolución |
| `Devuelto` | El socio lo devolvió (final) |
| `Cancelado` | Anulado antes de entregarse (final) |

El estado `Vencido` puede calcularse a partir de la fecha de vencimiento en lugar de guardarse.

## ¿Cómo verificamos el estado de un préstamo?

Consultando el préstamo, que expone su estado actual y su historial de cambios. En un préstamo interbibliotecario, el detalle incluye además el estado actual del remito.

## ¿Se considera el caso de que el socio no devuelva?

**Sí.** Pasada la fecha de vencimiento el préstamo queda `Vencido`, empieza a acumular multa por día y el socio se inhabilita. *No se contempla extravío por parte del socio como flujo propio* en esta etapa; si el material no vuelve, se registra como incidencia de extravío en la devolución (ver [Devoluciones](07-devoluciones.md)).

## Validaciones y reglas

- Un socio solo pide préstamos para sí mismo; el personal los registra en nombre de cualquier socio.
- Un préstamo sin retirar se cancela solo al vencer su plazo de retiro.
- No prestar ejemplares que no estén `Disponible`. *(enunciado)*
- No prestar a socios `Inhabilitados`. *(enunciado)*
- No prestar ejemplares que no pertenezcan a la **sede origen** del préstamo. *(enunciado)*
- No iniciar préstamos desde o hacia una sede en `Baja`. *(enunciado)*
- Controlar la fecha de vencimiento. *(enunciado)*
- No superar el máximo de préstamos simultáneos del socio.
- En un préstamo local, origen y destino coinciden.
- Un mismo socio no puede tener dos préstamos activos del mismo libro.
- No se renueva un préstamo vencido ni uno con reservas pendientes sobre el libro.

## Estados que se modelan

Préstamo: `Solicitado`, `En envío`, `Activo`, `Vencido`, `Devuelto`, `Cancelado`. Ejemplar: ver [catálogo](03-catalogo.md). Remito: ver [remitos](05-remitos.md). Los tres ciclos están acoplados y se documentan juntos en la parte técnica.
