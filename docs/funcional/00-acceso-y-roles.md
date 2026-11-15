# 00. Acceso y roles

Roles: **Administrador**, **Bibliotecario** (asociado a una sede) y **Socio**. Matriz completa en [contexto y actores](../negocio/00-contexto-y-actores.md#matriz-de-permisos-resumen).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-ACC-01 | El sistema debe identificar a cada usuario y asignarle exactamente un rol: Administrador, Bibliotecario o Socio. | Obligatorio |
| RF-ACC-02 | Todo bibliotecario debe estar asociado a una sede; el administrador no pertenece a ninguna. | Obligatorio |
| RF-ACC-03 | El sistema debe restringir cada operación y consulta a los roles autorizados por la matriz de permisos. | Obligatorio |
| RF-ACC-04 | Un bibliotecario solo puede operar (registrar préstamos, devoluciones, recepciones) en su sede, y consultar datos básicos de las demás. El administrador opera en cualquier sede (RF-ACC-13). | Obligatorio |
| RF-ACC-05 | Un socio solo puede ver sus propios datos, préstamos, reservas y multas. | Obligatorio |
| RF-ACC-06 | El administrador debe poder listar (filtrando por rol, sede, estado o texto), dar de alta, modificar, dar de baja y reactivar usuarios del personal. El alta fija usuario, nombre, contraseña, rol (Administrador o Bibliotecario) y sede; la modificación cambia solo el nombre y la sede (el rol y el usuario no cambian). | Obligatorio |
| RF-ACC-07 | Toda operación que modifica datos debe registrar el usuario y el momento (también el cambio de un parámetro de negocio, RF-ACC-12). | Obligatorio |
| RF-ACC-08 | El sistema debe resolver los permisos de cada usuario a partir de su rol en el servidor, en cada solicitud, y aplicar el cambio de rol, sede o estado del usuario de inmediato, sin esperar a que venza la sesión. | Obligatorio |
| RF-ACC-09 | El sistema debe asignar o reasignar un bibliotecario solo a una sede `Activa`, y permitir desvincularlo dándolo de baja. | Obligatorio |
| RF-ACC-10 | El sistema debe cerrar la sesión por vencimiento del token y rechazar tokens inválidos, vencidos o de usuarios dados de baja. | Obligatorio |
| RF-ACC-11 | Cada operación sobre préstamos se habilita por permiso, no por rol. El bibliotecario (`PRESTAMO_REGISTRAR`) registra préstamos en nombre de cualquier socio en su sede; el socio (`PRESTAMO_SOLICITAR_PROPIO`) los pide solo para sí: el socio sale de su sesión y un pedido a nombre de otro se rechaza. El administrador registra préstamos como el bibliotecario, indicando la sede donde el socio lo retira. | Obligatorio |
| RF-ACC-12 | El administrador debe poder consultar y modificar los parámetros de negocio (plazos, límites y montos). Cada valor se valida (montos de 0 a 1.000.000; renovaciones de 0 a 3650; los demás plazos y límites de 1 a 3650) y rige desde la siguiente operación, sin alterar multas ya emitidas. Cada cambio queda en una auditoría inalterable (quién, cuándo, valor anterior y nuevo) que el administrador consulta. | Obligatorio |
| RF-ACC-13 | El administrador tiene los permisos completos del proyecto: además de administrar la red, opera en el mostrador de **cualquier sede** (préstamos, remitos, reservas, devoluciones, ejemplares, multas). En una operación nueva indica la sede (la de retiro del préstamo, la de origen del remito); en las siguientes, la sede sale de la entidad. Solo quedan fuera las acciones de autogestión del socio (pedir un préstamo para sí, pagar en línea), que exigen una ficha de socio. | Obligatorio |

## Casos de uso

### CU-ACC-01. Iniciar sesión

- **Actor:** cualquier usuario.
- **Precondición:** el usuario existe y está activo.
- **Flujo normal:**
  1. El usuario ingresa sus credenciales.
  2. El sistema valida las credenciales.
  3. El sistema identifica el rol (y la sede, si es bibliotecario) y muestra las opciones permitidas.
- **Flujos alternativos:**
  - **A1 (paso 2): credenciales inválidas.** El sistema informa el error sin indicar cuál dato falló y permite reintentar.
  - **A2 (paso 2): usuario dado de baja.** El sistema rechaza el ingreso con el mismo mensaje de A1 (no revela que la cuenta existe).
- **Postcondición:** sesión iniciada con el rol y la sede del usuario.

### CU-ACC-02. Administrar usuarios del personal

- **Actor:** Administrador.
- **Flujo normal:**
  1. El administrador elige alta, modificación, baja o reactivación (puede buscar al usuario por rol, sede, estado o texto).
  2. En el alta carga usuario, nombre, contraseña, rol (Administrador o Bibliotecario) y sede si es bibliotecario; en la modificación, solo nombre y sede.
  3. El sistema valida y registra el cambio.
- **Flujos alternativos:**
  - **A1 (paso 3): usuario duplicado.** El sistema rechaza el alta e indica el usuario existente.
  - **A2 (paso 2): bibliotecario sin sede.** El sistema rechaza el alta.
  - **A3 (paso 1): baja de un usuario con operaciones en curso.** Se permite: la baja es lógica y conserva el historial.
  - **A4 (paso 2): sede en `Baja`.** El sistema rechaza asignar a un bibliotecario a una sede dada de baja.
  - **A5 (paso 1): reasignar a un bibliotecario.** El administrador elige otra sede **activa**; el cambio rige desde la siguiente solicitud del usuario.
  - **A6 (paso 1): reactivar a un bibliotecario cuya sede está en `Baja`.** El sistema rechaza hasta que se asigne una sede activa.
  - **A7 (paso 2): administrador con sede, o rol Socio.** El sistema rechaza el alta: el administrador no pertenece a ninguna sede y las cuentas de socio se crean desde la ficha del socio (CU-SOC-08). El rol y el usuario no se pueden modificar.
  - **A8 (paso 2): usuario o contraseña con formato inválido.** El sistema rechaza y señala el campo (usuario de 3 a 50 caracteres `a-z`, `0-9`, `.`, `_`, `-`; contraseña de 10 a 128 caracteres con al menos una letra y un número).
  - **A9 (paso 1): el administrador intenta darse de baja a sí mismo.** El sistema lo rechaza.
  - **A10 (paso 1): el usuario ya está en baja (o ya está activo).** El sistema informa que no hay nada que hacer.

### CU-ACC-03. Cerrar sesión y expiración

- **Actor:** cualquier usuario.
- **Flujo normal:** el usuario cierra la sesión y el cliente descarta el token. Si no lo hace, el token vence solo a los 60 minutos.
- **Flujos alternativos:**
  - **A1:** token vencido o inválido. El sistema responde que no está autenticado y el cliente lleva al login.
  - **A2:** el usuario fue dado de baja con el token vigente. La siguiente solicitud se rechaza.

### CU-ACC-04. Configurar parámetros de negocio

- **Actor:** Administrador.
- **Flujo normal:**
  1. El administrador abre **Parámetros** en el portal y ve los valores vigentes, cada uno con quién lo modificó por última vez y cuándo.
  2. Modifica el valor de uno y lo guarda.
  3. El sistema lo valida, lo guarda y registra el cambio en la auditoría (usuario, momento, valor anterior y nuevo); rige desde la siguiente operación (las multas ya emitidas no cambian).
  4. El administrador consulta el historial de cambios, del más reciente al más antiguo.
- **Flujos alternativos:**
  - **A1 (paso 2): clave inexistente.** El sistema responde que el parámetro no existe.
  - **A2 (paso 3): valor no numérico o fuera de rango.** El sistema rechaza y explica el rango válido.
  - **A3 (paso 1): bibliotecario o socio.** El sistema rechaza por falta de permiso.
  - **A4 (paso 3): el valor es igual al vigente.** El sistema lo rechaza: no hay cambio que registrar.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-ACC-01 | RF-ACC-03 | **Dado** un socio, **cuando** intenta registrar un préstamo, **entonces** el sistema rechaza la operación por falta de permiso. |
| CA-ACC-02 | RF-ACC-04 | **Dado** un bibliotecario de la sede A, **cuando** intenta registrar una devolución en la sede B, **entonces** el sistema rechaza la operación. |
| CA-ACC-03 | RF-ACC-04 | **Dado** un bibliotecario de la sede A, **cuando** consulta la sede B, **entonces** ve solo sus datos básicos. |
| CA-ACC-04 | RF-ACC-05 | **Dado** un socio, **cuando** consulta préstamos, **entonces** ve únicamente los propios. |
| CA-ACC-05 | RF-ACC-02 | **Dado** el alta de un bibliotecario sin sede, **cuando** se confirma, **entonces** el sistema la rechaza. |
| CA-ACC-06 | RF-ACC-07 | **Dado** cualquier modificación de datos, **cuando** se confirma, **entonces** queda registrado el usuario y el momento. |
| CA-ACC-07 | RF-ACC-01 | **Dado** credenciales inválidas, **cuando** se intenta ingresar, **entonces** no se inicia sesión y el mensaje no revela cuál dato es incorrecto. |
| CA-ACC-08 | RF-ACC-08 | **Dado** un bibliotecario con sesión iniciada, **cuando** el administrador lo reasigna a otra sede, **entonces** su siguiente solicitud ya opera sobre la nueva sede. |
| CA-ACC-09 | RF-ACC-09 | **Dado** una sede en `Baja`, **cuando** se asigna o reasigna a ella un bibliotecario, **entonces** el sistema lo rechaza. |
| CA-ACC-10 | RF-ACC-09 | **Dado** un bibliotecario dado de baja, **cuando** se consulta la baja de su sede, **entonces** ya no cuenta como asignado. |
| CA-ACC-11 | RF-ACC-10 | **Dado** un token vencido o manipulado, **cuando** se llama a cualquier endpoint protegido, **entonces** se responde no autenticado. |
| CA-ACC-12 | RF-ACC-10 | **Dado** un usuario dado de baja con un token todavía vigente, **cuando** hace una solicitud, **entonces** se rechaza. |
| CA-ACC-13 | RF-ACC-03 | **Dado** un bibliotecario, **cuando** intenta administrar usuarios del personal, **entonces** el sistema rechaza la operación por falta de permiso. |
| CA-ACC-14 | RF-ACC-06 | **Dado** un administrador, **cuando** intenta darse de baja a sí mismo, **entonces** el sistema lo rechaza. |
| CA-ACC-15 | RF-ACC-11 | **Dado** un socio, **cuando** pide un préstamo a nombre de otro socio (o usa el registro de mostrador), **entonces** el sistema lo rechaza por falta de permiso y no crea el préstamo. |
| CA-ACC-16 | RF-ACC-11 | **Dado** un bibliotecario o un administrador, **cuando** usa la solicitud propia del socio, **entonces** el sistema lo rechaza por falta de permiso. |
| CA-ACC-17 | RF-ACC-11 | **Dado** un administrador, **cuando** registra un préstamo sin indicar la sede de retiro, **entonces** el sistema lo rechaza y pide la sede; indicándola, el préstamo se registra a su nombre y él puede entregarlo y registrar la devolución. |
| CA-ACC-18 | RF-ACC-07 | **Dado** un parámetro, **cuando** el administrador cambia su valor, **entonces** la auditoría registra quién, cuándo, el valor anterior y el nuevo, la lista de parámetros muestra el último cambio, un valor igual al vigente se rechaza, la auditoría no se puede modificar ni borrar y el bibliotecario no la consulta. |
| CA-ACC-19 | RF-ACC-13 | **Dado** un administrador, **cuando** genera un remito indicando la sede origen y lo empaqueta, despacha y recibe, o cancela una reserva de cualquier sede, **entonces** el sistema lo permite; sin sede origen el remito se rechaza, y un bibliotecario sigue sin poder operar en otra sede. |
