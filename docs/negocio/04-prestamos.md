# 04. Solicitudes de préstamo

Proceso obligatorio 4 del enunciado. Los puntos marcados como *A consultar* siguen abiertos con la cátedra.

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

El **Bibliotecario** lo registra en nombre del socio. El Administrador puede consultarlos pero no puede registrar/solicitar un préstamo. El **Socio** puede solicitar un préstamo solo en el caso que sea de tipo **interbibliotecario**. Si el sistema determina que corresponde un préstamo local, rechaza la solicitud y le indica que se acerque al mostrador de la sede. La solicitud de préstamos locales por parte del socio queda para un evolutivo; la implementación debe permitir habilitarla sin rediseñar el flujo.

## Parámetros

Ver [parámetros globales](00-contexto-y-actores.md#parámetros-globales-configurables): plazo local, plazo interbibliotecario, renovaciones y máximo de préstamos por socio.

## Inicio del flujo

El usuario inicia un único flujo, **«Solicitud de préstamo»**, indicando el socio y el **libro**. No elige el tipo de préstamo ni el ejemplar: los determina el sistema según la disponibilidad por sede.

### Sede de la solicitud (sede destino)

Es la sede donde el socio retira y devuelve el ejemplar.

- **Bibliotecario:** la sede asignada a su usuario. No se puede cambiar.
- **Socio:** la **sede del socio** (atributo del socio, ver [Socios](02-socios.md)) se propone por defecto; el socio puede cambiarla por otra sede activa antes de confirmar.

### Determinación del tipo

1. El sistema valida al socio antes de evaluar la disponibilidad: que esté `Habilitado`, que no supere el máximo de préstamos simultáneos y que no tenga ya un préstamo abierto del mismo libro. También valida que la sede destino esté activa.
2. Si el libro tiene ejemplares `Disponible` **en la sede destino**, corresponde un **préstamo local**: el sistema asigna cualquiera de ellos.
3. Si no, pero hay ejemplares `Disponible` en **otras sedes activas**, corresponde un **préstamo interbibliotecario**: la sede origen es la que tiene **más ejemplares disponibles** de ese libro (en caso de empate, la de **menor id**), y el sistema asigna uno de sus ejemplares.
4. Si no hay ejemplares disponibles en ninguna sede activa, el sistema **rechaza** la solicitud y **ofrece reservar** el libro con retiro en la sede destino (ver [Reservas](06-reservas.md)).
5. Antes de confirmar, el usuario ve un resumen con el tipo, la sede origen y el plazo. La asignación definitiva se hace al confirmar: si el ejemplar asignado dejó de estar disponible en ese momento, el sistema vuelve a determinar el tipo.

Si quien solicita es el **socio** y el paso 2 determina un préstamo local, el sistema rechaza la solicitud e informa que hay ejemplares disponibles en la sede y que se acerque al mostrador.

## Préstamo local

1. El socio pide un libro en una sede, y el sistema encuentra ejemplares `Disponible` **de esa sede**.
2. El sistema asigna cualquiera de esos ejemplares (origen = destino).
3. El sistema valida las reglas (incluyendo el control de 
    - cantidad de préstamos activos por socio vs límite permitido
    - estado del socio).
4. Se entrega el ejemplar: préstamo `Activo`, ejemplar `Prestado`, se calcula el vencimiento.

## Préstamo entre sedes

1. El socio o el bibliotecario pide un libro que no tiene ejemplares disponibles en la sede destino, pero sí en otra.
2. El sistema elige la sede origen (la de más ejemplares disponibles; si hay empate, la de menor id) y asigna uno de sus ejemplares.
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

- El tipo de préstamo y el ejemplar no los elige el usuario: los determina el sistema según la disponibilidad por sede.
- Un socio solo puede solicitar préstamos interbibliotecarios; los locales los registra el bibliotecario.
- Si no hay ejemplares disponibles en ninguna sede activa, no se registra el préstamo y se ofrece una reserva.
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
