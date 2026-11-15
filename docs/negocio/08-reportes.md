# 08. Reportes

El enunciado exige **al menos 4 reportes no triviales**; se documentan los 6 sugeridos. Para cada uno se indica la información necesaria, los roles que acceden y su utilidad.

Los reportes 1 y 2 dependen del **historial de estados del remito**, por eso ese historial se guarda desde el modelo (ver [Remitos](05-remitos.md)).

## Resumen

| # | Reporte | Complejidad | Acceso |
|---|---------|-------------|--------------------|
| R1 | Movimiento de ejemplares entre sedes y tiempo de tránsito | Alta | Administrador; bibliotecario (su sede) |
| R2 | Tasa de envíos exitosos e incidencias | Alta | Administrador |
| R3 | Libros más solicitados en préstamos entre sedes | Media | Administrador |
| R4 | Préstamos vencidos y multas acumuladas | Media | Administrador; bibliotecario (su sede) |
| R5 | Disponibilidad de catálogo por sede | Baja | Todos los roles |
| R6 | Préstamos activos y material en tránsito | Baja | Administrador; bibliotecario (su sede) |

Los socios acceden solo a la consulta de disponibilidad (R5) y a su propia información de préstamos y multas, que no es un reporte de gestión.

**Selección:** implementar R1, R2, R3 y R4 como los cuatro no triviales obligatorios, y R5 y R6 como complemento.

## R1. Movimiento de ejemplares entre sedes

- **Propósito:** conocer el flujo logístico entre sedes y su eficiencia; detectar rutas lentas y sedes que reciben o envían más material.
- **Contenido:** por par sede origen → sede destino: cantidad de envíos, cantidad de ejemplares recibidos y **tiempo promedio de tránsito**.
- **Filtros:** rango de fechas, sede origen, sede destino, motivo (ida/retorno).
- **Datos necesarios:** remitos (origen, destino, motivo), detalle (cantidad de ejemplares) y el historial de estados (fecha de `Despachado` y de `Recibido`). Tiempo de tránsito = fecha de recepción − fecha de despacho, sobre remitos `Recibido`.
- **Regla:** solo cuentan remitos finalizados en `Recibido` (con o sin incidencias) para el promedio. Los ejemplares faltantes no cuentan como movidos.

## R2. Tasa de envíos exitosos e incidencias

- **Propósito:** medir la calidad del servicio logístico y detectar rutas con problemas.
- **Contenido:** total de envíos, % `Recibido` sin incidencia, % `Extraviado`, `Dañado`, `Destruido` e `Incompleto` (recibido con faltantes); detalle por sede origen y por sede destino.
- **Filtros:** rango de fechas, sede.
- **Datos necesarios:** estado final del remito, historial de estados, resultado de la revisión de recepción.
- **Regla:** tasa de éxito = remitos `Recibido` ÷ remitos con estado final. Se excluyen los `Anulado` y los que siguen abiertos.

## R3. Libros más solicitados en préstamos entre sedes

- **Propósito:** decidir dónde conviene reforzar ejemplares y detectar demanda no cubierta localmente.
- **Contenido:** ranking de libros por cantidad de préstamos interbibliotecarios, con sede origen y destino más frecuentes.
- **Filtros:** rango de fechas, categoría, sede (como origen o destino del préstamo).
- **Datos necesarios:** préstamos de tipo `Interbibliotecario`, ejemplar y libro asociados, sedes.
- **Regla:** cuentan los préstamos no cancelados.

## R4. Préstamos vencidos y multas acumuladas

- **Propósito:** controlar la morosidad y el monto adeudado.
- **Contenido:** préstamos vencidos con socio, libro, sede, días de atraso y multa acumulada hasta la fecha; total adeudado; multas pendientes de devoluciones ya registradas.
- **Filtros:** sede, socio, rango de atraso; también el estado de la multa y el período (fecha de generación de la multa).
- **Datos necesarios:** préstamos, fechas de vencimiento y devolución, parámetro de multa por día, multas generadas y su estado.
- **Regla:** la multa de un préstamo vencido no devuelto se calcula al momento de la consulta.
- **Regla:** la sede y el socio definen el alcance; la sede interviene como origen (dueña del ejemplar) o destino (donde lo retiró el socio), igual que en R6. Los totales (vencidos, acumulado, multas pendientes, total adeudado) son la deuda real del alcance: el estado de la multa, el período y el rango de atraso solo acotan las listas.

## R5. Disponibilidad de catálogo por sede

- **Propósito:** saber qué hay en cada sede y qué se puede pedir.
- **Contenido:** por libro y sede: ejemplares totales, disponibles, prestados, reservados y en tránsito.
- **Filtros:** sede, título, autor, categoría.
- **Datos necesarios:** libros, ejemplares con sede y estado de disponibilidad.
- **Regla:** se cuenta igual que en la ficha del libro. «Reservados» son los ejemplares retenidos para una reserva; los apartados para un préstamo solicitado o un retorno y los que están en revisión van en «otros».

## R6. Préstamos activos y material en tránsito

- **Propósito:** ver el estado operativo del momento.
- **Contenido:** préstamos activos y su vencimiento; remitos abiertos con su estado actual, origen, destino y antigüedad.
- **Filtros:** sede, estado (al día o vencido, según la fecha de vencimiento, igual que R4), tipo de préstamo y estado del remito.
- **Datos necesarios:** préstamos, remitos y su estado actual.

## Matriz de datos

| Dato | R1 | R2 | R3 | R4 | R5 | R6 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|
| Remito y su detalle | ✔ | ✔ | | | | ✔ |
| Historial de estados del remito | ✔ | ✔ | | | | |
| Préstamo (tipo, fechas, estado) | | | ✔ | ✔ | | ✔ |
| Ejemplar y libro | | | ✔ | ✔ | ✔ | ✔ |
| Multas y parámetro de multa | | | | ✔ | | |
| Sedes | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
