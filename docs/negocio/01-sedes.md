# 01. Administración de sedes

Proceso obligatorio 1 del enunciado.

## ¿Qué datos se modelan?

**Definido** por el enunciado: dirección, datos de contacto, horarios y estado activo/baja. El resto de los campos y sus reglas se decidieron para esta implementación.

| Campo | Obligatorio | Regla |
|-------|:---:|-------|
| Código de sede | Sí | Identificador único corto (ej. `CEN`, `NORTE_2`). De 3 a 15 caracteres, solo `A-Z`, `0-9` y `_`. Se guarda siempre en mayúsculas (si se carga en minúsculas se convierte). **Inmutable** después del alta |
| Nombre | Sí | De 3 a 100 caracteres. Único en la red, sin distinguir mayúsculas, tildes, puntuación ni espacios de más (`Centro.` = `centro`) |
| Calle | Sí | De 2 a 100 caracteres |
| Número | Sí | Número de puerta (`1250`, `1250B`) o `S/N` |
| Localidad | Sí | Se elige de una **lista cerrada** (ver [Domicilio](#domicilio-lista-cerrada-de-provincias-y-localidades)) |
| Provincia | — | No se carga: se deduce de la localidad elegida |
| Teléfono | Sí | Formato internacional [E.164](#formato-de-contacto): `+543514221234` |
| Correo electrónico | Sí | Formato de correo válido; se guarda en minúsculas |
| Responsable | Sí | Nombre de la persona a cargo de la sede (3 a 100 caracteres) |
| Horarios semanales | Sí | Al menos una franja en la semana (ver [Horarios](#horarios-de-atención)) |
| Excepciones de horario | No | Cierres por fecha: feriados, días no laborables, etc. (ver [Excepciones](#excepciones-de-horario)) |
| Estado | Automático | `Activa` / `Baja`. Toda sede nace `Activa` |
| Fecha, motivo y responsable de la baja | Automático | Solo si está en baja |

**Por qué estos son obligatorios.** Una sede forma parte de una red donde se arman envíos: el personal de otra sede necesita saber dónde está, cómo contactarla, quién la atiende y cuándo recibe. Una sede sin alguno de esos datos no se puede usar para operar, así que el sistema no permite crearla incompleta.

## ¿Quién administra las sedes?

El **Administrador**. El bibliotecario no da de alta, modifica ni da de baja sedes.

## Funcionalidades a cubrir

- Alta, modificación y consulta de sedes.
- Baja y reactivación.
- Listado paginado con filtro por estado, búsqueda por texto y orden.
- Consulta de horarios, excepciones de horario y contacto.
- Alta y baja de excepciones de horario por fecha.
- Historial de cambios de cada sede (solo administrador).

## ¿Quién puede ver esta información?

| Dato | Administrador | Bibliotecario | Socio |
|------|:---:|:---:|:---:|
| Código, nombre | ✔ | ✔ | ✔ |
| Dirección (calle, número, localidad, provincia) | ✔ | ✔ | ✔ |
| Teléfono y correo | ✔ | ✔ | ✔ |
| Responsable | ✔ | ✔ | — |
| Horarios y excepciones vigentes (hoy y futuras) | ✔ | ✔ | ✔ |
| Indicador «abierta ahora» | ✔ | ✔ | ✔ |
| Estado | ✔ | ✔ | — (solo ve sedes activas) |
| Fecha, motivo y responsable de la baja | ✔ | — | — |
| Excepciones pasadas | ✔ | — | — |
| Versión, auditoría y historial | ✔ | — | — |
| Sedes que puede listar | todas | todas (activas por defecto) | solo activas |

Una sede en `Baja` **no existe** para el socio: si pide su detalle recibe «no encontrada», como si no estuviera registrada.

## ¿El personal de una sede ve las otras sedes?

Sí, en modo **solo lectura** y con datos básicos (nombre, dirección, contacto, responsable, horarios, estado). Es necesario para operar préstamos interbibliotecarios. La gestión operativa (préstamos, remitos, devoluciones) queda limitada a su propia sede, salvo los remitos entrantes y salientes que la involucran.

## Domicilio: lista cerrada de provincias y localidades

- La provincia y la localidad **no son texto libre**: se eligen de un catálogo cerrado.
- En esta etapa el catálogo contiene **solo la provincia de Córdoba (Argentina)**, con prioridad para la ciudad de Córdoba (capital) y las principales localidades de la provincia. El catálogo es ampliable por migración sin cambiar el sistema.
- El alta de nuevas localidades o provincias **no es una función del usuario**: se hace con una carga de datos controlada.
- Una localidad fuera del catálogo se rechaza.
- Fuera de alcance: barrios y código postal.

## Formato de contacto

- **Teléfono:** formato internacional E.164: signo `+`, código de país y número, de 8 a 15 dígitos en total (por ejemplo `+543514221234`, Córdoba capital). Se aceptan espacios, guiones y paréntesis al escribirlo; el sistema los quita y guarda solo `+` y dígitos.
- **Correo:** formato de correo válido, en minúsculas.

## Horarios de atención

- Cada franja tiene un **día de la semana** (lunes a domingo), una **hora de apertura** y una **hora de cierre**, en horas y minutos.
- Un mismo día puede tener **varias franjas** (por ejemplo mañana y tarde), hasta 4.
- La hora de cierre es **posterior** a la de apertura y ambas son del mismo día: no hay franjas que crucen la medianoche.
- Las franjas de un mismo día **no pueden solaparse**. Dos franjas contiguas (cierra a las 13:00 y abre a las 13:00) se aceptan.
- **«Cerrado» significa que ese día de la semana no tiene franjas.** No existe un valor explícito «cerrado».
- La sede debe tener **al menos una franja** en la semana.
- **Zona horaria única** para toda la red: `America/Argentina/Cordoba`. Las horas se guardan sin zona y se interpretan siempre en esa.
- Al modificar una sede, el conjunto de franjas se **reemplaza completo**: lo que se envía es el horario nuevo. No se editan franjas sueltas.

## Excepciones de horario

Una excepción cierra la sede en una fecha puntual aunque el horario semanal indique que atiende.

| Dato | Regla |
|------|-------|
| Fecha | Desde hoy en adelante; no se cargan excepciones en el pasado |
| Tipo | **Cierre total** (todo el día) o **cierre parcial** (entre una hora de inicio y una de fin) |
| Horas | Solo en el cierre parcial; el inicio es anterior al fin |
| Motivo | Opcional, hasta 150 caracteres (feriado, día no laborable, mantenimiento, etc.) |

- Cada sede administra **sus propias** excepciones; no hay un calendario global de feriados.
- Se puede cargar un **rango de fechas** de una sola vez (por ejemplo, vacaciones): el sistema crea una excepción por día, hasta 31 días.
- Dos excepciones de la misma sede y fecha no pueden solaparse; un cierre total excluye cualquier otra ese día.
- Se pueden eliminar las excepciones de hoy y futuras; las pasadas se conservan como historial.
- Una excepción **informa** el horario efectivo («abierta ahora», próximos cierres) y la usarán los procesos de envío y retiro. **No bloquea por sí sola** ninguna operación en esta etapa.
- Una sede en `Baja` no admite altas ni bajas de excepciones.

## Casos de uso y flujos

1. **Alta de sede:** el administrador carga los datos; el sistema valida formato, unicidad y horarios, y crea la sede `Activa`.
2. **Modificación:** actualiza nombre, dirección, contacto, responsable u horarios. El código no se puede cambiar.
3. **Baja de sede:** el administrador la solicita con un motivo; el sistema verifica que no haya actividad pendiente y la pasa a `Baja` con fecha, motivo y responsable.
4. **Reactivación:** vuelve a `Activa`, sin condiciones, y conserva el historial.
5. **Consulta:** listado y detalle según el rol.
6. **Excepciones de horario:** el administrador agrega o elimina cierres por fecha.
7. **Historial:** el administrador consulta qué cambió, quién lo hizo y cuándo.

## Validaciones y reglas

- Código, nombre, domicilio, teléfono, correo, responsable y horarios son obligatorios.
- Código y nombre únicos. El código no se modifica nunca.
- Los horarios no pueden solaparse en un mismo día y la hora de cierre es posterior a la de apertura.
- Una sede en `Baja` **no puede ser origen ni destino** de préstamos, reservas ni envíos (regla del enunciado).
- Una sede en `Baja` **no recibe**: altas de ejemplares nuevos, altas de socios, ni asignación de bibliotecarios.
- Una sede en `Baja` **no se edita** en absoluto (datos, horarios ni excepciones). Hay que reactivarla primero.
- Nunca se elimina físicamente una sede.
- Dos personas no pisan los cambios del otro: si alguien modificó la sede mientras se editaba, el sistema avisa y pide recargar.

## ¿Bajo qué criterio se habilita o deshabilita una sede?

El administrador decide. Motivos habituales: cierre definitivo, cierre temporal, obras o fusión con otra sede. Siempre queda registrado el motivo (de 5 a 300 caracteres), la fecha y quién la dio de baja.

La **baja temporal no tiene un tratamiento propio**: se resuelve con la baja y la reactivación manual. No hay fecha de reapertura programada.

## ¿Se puede dar de baja una sede con actividad pendiente?

**No.** La baja se bloquea mientras exista **cualquiera** de los siguientes impedimentos. «Actividad pendiente» es todo lo que dejaría a la sede, a un socio o a un ejemplar sin dónde continuar.

| # | Impedimento | Condición que bloquea |
|---|-------------|-----------------------|
| 1 | **Préstamos en curso** | Préstamos `Solicitado`, `En envío`, `Activo` o `Vencido` con la sede como **origen o destino** |
| 2 | **Remitos abiertos** | Remitos `Generado`, `Empaquetado`, `Despachado` o `En tránsito` con la sede como **origen o destino** |
| 3 | **Reservas pendientes** | Reservas `Pendiente` o `Disponible para retiro` con **retiro en la sede** |
| 4 | **Ejemplares alojados en la sede** | Ejemplares que **están físicamente en la sede** (propios o de otras sedes) y no están dados de baja, en cualquier estado: disponible, reservado, apartado, prestado, en revisión |
| 5 | **Ejemplares propios fuera de la sede** | Ejemplares **de su propiedad** que están en otra sede o en tránsito y no están dados de baja |
| 6 | **Bibliotecarios asignados** | Bibliotecarios **activos** asignados a la sede |

Para poder dar de baja:

- Los **ejemplares** (4 y 5) deben haberse **transferido a otra sede** con un remito de traslado, que además cambia la sede propietaria, o haberse dado de baja. Los ejemplares prestados o fuera de la sede deben volver o transferirse antes.
- Los **préstamos, remitos y reservas** (1, 2 y 3) deben haber finalizado: devueltos, recibidos, anulados, cumplidos o cancelados.
- Los **bibliotecarios** (6) deben **reasignarse a otra sede activa** o **desvincularse**. Como todo bibliotecario debe tener una sede, desvincular significa **dar de baja su usuario** (sigue en el historial, pero no cuenta como asignado).

### Qué no bloquea la baja

| Situación | Motivo |
|-----------|--------|
| Préstamos `Devuelto` o `Cancelado` | Ya terminaron; son historial |
| Remitos `Recibido`, `Extraviado`, `Dañado`, `Destruido` o `Anulado` | Están cerrados |
| Reservas `Cumplida`, `Cancelada` o `Vencida` | Ya terminaron |
| Ejemplares dados de baja | Salieron del circuito |
| Socios dados de alta en la sede | El socio pertenece a la red, no a una sede (ver abajo) |
| Multas impagas de préstamos de la sede | La multa es del socio, no de la sede |
| Incidencias registradas | Son historial; los ejemplares afectados se controlan en 4 y 5 |
| Bibliotecarios dados de baja | Ya no operan |

### Cómo se informa

La baja **nunca cancela ni modifica automáticamente** nada: se bloquea hasta que las operaciones finalicen. Ninguna operación cambia de estado cuando la baja se rechaza.

La respuesta es siempre la misma estructura:

- Un **mensaje general** que nombra la sede y dice que tiene actividad pendiente, con el resumen por tipo (por ejemplo: «No se puede dar de baja la sede Centro: tiene actividad pendiente (3 préstamos en curso, 1 remito abierto, 2 bibliotecarios asignados). Finalice o transfiera esa actividad y vuelva a intentar»).
- El **detalle por tipo de impedimento**: cantidad y una muestra de los elementos (hasta 10 por tipo) para poder encontrarlos.

## ¿Qué pasa con los socios y las sedes?

- Un socio **no está vinculado** a una sede: puede operar en todas las sedes activas.
- La «sede de alta» del socio es solo un dato de registro (dónde se dio de alta). No limita lo que puede hacer y **no impide** la baja de esa sede.
- No se puede **dar de alta un socio** en una sede en `Baja`.

## ¿Qué pasa con los bibliotecarios?

- Todo bibliotecario activo tiene **una sede activa**.
- Un bibliotecario solo se puede asignar o reasignar a una **sede activa**.
- Un bibliotecario de una sede dada de baja no existe: la baja se bloquea hasta que todos se reasignen o se desvinculen.

## ¿Qué se registra de cada sede? (historial)

Cada sede tiene su **propio historial** de eventos de su ciclo de vida y de sus datos. Es solo de inserción: no se modifica ni se borra.

| Evento | Cuándo | Qué guarda |
|--------|--------|------------|
| Alta | Se crea la sede | Todos los datos iniciales |
| Modificación | Se guarda un cambio | Cada campo que cambió, con valor anterior y nuevo (incluye horarios y la confirmación de dirección duplicada) |
| Baja | Se da de baja | Estado anterior y nuevo, motivo |
| Reactivación | Se reactiva | Estado anterior y nuevo |
| Excepción agregada / eliminada | Se carga o borra un cierre | Fecha, tipo, horas y motivo |

Cada evento guarda además **quién** lo hizo y **cuándo**.

**Lo que no entra en este historial.** Los préstamos, remitos, reservas, ejemplares y devoluciones de una sede **no se copian** a su historial: cada proceso ya tiene su propio registro de movimientos con trazabilidad (ver [Préstamos](04-prestamos.md), [Remitos](05-remitos.md), [Reservas](06-reservas.md)). La actividad de una sede se consulta con los reportes y listados de cada proceso filtrados por sede, que usan esos registros. Así hay una sola fuente de verdad por dato.

Los intentos de baja rechazados no quedan en el historial de la sede (no cambió nada); se registran en el log de la aplicación.

## ¿Cómo evitamos sedes duplicadas?

- **Código** único y **nombre** único. El código se compara en mayúsculas; el nombre, sin distinguir mayúsculas, tildes, puntuación ni espacios de más. Se rechaza el alta o el cambio.
- **Dirección repetida:** se compara la combinación localidad + calle + número, normalizada (sin mayúsculas, tildes, puntuación ni espacios de más, y con abreviaturas unificadas: `Av.` = `Avenida`, `Gral.` = `General`, etc.). Se compara contra **todas** las sedes, activas o en baja.
  - No se rechaza: se **advierte**, mostrando la sede que ya está en esa dirección.
  - El administrador puede **corregir** los datos y reintentar, o **confirmar** que la duplicación es intencional.
  - Pasa igual al **modificar**, pero solo cuando cambia el domicilio; si no cambió, no se vuelve a advertir.

## Reactivación

La reactivación depende solamente de que la sede esté en `Baja`. Se limpia la fecha, el motivo y el responsable de la baja de la sede, y el evento queda en el historial. Los datos, horarios y excepciones vuelven como estaban.
