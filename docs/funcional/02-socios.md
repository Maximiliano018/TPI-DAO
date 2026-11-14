# 02. Socios

Origen: [negocio/02-socios.md](../negocio/02-socios.md). Proceso obligatorio 2.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-SOC-01 | El sistema debe permitir al personal registrar un socio con documento, nombre, apellido, contacto (al menos correo o teléfono) y, opcionalmente, fecha de nacimiento y domicilio, asignando un número de socio único y estado `Habilitado`. | Obligatorio |
| RF-SOC-02 | El sistema debe evitar socios duplicados: tipo y número de documento únicos, con búsqueda previa por documento y por nombre más fecha de nacimiento. | Obligatorio |
| RF-SOC-03 | El sistema debe permitir modificar los datos de un socio. | Obligatorio |
| RF-SOC-04 | El sistema debe permitir buscar socios por número de socio, documento o apellido. | Obligatorio |
| RF-SOC-05 | El sistema debe inhabilitar automáticamente a un socio con un préstamo vencido o una multa pendiente, registrando el motivo, y rehabilitarlo cuando ambas causas desaparezcan. | Obligatorio |
| RF-SOC-06 | El administrador debe poder inhabilitar y rehabilitar manualmente a un socio, con motivo. | Obligatorio |
| RF-SOC-07 | El sistema debe impedir préstamos y reservas a un socio `Inhabilitado`. | Obligatorio |
| RF-SOC-08 | El sistema debe limitar los préstamos simultáneos de un socio al máximo configurado. | Obligatorio |
| RF-SOC-09 | El sistema debe permitir dar de baja lógica a un socio sin préstamos activos ni multas pendientes, y reactivar a un socio dado de baja en lugar de duplicarlo. | Obligatorio |
| RF-SOC-10 | El sistema debe mostrar la situación de un socio: préstamos activos y vencidos, multas, reservas e historial. El socio solo ve la propia. | Obligatorio |
| RF-SOC-11 | La baja debe tener un tipo: a pedido del socio (la registra y la reactiva el personal), administrativa (solo el administrador) o por fallecimiento (solo el administrador; es definitiva y desactiva la cuenta). Una inhabilitación administrativa debe conservarse tras la baja y la reactivación. | Obligatorio |
| RF-SOC-12 | El socio dado de baja debe poder solicitar su reactivación desde su cuenta; el personal que puede reactivarlo según el tipo de baja la aprueba o la rechaza con motivo. También debe poder reactivarse en mostrador. | Obligatorio |
| RF-SOC-13 | El sistema debe registrar un historial de solo inserción por socio (alta, modificaciones campo a campo, inhabilitaciones y rehabilitaciones con su origen, bajas, solicitudes, reactivaciones y cuenta), con usuario y momento. | Obligatorio |
| RF-SOC-14 | Cada rol debe recibir solo los datos del socio que puede ver: el socio no ve la auditoría ni la identidad del personal; el bibliotecario no ve la auditoría. | Obligatorio |

## Casos de uso

### CU-SOC-01. Registrar un socio

- **Actor:** Bibliotecario (o Administrador).
- **Flujo normal:**
  1. Busca previamente por documento y por nombre y fecha de nacimiento.
  2. Al no encontrarlo, ingresa los datos.
  3. El sistema valida formato y unicidad.
  4. Asigna el número de socio, estado `Habilitado`, fecha de alta y sede de alta.
- **Flujos alternativos:**
  - **A1 (paso 1): el socio ya existe habilitado.** El sistema muestra el existente y no permite crear otro.
  - **A2 (paso 1): el socio existe dado de baja.** El sistema ofrece reactivarlo (CU-SOC-04).
  - **A3 (paso 3): documento duplicado.** Rechaza el alta.
  - **A4 (paso 3): dato obligatorio faltante o con formato inválido.** Rechaza y lo señala.
  - **A5 (paso 3): sede del usuario en `Baja`.** Rechaza el alta.

### CU-SOC-02. Modificar datos de un socio

