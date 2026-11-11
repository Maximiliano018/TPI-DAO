# 01. Sedes

Origen: [negocio/01-sedes.md](../negocio/01-sedes.md). Proceso obligatorio 1.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-SED-01 | El sistema debe permitir al administrador dar de alta una sede con código, nombre, domicilio (calle, número, localidad), teléfono, correo, responsable y horarios, todos obligatorios, y estado `Activa`. | Obligatorio |
| RF-SED-02 | El sistema debe permitir modificar los datos de una sede `Activa`, salvo el código, que es inmutable. Una sede en `Baja` no se puede modificar en absoluto: debe reactivarse primero. | Obligatorio |
| RF-SED-03 | El sistema debe permitir dar de baja una sede registrando fecha, motivo y usuario, y reactivarla sin condiciones adicionales. La baja es lógica; la reactivación limpia fecha, motivo y usuario de la baja. | Obligatorio |
| RF-SED-04 | El sistema debe bloquear la baja de una sede con actividad pendiente: préstamos en curso, remitos abiertos, reservas pendientes, ejemplares alojados en la sede, ejemplares propios fuera de ella o bibliotecarios activos asignados. Debe informar un mensaje general con el motivo y el detalle por tipo. No debe cancelar nada automáticamente. | Obligatorio |
| RF-SED-05 | El sistema debe impedir que una sede en `Baja` sea origen o destino de préstamos, reservas y envíos, y que reciba ejemplares, socios o bibliotecarios nuevos. | Obligatorio |
| RF-SED-06 | El sistema debe evitar sedes duplicadas, tanto en el alta como en la modificación: código y nombre únicos (sin distinguir mayúsculas ni tildes) y advertencia por dirección repetida, con posibilidad de corregir los datos o confirmar. | Obligatorio |
| RF-SED-07 | El sistema debe validar los horarios: al menos una franja semanal, sin solapamientos en el mismo día, cierre posterior a la apertura y hasta 4 franjas por día. Al modificar, el conjunto de franjas se reemplaza completo. Un día sin franjas se considera cerrado. | Obligatorio |
| RF-SED-08 | El sistema debe permitir listar sedes con paginación, filtro por estado, búsqueda por texto y orden, y consultar el detalle, con la visibilidad y los campos que corresponden a cada rol. | Obligatorio |
| RF-SED-09 | El sistema debe permitir al administrador registrar y eliminar excepciones de horario por sede (cierre total o parcial en una fecha, con motivo opcional), y mostrar si la sede está abierta en este momento. | Opcional |
| RF-SED-10 | El sistema debe registrar un historial de solo inserción por sede, con alta, modificaciones campo a campo, baja, reactivación y excepciones, con usuario y momento, consultable por el administrador. | Opcional |
| RF-SED-11 | El sistema debe restringir el domicilio a un catálogo cerrado de provincias y localidades (hoy, la provincia de Córdoba). | Opcional |
| RF-SED-12 | El sistema debe validar el formato de los datos: código (3 a 15 caracteres `A-Z`, `0-9`, `_`, guardado en mayúsculas), teléfono en formato internacional E.164 y correo electrónico válido. | Obligatorio |
| RF-SED-13 | El sistema debe evitar que cambios simultáneos se pisen: bloqueo de la fila en las operaciones que cambian el estado y control de versión en las modificaciones. | Obligatorio |

## Casos de uso

### CU-SED-01. Dar de alta una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. El administrador elige «Nueva sede» e ingresa código, nombre, calle, número, localidad, teléfono, correo, responsable y horarios.
  2. El sistema valida campos obligatorios, formatos, unicidad y horarios.
  3. El sistema crea la sede en estado `Activa` y registra el evento `Alta` en el historial.
- **Flujos alternativos:**
  - **A1 (paso 2): código o nombre duplicado.** El sistema rechaza el alta e indica la sede existente.
  - **A2 (paso 2): dirección ya registrada.** El sistema advierte e indica la sede existente; el administrador puede corregir los datos y reintentar, o confirmar y guardar de todas formas.
  - **A3 (paso 2): horarios inválidos.** El sistema rechaza y señala el día en conflicto.
  - **A4 (paso 2): falta un dato obligatorio.** El sistema rechaza y lo señala.
  - **A5 (paso 2): formato inválido** de código, teléfono o correo. El sistema rechaza y señala el campo.
  - **A6 (paso 2): localidad fuera del catálogo.** El sistema rechaza.
