# 02. Socios

Origen: [negocio/02-socios.md](../negocio/02-socios.md). Proceso obligatorio 2.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-SOC-01 | El sistema debe permitir al personal registrar un socio con documento, nombre, apellido, contacto y fecha de nacimiento, asignando un número de socio único y estado `Habilitado`. | Obligatorio |
| RF-SOC-02 | El sistema debe evitar socios duplicados: tipo y número de documento únicos, con búsqueda previa por documento y por nombre más fecha de nacimiento. | Obligatorio |
| RF-SOC-03 | El sistema debe permitir modificar los datos de un socio. | Obligatorio |
| RF-SOC-04 | El sistema debe permitir buscar socios por número de socio, documento o apellido. | Obligatorio |
| RF-SOC-05 | El sistema debe inhabilitar automáticamente a un socio con un préstamo vencido o una multa pendiente, registrando el motivo, y rehabilitarlo cuando ambas causas desaparezcan. | Obligatorio |
| RF-SOC-06 | El administrador debe poder inhabilitar y rehabilitar manualmente a un socio, con motivo. | Obligatorio |
| RF-SOC-07 | El sistema debe impedir préstamos y reservas a un socio `Inhabilitado`. | Obligatorio |
| RF-SOC-08 | El sistema debe limitar los préstamos simultáneos de un socio al máximo configurado. | Obligatorio |
| RF-SOC-09 | El sistema debe permitir dar de baja lógica a un socio sin préstamos activos ni multas pendientes, y reactivar a un socio dado de baja en lugar de duplicarlo. | Obligatorio |
| RF-SOC-10 | El sistema debe mostrar la situación de un socio: préstamos activos y vencidos, multas, reservas e historial. El socio solo ve la propia. | Obligatorio |

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

- **Actor:** Administrador.
- **Flujo normal:** solicita la baja con motivo; el sistema verifica que no tenga préstamos activos ni multas y lo pasa a `Baja`. Para reactivar, selecciona al socio en `Baja` y confirma.
- **Flujos alternativos:**
  - **A1:** tiene préstamos activos o multas; bloquea la baja y los lista.
  - **A2:** tiene reservas pendientes; el sistema las cancela al darlo de baja, informándolo.

### CU-SOC-05. Consultar la situación de un socio

- **Actor:** Bibliotecario, Administrador, Socio (solo la propia).
- **Flujo normal:** busca al socio y abre su ficha con estado, préstamos, vencimientos, multas y reservas.
- **Flujo alternativo A1:** el socio intenta ver a otro; el sistema lo rechaza.

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