- **Actor:** Bibliotecario, Administrador.
- **Flujo normal:** busca al socio, edita datos y guarda; el sistema valida y registra el cambio.
- **Flujos alternativos:**
  - **A1:** el nuevo documento ya pertenece a otro socio; rechaza.
  - **A2:** el socio pidió la corrección desde su cuenta; el personal la aplica (el socio no edita directamente).

### CU-SOC-03. Inhabilitar y rehabilitar a un socio

- **Actor:** Sistema (automático), Administrador (manual).
- **Flujo normal (automático):**
  1. Un préstamo del socio pasa a `Vencido`, o se le genera una multa.
  2. El sistema lo pasa a `Inhabilitado` con motivo (`Préstamo vencido` o `Multa impaga`).
  3. Al devolver el material y saldar la multa, el sistema lo rehabilita.
- **Flujos alternativos:**
  - **A1 (paso 3): queda otra causa vigente.** Sigue inhabilitado con la causa restante.
  - **A2:** inhabilitación manual por decisión administrativa; solo el administrador puede levantarla.
  - **A3:** la inhabilitación no cancela préstamos en curso; el socio debe devolverlos igual.

### CU-SOC-04. Dar de baja o reactivar a un socio

- **Actor:** Bibliotecario (baja a pedido del socio), Administrador (todas).
- **Flujo normal:** elige el tipo de baja y el motivo; el sistema verifica que no tenga préstamos activos ni multas y lo pasa a `Baja`. Para reactivar en mostrador, selecciona al socio en `Baja` y confirma; vuelve `Habilitado`, o `Inhabilitado` si tenía una inhabilitación administrativa.
- **Flujos alternativos:**
  - **A0:** un bibliotecario intenta una baja administrativa o por fallecimiento, o reactivar una baja administrativa; el sistema lo rechaza por falta de permiso.
  - **A3:** baja por fallecimiento: el sistema desactiva la cuenta de acceso del socio; la baja no se puede reactivar.
  - **A1:** tiene préstamos activos o multas; bloquea la baja y los lista.
  - **A2:** tiene reservas pendientes; el sistema avisa antes de confirmar, las cancela al darlo de baja e informa cuántas canceló (los ejemplares pasan al siguiente de la cola).

### CU-SOC-05. Consultar la situación de un socio

- **Actor:** Bibliotecario, Administrador, Socio (solo la propia).
- **Flujo normal:** busca al socio y abre su ficha con estado, préstamos, vencimientos, multas, reservas e historial; cada rol ve solo los datos que le corresponden.
- **Flujos alternativos:**
  - **A1:** el socio intenta ver a otro; el sistema lo rechaza.
  - **A2:** el socio está inhabilitado o dado de baja: igual puede ingresar y ver su situación, pero no reservar ni recibir préstamos.

### CU-SOC-06. Solicitar la reactivación desde la cuenta

- **Actores:** Socio dado de baja; Bibliotecario o Administrador (según el tipo de baja).
- **Flujo normal:**
  1. El socio ingresa con su cuenta, abre «Mis datos» y pide la reactivación, con un mensaje opcional.
  2. La solicitud queda pendiente y aparece en el listado de socios del personal.
  3. El personal la aprueba: el socio se reactiva y el evento queda en su historial.
- **Flujos alternativos:**
  - **A1 (paso 3):** el personal la rechaza con un motivo; el socio sigue en baja, ve el motivo en su historial y puede volver a pedirla.
  - **A2 (paso 1):** ya tiene una solicitud pendiente; el sistema lo informa.
  - **A3 (paso 1):** la baja fue por fallecimiento; no hay reactivación posible.
  - **A4 (paso 3):** la baja es administrativa y la intenta resolver un bibliotecario; el sistema lo rechaza.

### CU-SOC-07. Consultar el historial de un socio