- **Postcondición:** la sede existe y está activa.

### CU-SED-02. Modificar una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. Selecciona la sede y edita nombre, domicilio, contacto, responsable u horarios.
  2. El sistema valida (mismas reglas que el alta), verifica la versión y guarda.
  3. El sistema registra el evento `Modificación` con cada campo cambiado.
- **Flujos alternativos:**
  - **A1 (paso 2): nuevo nombre duplicado.** Rechaza el cambio.
  - **A2 (paso 1): sede en `Baja`.** Rechaza: no se puede editar nada. Hay que reactivarla primero.
  - **A3 (paso 2): el domicilio cambió y ya existe otra sede en esa dirección.** Advierte; se puede corregir o confirmar.
  - **A4 (paso 2): intento de cambiar el código.** Rechaza: el código es inmutable.
  - **A5 (paso 2): la sede fue modificada por otra persona** desde que se abrió el formulario. Rechaza e indica que debe recargar.

### CU-SED-03. Dar de baja una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. Selecciona la sede e ingresa el motivo.
  2. El sistema bloquea la sede y verifica que no tenga actividad pendiente (los seis impedimentos del negocio).
  3. El sistema la pasa a `Baja` con fecha, motivo y usuario, y registra el evento `Baja`.
- **Flujos alternativos:**
  - **A1 (paso 2): hay actividad pendiente.** El sistema bloquea la baja con un mensaje general que explica el motivo y el detalle por tipo (préstamos, remitos, reservas, ejemplares alojados, ejemplares propios fuera, bibliotecarios). No cancela nada automáticamente. El administrador debe finalizar esas actividades, transferir los ejemplares y reasignar o desvincular a los bibliotecarios, y reintentar.
  - **A2 (paso 1): sede ya en `Baja`.** El sistema informa que no hay nada que hacer.
  - **A3 (paso 1): motivo vacío o fuera de los 5 a 300 caracteres.** Rechaza.
- **Postcondición:** la sede está en `Baja`; no admite nuevas operaciones ni ediciones.

### CU-SED-04. Reactivar una sede

- **Actor:** Administrador.
- **Flujo normal:** selecciona una sede en `Baja` y confirma; el sistema la pasa a `Activa`, limpia fecha, motivo y usuario de la baja, conserva el historial y registra el evento `Reactivación`.
- **Flujo alternativo A1:** la sede ya está activa; no se hace nada.

### CU-SED-05. Consultar sedes

- **Actores:** Administrador, Bibliotecario, Socio.
- **Flujo normal:** el usuario abre el listado, filtra, busca u ordena, y abre el detalle; el sistema muestra los datos permitidos para su rol.
- **Flujos alternativos:**
  - **A1:** el bibliotecario ve las sedes activas por defecto y puede pedir las dadas de baja; solo el administrador ve el motivo, la fecha y el responsable de la baja.
  - **A2:** el socio ve solo sedes activas, sin responsable ni estado.
  - **A3:** sin resultados, el sistema lo informa.
  - **A4:** un socio pide el detalle de una sede en `Baja`: el sistema responde «no encontrada».

### CU-SED-06. Gestionar excepciones de horario

- **Actor:** Administrador.
- **Flujo normal:**
  1. Abre la sede activa y elige «Agregar excepción».
  2. Indica fecha (o rango), tipo de cierre (total o parcial con horas) y, opcionalmente, el motivo.
  3. El sistema valida y guarda; registra el evento `Excepción agregada`.
  4. Para quitar una excepción de hoy o futura, la elimina; el sistema registra `Excepción eliminada`.
- **Flujos alternativos:**
  - **A1 (paso 3): fecha en el pasado.** Rechaza.
  - **A2 (paso 3): se superpone con otra excepción** de la misma fecha. Rechaza e indica la existente.
  - **A3 (paso 3): cierre parcial con horas inválidas.** Rechaza.
  - **A4 (paso 1): sede en `Baja`.** Rechaza.
  - **A5 (paso 2): rango de más de 31 días.** Rechaza.

### CU-SED-07. Consultar el historial de una sede

