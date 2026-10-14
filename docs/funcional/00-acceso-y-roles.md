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