- **Actores:** Bibliotecario, Administrador, Socio (solo el propio).
- **Flujo normal:** abre la pestaña de historial de la ficha; el sistema lista los eventos del más reciente al más antiguo, con autor, fecha, estados, motivo, origen y cambios.
- **Flujo alternativo A1:** el socio ve el suyo sin la identidad del personal («Personal de la biblioteca», «Sistema»).

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-SOC-01 | RF-SOC-01 | **Dado** datos válidos, **cuando** se registra un socio, **entonces** se crea `Habilitado` con número de socio único. |
| CA-SOC-02 | RF-SOC-02 | **Dado** un socio con DNI 30.111.222, **cuando** se registra otro con el mismo DNI, **entonces** se rechaza. |
| CA-SOC-03 | RF-SOC-09 | **Dado** un socio dado de baja, **cuando** se intenta registrarlo de nuevo, **entonces** el sistema ofrece reactivar el existente. |
| CA-SOC-04 | RF-SOC-07 | **Dado** un socio `Inhabilitado`, **cuando** se intenta crear un préstamo o una reserva, **entonces** se rechaza. |
| CA-SOC-05 | RF-SOC-05 | **Dado** un socio con un préstamo que pasa a `Vencido`, **cuando** se detecta el vencimiento, **entonces** el socio queda `Inhabilitado` con motivo `Préstamo vencido`. |
| CA-SOC-06 | RF-SOC-05 | **Dado** un socio inhabilitado por préstamo vencido y por multa, **cuando** devuelve el material pero la multa sigue pendiente, **entonces** continúa inhabilitado. |
| CA-SOC-07 | RF-SOC-05 | **Dado** un socio sin otras causas, **cuando** devuelve lo vencido y salda la multa, **entonces** vuelve a `Habilitado`. |
| CA-SOC-08 | RF-SOC-08 | **Dado** un socio con 3 préstamos activos, **cuando** se intenta un cuarto, **entonces** se rechaza. |
| CA-SOC-09 | RF-SOC-09 | **Dado** un socio con un préstamo activo, **cuando** se pide su baja, **entonces** se bloquea. |
| CA-SOC-10 | RF-SOC-06 | **Dado** un socio inhabilitado por decisión administrativa, **cuando** un bibliotecario intenta rehabilitarlo, **entonces** se rechaza. |
| CA-SOC-11 | RF-SOC-10 | **Dado** un socio autenticado, **cuando** consulta a otro socio, **entonces** se rechaza. |
| CA-SOC-12 | RF-SOC-11 | **Dado** un bibliotecario, **cuando** registra la baja a pedido de un socio, **entonces** se acepta; **cuando** intenta una baja administrativa o por fallecimiento, o reactivar una administrativa, **entonces** se rechaza por falta de permiso. |
| CA-SOC-13 | RF-SOC-11 | **Dado** un socio con cuenta, **cuando** el administrador lo da de baja por fallecimiento, **entonces** su cuenta queda desactivada y la baja no se puede reactivar. |
| CA-SOC-14 | RF-SOC-11 | **Dado** un socio inhabilitado por decisión administrativa, **cuando** se lo da de baja y se lo reactiva, **entonces** vuelve `Inhabilitado` con el mismo motivo. |
| CA-SOC-15 | RF-SOC-12 | **Dado** un socio dado de baja a pedido, **cuando** pide la reactivación desde su cuenta, **entonces** la solicitud queda pendiente y visible para el personal, y al aprobarla vuelve a `Habilitado`. |
| CA-SOC-16 | RF-SOC-12 | **Dado** una solicitud pendiente, **cuando** el personal la rechaza con motivo, **entonces** el socio sigue en baja, ve el motivo en su historial y puede volver a pedirla. |
| CA-SOC-17 | RF-SOC-12 | **Dado** un socio inhabilitado o dado de baja, **cuando** ingresa con su cuenta, **entonces** ve su situación pero no puede reservar ni recibir préstamos. |
| CA-SOC-18 | RF-SOC-13 | **Dado** un cambio en el socio, **cuando** se confirma, **entonces** el historial lo registra con autor y momento; los cambios automáticos, sin autor y con su origen. |
| CA-SOC-19 | RF-SOC-13 | **Dado** un socio, **cuando** consulta su historial, **entonces** lo ve sin la identidad del personal; **cuando** pide el de otro socio, **entonces** se rechaza. |
| CA-SOC-20 | RF-SOC-14 | **Dado** un socio, un bibliotecario y un administrador, **cuando** consultan la misma ficha, **entonces** solo el administrador ve la auditoría y el socio solo ve el nombre de usuario de su cuenta. |
