# 05. Remitos y envíos entre sedes

Origen: [negocio/05-remitos.md](../negocio/05-remitos.md). Proceso obligatorio 5. El ciclo de vida del remito se evalúa críticamente, por lo que sus transiciones están completas.

## Ciclo de vida de referencia

```
Generado ──▶ Empaquetado ──▶ Despachado ──▶ En tránsito ──▶ Recibido
   │              │              │               │
   └──▶ Anulado   └──▶ Anulado   │               ├──▶ Extraviado
                                 └──▶ Extraviado └──▶ Dañado / Destruido
```

Estados finales: `Recibido`, `Extraviado`, `Dañado`, `Destruido`, `Anulado`.

## Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-REM-01 | El sistema debe generar remitos con número único, sede origen, sede destino, motivo (`Envío por préstamo`, `Retorno por devolución`, `Traslado`) y estado `Generado`. | Obligatorio |
| RF-REM-02 | Un remito debe tener un detalle con una línea por ejemplar. Todos los ejemplares comparten origen y destino. | Obligatorio |
| RF-REM-03 | Cada línea de un remito por préstamo o retorno debe asociarse a su préstamo; los remitos de traslado no tienen préstamo. | Obligatorio |
| RF-REM-04 | La ida y la vuelta de un préstamo interbibliotecario deben tener remitos distintos. | Obligatorio |
| RF-REM-05 | El sistema debe permitir las transiciones válidas del ciclo de vida y rechazar saltos, retrocesos y salidas de un estado final. | Obligatorio |
| RF-REM-06 | Cada transición debe registrar un movimiento con estado anterior, estado nuevo, fecha y hora, responsable y observación. | Obligatorio |
| RF-REM-07 | Empaquetar, despachar y anular solo pueden hacerlo bibliotecarios de la sede origen; recibir y registrar incidencias, la sede destino. | Obligatorio |
| RF-REM-08 | Al despachar, los ejemplares del remito deben pasar a `En tránsito`. | Obligatorio |
| RF-REM-09 | Al recibir, el destino debe verificar cada línea y registrar su estado físico; los ejemplares quedan `Disponible` o `Prestado` en destino según el motivo. | Obligatorio |
| RF-REM-10 | El sistema debe rechazar remitos con una sede en `Baja` como origen o destino, ejemplares que no pertenezcan o no estén en la sede origen, o ejemplares ya incluidos en otro remito abierto. | Obligatorio |
| RF-REM-11 | El sistema debe permitir anular un remito solo antes del despacho, liberando los ejemplares. | Obligatorio |
| RF-REM-12 | El sistema debe permitir marcar `Extraviado` un remito despachado cuando venció el plazo máximo de tránsito (7 días). | Obligatorio |
| RF-REM-13 | El sistema debe registrar la revisión de recepción: ejemplar dañado o destruido, con efecto sobre el ejemplar (revisión o baja). | Opcional |
| RF-REM-14 | El sistema debe permitir consultar un remito y su historial completo de movimientos, con la visibilidad que corresponda a cada rol. | Obligatorio |

## Casos de uso

### CU-REM-01. Generar un remito de envío

- **Actor:** Bibliotecario de la sede origen.
- **Precondición:** hay préstamos interbibliotecarios en `Solicitado` con el mismo origen y destino, o un traslado a realizar.
- **Flujo normal:**
  1. Selecciona uno o más ejemplares con igual origen y destino.
  2. El sistema valida los ejemplares y las sedes.
  3. Crea el remito `Generado` con su número y su detalle, y registra el primer movimiento.
  4. Los préstamos asociados pasan a `En envío`.
- **Flujos alternativos:**
  - **A1 (paso 2): destinos distintos.** El sistema propone un remito por cada destino.
  - **A2 (paso 2): ejemplar ya en un remito abierto.** Rechaza ese ejemplar.
  - **A3 (paso 2): sede origen o destino en `Baja`.** Rechaza.
  - **A4 (paso 2): ejemplar que no está físicamente en la sede origen.** Rechaza.

### CU-REM-02. Empaquetar y despachar

- **Actor:** Bibliotecario de la sede origen.
- **Flujo normal:**
  1. Abre un remito `Generado` y confirma el empaquetado: pasa a `Empaquetado`.
  2. Confirma el despacho: pasa a `Despachado` y los ejemplares a `En tránsito`.
  3. El remito pasa a `En tránsito` (automático o manual).
- **Flujos alternativos:**
  - **A1:** intenta despachar un remito `Generado` sin empaquetar; rechaza (sin saltos).
  - **A2:** bibliotecario de otra sede; rechaza.

### CU-REM-03. Anular un remito

- **Actor:** Bibliotecario de la sede origen.
- **Flujo normal:** anula un remito `Generado` o `Empaquetado` con motivo; pasa a `Anulado`, los ejemplares quedan `Disponible` y los préstamos asociados se cancelan.
- **Flujo alternativo A1:** el remito ya fue despachado; rechaza.

### CU-REM-04. Recibir un remito

- **Actor:** Bibliotecario de la sede destino.
- **Flujo normal:**
  1. Abre el remito `En tránsito` dirigido a su sede.
  2. Verifica cada línea y registra su estado físico.
  3. Confirma la recepción: pasa a `Recibido`.
  4. Los ejemplares quedan `Prestado` (entrega al socio, si el motivo es préstamo), `Disponible` (retorno o traslado) y, en traslados, cambian de sede propietaria.