- **Actor:** Administrador.
- **Flujo normal:** abre el detalle de una sede y la pestaña de historial; el sistema lista los eventos, del más reciente al más antiguo, con usuario, fecha, tipo y cambios, paginados y filtrables por tipo y fechas.
- **Flujo alternativo A1:** bibliotecario o socio intentan consultarlo; el sistema lo rechaza por falta de permiso.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-SED-01 | RF-SED-01 | **Dado** datos válidos, **cuando** el administrador da de alta una sede, **entonces** queda `Activa` y visible en el listado. |
| CA-SED-02 | RF-SED-06 | **Dado** una sede «Centro», **cuando** se da de alta «CENTRO», **entonces** se rechaza por nombre duplicado. |
| CA-SED-03 | RF-SED-06 | **Dado** una sede con la misma dirección, **cuando** se da de alta otra, **entonces** el sistema advierte indicando la sede existente y no la crea hasta que se corrija la dirección o se confirme. |
| CA-SED-04 | RF-SED-07 | **Dado** dos franjas solapadas el mismo día, **cuando** se guarda, **entonces** el sistema rechaza el cambio. |
| CA-SED-05 | RF-SED-04 | **Dado** una sede con un préstamo activo como origen, **cuando** se solicita la baja, **entonces** se bloquea y se muestra el préstamo que la impide. |
| CA-SED-06 | RF-SED-04 | **Dado** una sede con un remito en estado `En tránsito`, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-07 | RF-SED-04 | **Dado** una sede con actividad pendiente, **cuando** se bloquea la baja, **entonces** ningún préstamo, remito ni reserva cambia de estado. |
| CA-SED-08 | RF-SED-03 | **Dado** una sede sin actividad pendiente, **cuando** se da de baja con motivo, **entonces** queda `Baja` con fecha, motivo y usuario. |
| CA-SED-09 | RF-SED-05 | **Dado** una sede en `Baja`, **cuando** se intenta crear un préstamo, reserva o envío con ella como origen o destino, **entonces** se rechaza. |
| CA-SED-10 | RF-SED-03 | **Dado** una sede en `Baja`, **cuando** se reactiva, **entonces** vuelve a `Activa`, se limpian fecha y motivo de baja y conserva su historial. |
| CA-SED-11 | RF-SED-08 | **Dado** un socio, **cuando** lista sedes, **entonces** ve solo las activas, sin motivo de baja ni responsable. |
| CA-SED-12 | RF-SED-06 | **Dado** una sede «Centro», **cuando** se modifica otra sede para llamarse «centro», **entonces** se rechaza por nombre duplicado. |
| CA-SED-13 | RF-SED-06 | **Dado** una sede con código `CEN`, **cuando** se da de alta otra con código `cen`, **entonces** se rechaza por código duplicado. |
| CA-SED-14 | RF-SED-02 | **Dado** una sede, **cuando** se intenta modificar su código, **entonces** se rechaza y el código no cambia. |
| CA-SED-15 | RF-SED-02 | **Dado** una sede en `Baja`, **cuando** se intenta modificar cualquier dato, horario o excepción, **entonces** se rechaza hasta que se reactive. |
| CA-SED-16 | RF-SED-04 | **Dado** una sede con un bibliotecario activo asignado, **cuando** se solicita la baja, **entonces** se bloquea e informa al bibliotecario. |
| CA-SED-17 | RF-SED-04 | **Dado** una sede con un ejemplar alojado en ella (propio o de otra sede) no dado de baja, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-18 | RF-SED-04 | **Dado** una sede cuyo ejemplar propio está prestado en otra sede o en tránsito, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-19 | RF-SED-04 | **Dado** una sede con una reserva `Pendiente` o `Disponible para retiro` con retiro en ella, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-20 | RF-SED-04 | **Dado** una sede destino de un remito `Generado`, `Empaquetado` o `Despachado`, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-21 | RF-SED-04 | **Dado** una sede cuya única actividad son préstamos devueltos, remitos cerrados, reservas finalizadas, socios dados de alta en ella o multas impagas, **cuando** se solicita la baja, **entonces** se acepta. |
| CA-SED-22 | RF-SED-04 | **Dado** una baja bloqueada, **cuando** se finalizan las actividades y se reasignan los bibliotecarios, **entonces** el reintento de la baja se acepta. |
| CA-SED-23 | RF-SED-04 | **Dado** una baja bloqueada por varios impedimentos, **cuando** el sistema responde, **entonces** incluye un mensaje general con el motivo y el detalle por tipo con cantidad y elementos. |
| CA-SED-24 | RF-SED-05 | **Dado** una sede en `Baja`, **cuando** se intenta dar de alta un socio en ella, **entonces** se rechaza. |
| CA-SED-25 | RF-SED-05 | **Dado** una sede en `Baja`, **cuando** se intenta asignar o reasignar un bibliotecario a ella, **entonces** se rechaza. |
| CA-SED-26 | RF-SED-07 | **Dado** un alta sin ninguna franja horaria, **cuando** se confirma, **entonces** se rechaza. |
| CA-SED-27 | RF-SED-07 | **Dado** una sede con horarios, **cuando** se modifica enviando un conjunto nuevo de franjas, **entonces** las anteriores se reemplazan por completo. |
| CA-SED-28 | RF-SED-07 | **Dado** una franja con cierre igual o anterior a la apertura, **cuando** se guarda, **entonces** se rechaza. |
| CA-SED-29 | RF-SED-09 | **Dado** una sede con una excepción de cierre total hoy, **cuando** se consulta, **entonces** figura como no abierta ahora, aunque su horario semanal indique atención. |
| CA-SED-30 | RF-SED-09 | **Dado** una excepción de cierre parcial entre dos horas, **cuando** se consulta la sede en esa franja, **entonces** figura como cerrada, y fuera de ella aplica el horario semanal. |
| CA-SED-31 | RF-SED-09 | **Dado** una excepción existente en una fecha, **cuando** se carga otra que se superpone, **entonces** se rechaza. |
| CA-SED-32 | RF-SED-09 | **Dado** una excepción con fecha pasada, **cuando** se intenta cargar, **entonces** se rechaza. |
| CA-SED-33 | RF-SED-09 | **Dado** una excepción de hoy o futura, **cuando** se elimina, **entonces** deja de aplicarse y queda registrada en el historial. |
| CA-SED-34 | RF-SED-10 | **Dado** un alta de sede, **cuando** se confirma, **entonces** el historial registra el evento `Alta` con el usuario y el momento. |
| CA-SED-35 | RF-SED-10 | **Dado** una modificación, **cuando** se guarda, **entonces** el historial registra cada campo cambiado con su valor anterior y nuevo. |
| CA-SED-36 | RF-SED-10 | **Dado** una baja y una reactivación, **cuando** se confirman, **entonces** el historial registra ambos eventos, la baja con su motivo. |
| CA-SED-37 | RF-SED-10 | **Dado** un bibliotecario o un socio, **cuando** pide el historial de una sede, **entonces** se rechaza por falta de permiso. |
| CA-SED-38 | RF-SED-11 | **Dado** una localidad que no está en el catálogo, **cuando** se da de alta una sede con ella, **entonces** se rechaza. |
| CA-SED-39 | RF-SED-12 | **Dado** un teléfono que no cumple el formato internacional o un correo inválido, **cuando** se guarda, **entonces** se rechaza señalando el campo. |
| CA-SED-40 | RF-SED-12 | **Dado** un código en minúsculas de 3 a 15 caracteres válidos, **cuando** se guarda, **entonces** se almacena en mayúsculas; y un código de menos de 3, más de 15 o con otros caracteres se rechaza. |
| CA-SED-41 | RF-SED-13 | **Dado** una sede abierta para edición por dos administradores, **cuando** el segundo guarda con una versión desactualizada, **entonces** se rechaza indicando que debe recargar. |
| CA-SED-42 | RF-SED-13 | **Dado** una baja de sede y una operación sobre ella que se ejecutan a la vez, **cuando** ambas se procesan, **entonces** se serializan: o la baja se bloquea por la operación o la operación se rechaza por sede en baja, nunca ambas se aplican. |
| CA-SED-43 | RF-SED-08 | **Dado** más sedes que el tamaño de página, **cuando** el usuario lista con filtro por estado y búsqueda, **entonces** recibe una página con el total y solo las sedes que cumplen. |
| CA-SED-44 | RF-SED-08 | **Dado** un bibliotecario, **cuando** consulta una sede de otra sede, **entonces** ve datos básicos y responsable, y no ve motivo, fecha ni responsable de la baja. |
| CA-SED-45 | RF-SED-08 | **Dado** un socio, **cuando** pide el detalle de una sede en `Baja`, **entonces** recibe «no encontrada» con un mensaje representativo. |
| CA-SED-46 | RF-SED-01 | **Dado** un bibliotecario o un socio, **cuando** intenta crear, modificar, dar de baja o reactivar una sede, **entonces** se rechaza por falta de permiso. |
| CA-SED-47 | RF-SED-03 | **Dado** una sede en `Baja`, **cuando** se pide otra baja, o una sede `Activa` y se pide reactivarla, **entonces** el sistema informa que no hay nada que hacer y no cambia nada. |
