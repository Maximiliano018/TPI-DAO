# 02. Administración de socios

Proceso obligatorio 2 del enunciado. Los puntos marcados como *A consultar* siguen abiertos con la cátedra.

## ¿Qué datos se modelan?

| Campo | Obligatorio | Regla |
|-------|:---:|-------|
| Número de socio | Automático | Único, generado por el sistema con 5 dígitos (`00045`) |
| Documento | Sí | Tipo `DNI`, `LE`, `LC` o `Pasaporte`, y número. DNI, LE y LC: de 7 a 8 dígitos; pasaporte: de 6 a 9 letras o números. Se guarda sin puntos ni espacios. **Tipo y número únicos** |
| Nombre y apellido | Sí | Hasta 100 caracteres cada uno |
| Fecha de nacimiento | No | Entre 1900 y hoy. Dato informativo y de apoyo para detectar duplicados; no condiciona el alta |
| Correo y teléfono | **Al menos uno** | Correo con formato válido; teléfono en formato internacional E.164 (`+543514221234`) |
| Domicilio | No | Hasta 200 caracteres |
| Sede de alta | Automático | La del bibliotecario que lo registra (el administrador la elige). Es solo un **dato de registro**: no vincula al socio con la sede ni limita dónde puede operar |
| Fecha de alta | Automático | |
| Estado | Automático | `Habilitado`, `Inhabilitado` o `Baja` (ver [Estados](#estados-del-socio)) |
| Causas de inhabilitación | Automático | `Decisión administrativa`, `Préstamo vencido`, `Multa impaga`; puede tener varias a la vez |
| Tipo, fecha y motivo de la baja | Automático | Solo si está en baja (ver [Bajas](#bajas-del-socio)) |

## Estados del socio

| Estado | Significado | Puede pedir préstamos y reservar |
|--------|-------------|:---:|
| `Habilitado` | Sin causas de inhabilitación | Sí |
| `Inhabilitado` | Tiene al menos una causa vigente | No |
| `Baja` | Salió de la red (baja lógica); se conserva su historial y puede reactivarse | No |

El estado **no se elige**: sale de las causas vigentes. Con al menos una causa, el socio está inhabilitado; sin ninguna, habilitado.

| Causa | Origen | Cómo se levanta |
|-------|--------|-----------------|
| **Decisión administrativa** | La decide el administrador, con un motivo de 5 a 300 caracteres | Solo el administrador |
| **Préstamo vencido** | Automática: un préstamo pasa a `Vencido` | Sola, al devolver el material |
| **Multa impaga** | Automática: se genera una multa por atraso | Sola, cuando el personal registra la multa como saldada |

Un socio puede tener varias causas a la vez, y sigue inhabilitado mientras quede alguna. Cuando hay más de una, se muestra primero la de mayor **prioridad**: decisión administrativa, préstamo vencido y multa impaga, en ese orden.

## ¿Quién administra los socios?

El **Bibliotecario** (alta, modificación, creación de la cuenta de acceso, baja a pedido del socio y su reactivación) en cualquier sede de la red; el **Administrador** además inhabilita y levanta la inhabilitación administrativa, y registra y resuelve las bajas administrativas y por fallecimiento. Un socio pertenece a la red, no a una sola sede: puede pedir material en cualquier sede activa. No se puede dar de alta un socio en una sede en `Baja`, y la baja de la sede de alta no afecta al socio.

## ¿Quién puede ver esta información?

El personal (administrador y bibliotecario de cualquier sede) ve los datos de todos los socios; el socio ve solo los propios. Cada rol recibe únicamente los campos que le corresponden:

| Dato | Administrador | Bibliotecario | Socio (solo el suyo) |
|------|:---:|:---:|:---:|
| Número, documento, nombre, contacto, domicilio, fecha de nacimiento | ✔ | ✔ | ✔ |
| Estado, causas de inhabilitación y motivo administrativo | ✔ | ✔ | ✔ (tiene derecho a saber por qué) |
| Tipo, fecha y motivo de la baja; solicitud de reactivación | ✔ | ✔ | ✔ |
| Situación (préstamos, multas, reservas) | ✔ | ✔ | ✔ |
| Sede de alta | ✔ | ✔ | solo el nombre |
| Cuenta de acceso | completa | completa | solo su nombre de usuario |
| Auditoría (quién lo registró y lo modificó) | ✔ | — | — |
| Historial | ✔ | ✔ | ✔, sin la identidad del personal («Personal de la biblioteca») |

Los usuarios del personal (administradores y bibliotecarios) los ve y administra solo el administrador; cada usuario ve su propio perfil.

## Funcionalidades a cubrir

- Alta, modificación y consulta de socios.
- Búsqueda por número de socio, documento o apellido.
- Inhabilitación y rehabilitación.
- Baja con tipo, reactivación en mostrador y solicitud de reactivación desde la cuenta del socio.
- Consulta de la situación del socio: préstamos activos, vencidos, multas, reservas.
- Historial de cambios del socio.

## ¿Qué acciones puede realizar un socio?

- Consultar el catálogo y la disponibilidad por sede.
- Reservar un libro no disponible.
- Cancelar sus reservas.
- Ver sus préstamos (activos, vencidos, historial), fechas de vencimiento y multas.
- Ver sus propios datos y su historial, y solicitar su corrección al personal.

Su cuenta sigue activa aunque esté inhabilitado o dado de baja: puede entrar a ver su situación y hacer lo que lo lleva a habilitarse, pero no las operaciones diarias.

| Acción | Habilitado | Inhabilitado | En baja |
|--------|:---:|:---:|:---:|
| Ingresar y ver su ficha, situación e historial | ✔ | ✔ | ✔ (salvo fallecimiento) |
| Ver sus préstamos y multas con su monto | ✔ | ✔ | ✔ |
| Consultar el catálogo (solo lectura) | ✔ | ✔ | ✔ |
| Reservar y recibir préstamos | ✔ | — | — |
| Cancelar sus reservas | ✔ | ✔ | — (se cancelaron con la baja) |
| Devolver y saldar multas (en mostrador) | ✔ | ✔ | — (no tiene deudas) |
| Solicitar la reactivación desde su cuenta | — | — | ✔ (si el tipo de baja lo permite) |

**Deudas e inhabilitación.** Las deudas no llevan a la baja sino a la inhabilitación: la baja exige no tener préstamos en curso ni multas, así que un socio en baja nunca debe nada. El socio inhabilitado regulariza su situación así: ve desde su cuenta qué debe, devuelve el material o paga en el mostrador de cualquier sede, el personal registra la multa como saldada y el sistema lo habilita solo. El cobro real de las multas queda fuera del alcance.

La **solicitud de un préstamo** la registra el personal en nombre del socio (en mostrador). *A consultar con la cátedra* si el socio debe poder pedirlo directamente.

## Casos de uso y flujos

1. **Alta:** el bibliotecario carga los datos, el sistema valida duplicados y asigna el número de socio, estado `Habilitado`.
2. **Modificación de datos.**
3. **Inhabilitación:** manual (administrador) o automática por regla (multa impaga o préstamo vencido).
4. **Rehabilitación:** cuando desaparece la causa (se devuelve el material o se salda la multa) o por decisión del administrador.
5. **Baja del socio:** baja lógica con un tipo, solo si no tiene préstamos activos ni multas.
6. **Reactivación:** en mostrador, o por una solicitud del socio desde su cuenta que el personal aprueba o rechaza.

## Bajas del socio

La baja es lógica (el socio conserva su número e historial) y siempre lleva un **tipo**, que decide quién puede revertirla:

| Tipo | Cuándo | La registra | ¿Se reactiva? | Cuenta de acceso |
|------|--------|-------------|---------------|------------------|
| **A pedido del socio** | Se muda, renuncia o deja de usar la biblioteca | Bibliotecario o administrador | Sí: bibliotecario o administrador | Sigue activa |
| **Administrativa** | Sanción por faltas graves: daño o pérdida reiterados, mal uso | Administrador | Sí: solo el administrador | Sigue activa (ve el motivo) |
| **Fallecimiento** | Aviso de un familiar | Administrador | No: es definitiva | Se desactiva |

Reglas comunes a todos los tipos:

- Solo sin préstamos en curso ni multas pendientes; si los tiene, la baja se bloquea y se informa qué debe.
- Sus reservas activas se cancelan (se avisa antes de confirmar y se informa cuántas) y los ejemplares pasan al siguiente de la cola.
- La «baja por inactividad» (membresía que vence si no se renueva) queda fuera de alcance: no hay renovación de membresía.

### Prioridades

- **Entre estados:** `Baja` > `Inhabilitado` > `Habilitado`.
- **Entre causas de inhabilitación:** decisión administrativa > préstamo vencido > multa impaga (la que se muestra primero).
- **Entre tipos de baja:** fallecimiento > administrativa > a pedido (de la más grave a la más leve; define quién puede reactivar).

**La inhabilitación administrativa sobrevive a la baja.** Si un socio sancionado se da de baja y después se reactiva, vuelve `Inhabilitado` por decisión administrativa, con el mismo motivo, hasta que el administrador la levante. Así una baja y una reactivación no sirven para borrar una sanción. Si la baja misma era la sanción (baja administrativa), reactivarla equivale a levantarla.

### Reactivación

Un socio dado de baja vuelve con su mismo número de socio e historial, en lugar de registrarse de nuevo. Hay dos caminos, y en ambos decide quien puede reactivar según el tipo de baja:

1. **En mostrador:** el socio lo pide en cualquier sede y el personal lo reactiva.
2. **Desde su cuenta:** el socio envía una solicitud de reactivación (con un mensaje opcional). Queda pendiente y aparece en el listado de socios del personal; el personal la **aprueba** (el socio se reactiva) o la **rechaza** con un motivo (sigue en baja, ve el motivo en su historial y puede volver a pedirla). Hay una sola solicitud pendiente por vez.

Al reactivarse queda `Habilitado`, o `Inhabilitado` si tenía una inhabilitación administrativa.

### Escenarios típicos

| Escenario | Qué pasa |
|-----------|----------|
| Préstamo vencido | Queda inhabilitado solo → devuelve con atraso → se genera la multa y sigue inhabilitado por la multa → paga en mostrador → se habilita solo |
| Daño reiterado de material | El administrador lo inhabilita con un motivo; el socio lo ve en su cuenta; solo el administrador lo levanta |
| Socio sancionado que pide la baja | Se acepta si no tiene deudas; al reactivarse vuelve sancionado |
| Expulsión | Baja administrativa; puede ingresar y pedir la reactivación, y decide el administrador |
| Se muda y vuelve años después | Baja a pedido; al volver pide la reactivación desde su cuenta o en mostrador, y un bibliotecario la aprueba después de actualizar sus datos |
| Pide la baja con un libro en su poder | Se rechaza y se le informa qué debe |
| Fallecimiento | Baja por fallecimiento: se cancela su actividad pendiente de reservas y su cuenta deja de funcionar |

## ¿Qué se registra de cada socio? (historial)

Cada socio tiene su propio historial de solo inserción, con quién hizo cada cambio y cuándo:

| Evento | Qué guarda |
|--------|------------|
| Alta | Los datos iniciales |
| Modificación | Cada dato que cambió, con valor anterior y nuevo |
| Inhabilitación / rehabilitación manual | Estado anterior y nuevo, causas y motivo |
| Cambio automático | Estado y causas antes y después, y **qué lo provocó** («Préstamo P-2026-0012 vencido», «Multa del préstamo P-2026-0012 saldada»); lo hace el sistema |
| Baja | Tipo y motivo |
| Solicitud de reactivación / rechazo | El mensaje del socio / el motivo del rechazo |
| Reactivación | Cómo se reactivó (en mostrador o por solicitud aprobada) |
| Cuenta creada | El nombre de usuario |

**Por qué solo los eventos del socio.** Los préstamos, multas y reservas ya tienen sus propios movimientos con trazabilidad; copiarlos al historial del socio crearía dos fuentes de verdad. La ficha los muestra desde su módulo. El historial sí registra **cómo esos hechos afectaron al socio** (por ejemplo, que un préstamo vencido lo inhabilitó), que es lo que se necesita para responder un reclamo como «¿por qué me bloquearon el 3/11?».

## Validaciones y reglas

- Documento y datos de contacto obligatorios y con formato válido.
- Un socio `Inhabilitado` **no puede recibir préstamos ni hacer reservas** (regla del enunciado).
- Un socio no puede superar el máximo de préstamos simultáneos (parámetro, valor 3).
- No se elimina físicamente un socio con historial.

## ¿Se debe inhabilitar a un socio con devoluciones o multas pendientes?

**Sí.**

- Con un **préstamo vencido** sin devolver: queda inhabilitado hasta devolver.
- Con una **multa impaga**: queda inhabilitado hasta saldarla. El sistema solo registra la multa como saldada (el cobro real queda fuera del alcance).
- La inhabilitación no borra los préstamos en curso: el socio sigue obligado a devolver.

## ¿Cómo evitamos socios duplicados?

- Número y tipo de documento únicos.
- Búsqueda previa obligatoria en el alta (por documento y por nombre + fecha de nacimiento).
- Si el socio existe en estado de baja, se **reactiva** en lugar de crear uno nuevo.