- **Flujos alternativos:**
  - **A1 (paso 2): una línea llega dañada.** Se registra la incidencia (CU-REM-05).
  - **A2 (paso 1): sede distinta del destino.** Rechaza.
  - **A3 (paso 1): remito en `Despachado` sin pasar a `En tránsito`.** Se permite recibir; el sistema completa el estado intermedio y lo registra.
  - **A4 (paso 3): la sede destino pasó a `Baja` durante el tránsito.** No ocurre: la baja se bloqueó por el remito abierto.

### CU-REM-05. Registrar una incidencia de recepción

- **Actor:** Bibliotecario de la sede destino.
- **Flujo normal:** al verificar, marca el remito como `Dañado` o `Destruido` con observaciones; el ejemplar queda en revisión (dañado) o `Baja` (destruido) y el préstamo asociado pasa a `Cancelado`.
- **Flujos alternativos:**
  - **A1:** daño parcial en un remito de varios ejemplares; se registra por línea y se informa en el remito.
  - **A2:** remito sin observaciones; rechaza (la incidencia exige descripción).

### CU-REM-06. Marcar un remito como extraviado

- **Actor:** Bibliotecario de la sede origen o destino, Administrador.
- **Flujo normal:** sobre un remito despachado cuyo plazo máximo de tránsito venció, marca `Extraviado` con observación; los ejemplares pasan a `Baja` con incidencia y los préstamos a `Cancelado`.
- **Flujos alternativos:**
  - **A1:** el plazo todavía no venció; rechaza.
  - **A2:** el remito llega luego de marcarse; no se revierte. Se registra aparte como hallazgo y se corrige por un ajuste administrativo.

### CU-REM-07. Consultar un remito

- **Actores:** Bibliotecario (sedes involucradas), Administrador, Socio (remito de su préstamo).
- **Flujo normal:** busca por número, préstamo o ejemplar; ve estado actual, detalle y movimientos ordenados en el tiempo.
- **Flujo alternativo A1:** sede ajena al remito; rechaza.

## Criterios de aceptación

| ID | RF | Criterio |
|----|----|----------|
| CA-REM-01 | RF-REM-01 | **Dado** dos remitos creados, **cuando** se comparan, **entonces** tienen números distintos. |
| CA-REM-02 | RF-REM-02 | **Dado** un envío con 3 ejemplares a la misma sede destino, **cuando** se genera, **entonces** hay un único remito con 3 líneas. |
| CA-REM-03 | RF-REM-04 | **Dado** un préstamo interbibliotecario devuelto, **cuando** se genera el retorno, **entonces** es un remito distinto del de ida. |
| CA-REM-04 | RF-REM-05 | **Dado** un remito `Generado`, **cuando** se intenta despachar sin empaquetar, **entonces** se rechaza. |
| CA-REM-05 | RF-REM-05 | **Dado** un remito `Recibido`, **cuando** se intenta pasarlo a otro estado, **entonces** se rechaza. |
| CA-REM-06 | RF-REM-05 | **Dado** un remito `En tránsito`, **cuando** se intenta volver a `Empaquetado`, **entonces** se rechaza. |
| CA-REM-07 | RF-REM-06 | **Dado** un remito que recorre todo el ciclo, **cuando** se consulta, **entonces** muestra un movimiento por cada transición, en orden, con fecha, hora y responsable. |
| CA-REM-08 | RF-REM-07 | **Dado** un bibliotecario de la sede destino, **cuando** intenta despachar, **entonces** se rechaza. |
| CA-REM-09 | RF-REM-08 | **Dado** un remito que se despacha, **cuando** pasa a `Despachado`, **entonces** sus ejemplares quedan `En tránsito`. |
| CA-REM-10 | RF-REM-09 | **Dado** un remito de préstamo recibido, **cuando** se entrega al socio, **entonces** el ejemplar queda `Prestado` y el préstamo `Activo`. |
| CA-REM-11 | RF-REM-10 | **Dado** una sede destino en `Baja`, **cuando** se genera un remito hacia ella, **entonces** se rechaza. |
| CA-REM-12 | RF-REM-10 | **Dado** un ejemplar de la sede C, **cuando** se incluye en un remito con origen A, **entonces** se rechaza. |
| CA-REM-13 | RF-REM-10 | **Dado** un ejemplar en un remito abierto, **cuando** se lo incluye en otro, **entonces** se rechaza. |
| CA-REM-14 | RF-REM-11 | **Dado** un remito `Despachado`, **cuando** se intenta anular, **entonces** se rechaza. |
| CA-REM-15 | RF-REM-11 | **Dado** un remito `Empaquetado`, **cuando** se anula, **entonces** pasa a `Anulado` y los ejemplares quedan `Disponible`. |
| CA-REM-16 | RF-REM-12 | **Dado** un remito despachado hace 3 días, **cuando** se intenta marcar `Extraviado`, **entonces** se rechaza. |
| CA-REM-17 | RF-REM-12 | **Dado** un remito despachado hace 8 días, **cuando** se marca `Extraviado`, **entonces** los ejemplares pasan a `Baja` con incidencia. |
| CA-REM-18 | RF-REM-13 | **Dado** un ejemplar recibido destruido, **cuando** se registra, **entonces** el ejemplar queda en `Baja` y el préstamo `Cancelado`. |
| CA-REM-19 | RF-REM-09 | **Dado** un traslado recibido, **cuando** se cierra, **entonces** el ejemplar cambia de sede propietaria. |
