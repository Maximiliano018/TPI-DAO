# 08. Reportes

Origen: [negocio/08-reportes.md](../negocio/08-reportes.md). El enunciado exige al menos 4 reportes no triviales; se especifican los 6 sugeridos. R1 a R4 son los no triviales.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-REP-01 | **R1.** El sistema debe emitir el movimiento de ejemplares entre sedes: por par origen → destino, cantidad de envíos, de ejemplares y tiempo promedio de tránsito (recepción − despacho) sobre remitos `Recibido`. | Obligatorio |
| RF-REP-02 | **R2.** El sistema debe emitir la tasa de envíos exitosos e incidencias: total, % `Recibido`, % `Extraviado`, `Dañado` y `Destruido`, con detalle por sede. Excluye `Anulado` y los remitos abiertos. | Obligatorio |
| RF-REP-03 | **R3.** El sistema debe emitir el ranking de libros más solicitados en préstamos interbibliotecarios no cancelados, con sedes origen y destino más frecuentes. | Obligatorio |
| RF-REP-04 | **R4.** El sistema debe emitir los préstamos vencidos con socio, libro, sede, días de atraso y multa acumulada a la fecha, el total adeudado y las multas pendientes. | Obligatorio |
| RF-REP-05 | **R5.** El sistema debe emitir la disponibilidad de catálogo por libro y sede: totales, disponibles, prestados, reservados y en tránsito. | Obligatorio |
| RF-REP-06 | **R6.** El sistema debe emitir los préstamos activos con su vencimiento y los remitos abiertos con estado, origen, destino y antigüedad. | Obligatorio |
| RF-REP-07 | Cada reporte debe permitir los filtros definidos (rango de fechas, sede, estado, categoría o socio, según corresponda) y mostrar un mensaje claro si no hay datos. | Obligatorio |
| RF-REP-08 | El acceso a cada reporte debe respetar los roles: R1, R4 y R6 para el administrador y el bibliotecario (su sede); R2 y R3 para el administrador; R5 para todos. | Obligatorio |
| RF-REP-09 | Los reportes deben calcularse sobre datos registrados (historial de estados, préstamos, multas), sin datos cargados a mano. | Obligatorio |
| RF-REP-10 | El sistema debe permitir exportar el resultado de un reporte (por ejemplo, a CSV). | Opcional |

## Casos de uso

### CU-REP-01. Emitir un reporte

- **Actores:** según RF-REP-08.
- **Flujo normal:**
  1. El usuario elige el reporte (R1 a R6).
  2. Define los filtros (rango de fechas, sede, etc.).
  3. El sistema valida los filtros y calcula el resultado desde los datos.
  4. Muestra el resultado con su detalle y totales.
- **Flujos alternativos:**
  - **A1 (paso 1): rol sin permiso.** El sistema no ofrece el reporte y rechaza el acceso directo.
  - **A2 (paso 2): rango de fechas inválido (fin anterior al inicio).** Rechaza y pide corregir.
  - **A3 (paso 3): sin datos para los filtros.** Informa que no hay resultados.
  - **A4 (paso 2): bibliotecario filtra por otra sede.** El sistema limita el resultado a su sede.
  - **A5 (paso 4): el usuario pide exportar (opcional).** El sistema genera el archivo con el mismo contenido.

### CU-REP-02. Interpretar R1: tiempo de tránsito

- **Flujo normal:** el sistema toma, de cada remito `Recibido` del período, las fechas de `Despachado` y `Recibido` del historial de estados, promedia por ruta y muestra los envíos de cada ruta.
- **Flujos alternativos:**
  - **A1:** remitos sin fecha de despacho (anulados); se excluyen.
  - **A2:** una ruta con un solo envío; el promedio es ese valor.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-REP-01 | RF-REP-01 | **Dado** dos remitos A → B recibidos con tránsitos de 2 y 4 días, **cuando** se emite R1, **entonces** la ruta A → B muestra 2 envíos y un tiempo promedio de 3 días. |
| CA-REP-02 | RF-REP-01 | **Dado** un remito A → B todavía `En tránsito`, **cuando** se emite R1, **entonces** no entra en el promedio. |
| CA-REP-03 | RF-REP-01 | **Dado** un remito con 3 ejemplares, **cuando** se emite R1, **entonces** cuenta 1 envío y 3 ejemplares. |
| CA-REP-04 | RF-REP-02 | **Dado** 8 remitos `Recibido`, 1 `Extraviado` y 1 `Dañado`, **cuando** se emite R2, **entonces** la tasa de éxito es 80 % y las incidencias 20 %. |
| CA-REP-05 | RF-REP-02 | **Dado** remitos `Anulado` o abiertos, **cuando** se emite R2, **entonces** no se cuentan en la tasa. |
| CA-REP-06 | RF-REP-03 | **Dado** el libro X con 5 préstamos interbibliotecarios (1 cancelado) y Y con 3, **cuando** se emite R3, **entonces** X aparece primero con 4. |
| CA-REP-07 | RF-REP-03 | **Dado** préstamos locales, **cuando** se emite R3, **entonces** no se incluyen. |
| CA-REP-08 | RF-REP-04 | **Dado** un préstamo vencido hace 4 días, **cuando** se emite R4, **entonces** figura con 4 días de atraso y una multa acumulada de $800. |
| CA-REP-09 | RF-REP-04 | **Dado** un préstamo vencido que se devuelve, **cuando** se emite R4 después, **entonces** deja de figurar como vencido y su multa figura como pendiente o saldada. |
| CA-REP-10 | RF-REP-05 | **Dado** un libro con 2 ejemplares en la sede A (1 disponible, 1 prestado), **cuando** se emite R5, **entonces** A muestra 2 totales, 1 disponible y 1 prestado. |
| CA-REP-11 | RF-REP-06 | **Dado** un préstamo activo y un remito `En tránsito`, **cuando** se emite R6, **entonces** ambos figuran con su estado. |
| CA-REP-12 | RF-REP-08 | **Dado** un bibliotecario, **cuando** intenta emitir R2 o R3, **entonces** se rechaza. |
| CA-REP-13 | RF-REP-08 | **Dado** un bibliotecario de la sede A, **cuando** emite R6, **entonces** ve solo lo que involucra a A. |
| CA-REP-14 | RF-REP-07 | **Dado** un rango con fin anterior al inicio, **cuando** se emite, **entonces** se rechaza. |
| CA-REP-15 | RF-REP-07 | **Dado** filtros sin datos, **cuando** se emite, **entonces** muestra «sin resultados» sin error. |
