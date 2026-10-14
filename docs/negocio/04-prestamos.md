# 04. Solicitudes de préstamo

Proceso obligatorio 4 del enunciado. Las definiciones fueron confirmadas por Maxi; los puntos marcados como *A consultar* siguen abiertos con la cátedra.

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
| Registrado por | Usuario del personal |
| Remito de ida y de vuelta | Solo en préstamos interbibliotecarios |

## ¿Cómo se relaciona un préstamo con los ejemplares?

Un préstamo tiene **un ejemplar** (un registro por ejemplar prestado). Si el socio se lleva varios libros, son varios préstamos, cada uno con su estado y vencimiento. Esto simplifica vencimientos, multas y reportes. El límite de préstamos simultáneos se cuenta por socio.

## ¿Cómo determinamos cuándo inicia el préstamo?

- **Local:** inicia cuando el bibliotecario **entrega** el ejemplar al socio.
- **Interbibliotecario:** inicia cuando la sede destino **entrega** el ejemplar al socio, después de recibir el remito. El tiempo de traslado **no consume** el plazo del socio.

Hasta ese momento el préstamo está en estado `Solicitado` o `En envío`, y el ejemplar queda apartado para que nadie más lo pida.

## ¿Qué usuarios pueden solicitar un préstamo?

El **Bibliotecario** lo registra en nombre del socio. El Administrador puede consultarlos. *A consultar:* si el socio debe poder iniciar la solicitud por sí mismo.

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
