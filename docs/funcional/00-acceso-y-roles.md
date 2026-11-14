# 00. Acceso y roles

Roles: **Administrador**, **Bibliotecario** (asociado a una sede) y **Socio**. Matriz completa en [contexto y actores](../negocio/00-contexto-y-actores.md#matriz-de-permisos-resumen).

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-ACC-01 | El sistema debe identificar a cada usuario y asignarle exactamente un rol: Administrador, Bibliotecario o Socio. | Obligatorio |
| RF-ACC-02 | Todo bibliotecario debe estar asociado a una sede; el administrador no pertenece a ninguna. | Obligatorio |
| RF-ACC-03 | El sistema debe restringir cada operación y consulta a los roles autorizados por la matriz de permisos. | Obligatorio |
| RF-ACC-04 | Un bibliotecario solo puede operar (registrar préstamos, devoluciones, recepciones) en su sede, y consultar datos básicos de las demás. | Obligatorio |
| RF-ACC-05 | Un socio solo puede ver sus propios datos, préstamos, reservas y multas. | Obligatorio |
| RF-ACC-06 | El administrador debe poder dar de alta, modificar y dar de baja usuarios del personal. | Obligatorio |
| RF-ACC-07 | Toda operación que modifica datos debe registrar el usuario y el momento. | Obligatorio |
| RF-ACC-08 | El sistema debe resolver los permisos de cada usuario a partir de su rol en el servidor, en cada solicitud, y aplicar el cambio de rol, sede o estado del usuario de inmediato, sin esperar a que venza la sesión. | Obligatorio |
| RF-ACC-09 | El sistema debe asignar o reasignar un bibliotecario solo a una sede `Activa`, y permitir desvincularlo dándolo de baja. | Obligatorio |
| RF-ACC-10 | El sistema debe cerrar la sesión por vencimiento del token y rechazar tokens inválidos, vencidos o de usuarios dados de baja. | Obligatorio |
| RF-ACC-11 | Cada operación sobre préstamos se habilita por permiso, no por rol. El bibliotecario (`PRESTAMO_REGISTRAR`) registra préstamos en nombre de cualquier socio en su sede; el socio (`PRESTAMO_SOLICITAR_PROPIO`) los pide solo para sí: el socio sale de su sesión y un pedido a nombre de otro se rechaza. El administrador no registra préstamos. | Obligatorio |

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
  - **A2 (paso 2): usuario dado de baja.** El sistema rechaza el ingreso.
- **Postcondición:** sesión iniciada con el rol y la sede del usuario.

### CU-ACC-02. Administrar usuarios del personal

- **Actor:** Administrador.
- **Flujo normal:**
  1. El administrador elige alta, modificación o baja.
  2. Carga los datos (nombre, credenciales, rol; sede si es bibliotecario).
  3. El sistema valida y registra el cambio.
- **Flujos alternativos:**
  - **A1 (paso 3): usuario duplicado.** El sistema rechaza el alta e indica el usuario existente.
  - **A2 (paso 2): bibliotecario sin sede.** El sistema rechaza el alta.
  - **A3 (paso 1): baja de un usuario con operaciones en curso.** Se permite: la baja es lógica y conserva el historial.
  - **A4 (paso 2): sede en `Baja`.** El sistema rechaza asignar a un bibliotecario a una sede dada de baja.
  - **A5 (paso 1): reasignar a un bibliotecario.** El administrador elige otra sede **activa**; el cambio rige desde la siguiente solicitud del usuario.
  - **A6 (paso 1): reactivar a un bibliotecario cuya sede está en `Baja`.** El sistema rechaza hasta que se asigne una sede activa.

### CU-ACC-03. Cerrar sesión y expiración

- **Actor:** cualquier usuario.
- **Flujo normal:** el usuario cierra la sesión y el cliente descarta el token. Si no lo hace, el token vence solo a los 60 minutos.
- **Flujos alternativos:**
  - **A1:** token vencido o inválido. El sistema responde que no está autenticado y el cliente lleva al login.
  - **A2:** el usuario fue dado de baja con el token vigente. La siguiente solicitud se rechaza.

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
| CA-ACC-17 | RF-ACC-11 | **Dado** un administrador, **cuando** intenta registrar un préstamo, **entonces** el sistema lo rechaza por falta de permiso. |
