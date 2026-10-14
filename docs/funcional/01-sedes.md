# 01. Sedes

Origen: [negocio/01-sedes.md](../negocio/01-sedes.md). Proceso obligatorio 1.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-SED-01 | El sistema debe permitir al administrador dar de alta una sede con código, nombre, dirección, contacto, horarios y estado `Activa`. | Obligatorio |
| RF-SED-02 | El sistema debe permitir modificar los datos de una sede. | Obligatorio |
| RF-SED-03 | El sistema debe permitir dar de baja una sede registrando fecha y motivo, y reactivarla. La baja es lógica. | Obligatorio |
| RF-SED-04 | El sistema debe bloquear la baja de una sede que tenga actividad pendiente: préstamos activos o vencidos, remitos no cerrados, reservas pendientes o ejemplares propios fuera de ella. Debe informar qué elementos lo impiden. | Obligatorio |
| RF-SED-05 | El sistema debe impedir que una sede en `Baja` sea origen o destino de préstamos, reservas y envíos, y que reciba ejemplares o socios nuevos. | Obligatorio |
| RF-SED-06 | El sistema debe evitar sedes duplicadas: código y nombre únicos (sin distinguir mayúsculas ni tildes) y advertencia por dirección repetida. | Obligatorio |
| RF-SED-07 | El sistema debe validar los horarios: sin solapamientos en el mismo día y cierre posterior a la apertura. | Obligatorio |
| RF-SED-08 | El sistema debe permitir listar sedes con filtro por estado y consultar el detalle (contacto y horarios), con la visibilidad que corresponda a cada rol. | Obligatorio |

## Casos de uso

### CU-SED-01. Dar de alta una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. El administrador elige «Nueva sede» e ingresa código, nombre, dirección, contacto y horarios.
  2. El sistema valida campos obligatorios, unicidad y horarios.
  3. El sistema crea la sede en estado `Activa`.
- **Flujos alternativos:**
  - **A1 (paso 2): código o nombre duplicado.** El sistema rechaza el alta e indica la sede existente.
  - **A2 (paso 2): dirección ya registrada.** El sistema advierte; el administrador puede confirmar o cancelar.
  - **A3 (paso 2): horarios inválidos.** El sistema rechaza y señala el día en conflicto.
  - **A4 (paso 2): falta un dato obligatorio.** El sistema rechaza y lo señala.
- **Postcondición:** la sede existe y está activa.

### CU-SED-02. Modificar una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. Selecciona la sede y edita dirección, contacto u horarios.
  2. El sistema valida y guarda.
- **Flujos alternativos:**
  - **A1 (paso 2): nuevo nombre o código duplicado.** Rechaza el cambio.
  - **A2 (paso 1): sede en `Baja`.** Se permite editar contacto y dirección, pero no horarios operativos.

### CU-SED-03. Dar de baja una sede

- **Actor:** Administrador.
- **Flujo normal:**
  1. Selecciona la sede e ingresa el motivo.
  2. El sistema verifica que no tenga actividad pendiente.
  3. El sistema la pasa a `Baja` con fecha y motivo.
- **Flujos alternativos:**
  - **A1 (paso 2): hay actividad pendiente.** El sistema bloquea la baja y lista los préstamos, remitos, reservas y ejemplares que la impiden. No cancela nada automáticamente. El administrador debe finalizar esas actividades o trasladar los ejemplares y reintentar.
  - **A2 (paso 1): sede ya en `Baja`.** El sistema informa que no hay nada que hacer.
  - **A3 (paso 1): motivo vacío.** Rechaza.
- **Postcondición:** la sede está en `Baja`; no admite nuevas operaciones.

### CU-SED-04. Reactivar una sede

- **Actor:** Administrador.
- **Flujo normal:** selecciona una sede en `Baja` y confirma; el sistema la pasa a `Activa` conservando el historial.
- **Flujo alternativo A1:** la sede ya está activa; no se hace nada.

### CU-SED-05. Consultar sedes

- **Actores:** Administrador, Bibliotecario, Socio.
- **Flujo normal:** el usuario abre el listado, filtra por estado y abre el detalle; el sistema muestra los datos permitidos para su rol.
- **Flujos alternativos:**
  - **A1:** socio o bibliotecario ven solo sedes activas por defecto y datos básicos; el motivo y la fecha de baja los ve solo el administrador.
  - **A2:** sin resultados, el sistema lo informa.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-SED-01 | RF-SED-01 | **Dado** datos válidos, **cuando** el administrador da de alta una sede, **entonces** queda `Activa` y visible en el listado. |
| CA-SED-02 | RF-SED-06 | **Dado** una sede «Centro», **cuando** se da de alta «CENTRO», **entonces** se rechaza por nombre duplicado. |
| CA-SED-03 | RF-SED-06 | **Dado** una sede con la misma dirección, **cuando** se da de alta otra, **entonces** el sistema advierte y requiere confirmación. |
| CA-SED-04 | RF-SED-07 | **Dado** dos franjas solapadas el mismo día, **cuando** se guarda, **entonces** el sistema rechaza el cambio. |
| CA-SED-05 | RF-SED-04 | **Dado** una sede con un préstamo activo como origen, **cuando** se solicita la baja, **entonces** se bloquea y se muestra el préstamo que la impide. |
| CA-SED-06 | RF-SED-04 | **Dado** una sede con un remito en estado `En tránsito`, **cuando** se solicita la baja, **entonces** se bloquea. |
| CA-SED-07 | RF-SED-04 | **Dado** una sede con actividad pendiente, **cuando** se bloquea la baja, **entonces** ningún préstamo, remito ni reserva cambia de estado. |
| CA-SED-08 | RF-SED-03 | **Dado** una sede sin actividad pendiente, **cuando** se da de baja con motivo, **entonces** queda `Baja` con fecha, motivo y usuario. |
| CA-SED-09 | RF-SED-05 | **Dado** una sede en `Baja`, **cuando** se intenta crear un préstamo, reserva o envío con ella como origen o destino, **entonces** se rechaza. |
| CA-SED-10 | RF-SED-03 | **Dado** una sede en `Baja`, **cuando** se reactiva, **entonces** vuelve a `Activa` y conserva su historial. |
| CA-SED-11 | RF-SED-08 | **Dado** un socio, **cuando** lista sedes, **entonces** ve solo las activas, sin motivo de baja. |
