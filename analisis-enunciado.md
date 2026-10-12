# Análisis del dominio: Sistema de Préstamos Interbibliotecarios

> Análisis inicial del enunciado. Las decisiones de diseño vigentes están en [ARCHITECTURE.md](ARCHITECTURE.md) y las dudas abiertas en [pendientes.md](pendientes.md).

## Objetivo

Reemplazar la gestión manual de una **red de bibliotecas públicas** por un sistema que controle préstamos, devoluciones y disponibilidad. El rasgo distintivo es el **préstamo interbibliotecario**. Un socio puede pedir un ejemplar que está físicamente en otra sede, y el sistema debe gestionar su traslado logístico con trazabilidad.

En esta versión lo usa solo el personal (operación, logística y administración); los socios consultan, piden préstamos y reservan a través de él. Si los socios deben tener acceso propio está pendiente (PENDIENTE-3).

## Alcance

**Dentro del alcance (obligatorio)**

| # | Proceso | Qué implica |
|---|---------|-------------|
| 1 | ABM de sedes | Dirección, contacto, horarios, estado activo/baja |
| 2 | ABM de socios | Incluye estado habilitado/inhabilitado |
| 3 | Catálogo y ejemplares | Libro (título) ≠ ejemplar (copia física); cada ejemplar pertenece a una sede |
| 4 | Solicitud de préstamo | Local o interbibliotecario (sede origen y destino) |
| 5 | Logística de envío | Empaquetar, despachar y recibir, con remito y estados |
| 6 | Consulta de disponibilidad | Por libro y por sede |
| 7 | Reservas | Cola o espera sobre material no disponible |
| 8 | Devoluciones | Registro del estado físico del material |

**Opcional (extensiones):** se implementan **notificaciones** (simuladas) y **revisión de estado de recepción** (conforme, dañado, destruido, extraviado). El inventario usa códigos de texto únicos, sin códigos de barra. Historial de lecturas y recomendaciones quedan fuera de esta versión.

**Fuera de alcance (implícito):** adquisiciones, catalogación bibliográfica avanzada (MARC), pagos de multas y logística externa real.

## Entidades del dominio

El modelo completo, con atributos, relaciones y diagramas, está en [ARCHITECTURE.md §4](ARCHITECTURE.md#4-modelo-de-dominio) y el esquema de la base en [§5](ARCHITECTURE.md#5-base-de-datos).

- **Sede** y **HorarioSede**: código, nombre, dirección, contacto, horarios por día (admite horario cortado), activa/baja.
- **Socio**: datos personales, número de socio, DNI, habilitación manual con motivo, baja lógica.
- **Libro**, **Autor**, **Categoria**: obra del catálogo de la red, identificada por ISBN-13.
- **Ejemplar**: código de inventario, libro, sede propietaria, situación (`estado`), condición física, si es prestable o de consulta en sala, motivo de baja.
- **Prestamo**: socio, ejemplar, sede origen y destino, fechas de solicitud, límite de retiro, inicio y vencimiento, estado, motivo de cancelación.
- **Devolucion**: préstamo, fecha, condición física del material, observación.
- **Multa**: préstamo, días de atraso, monto (solo por atraso).
- **Reserva**: socio, libro, sede de retiro, ejemplar asignado, fecha límite, estado.
- **Remito** y **MovimientoRemito**: traslado de un ejemplar en un viaje (ida o vuelta), con revisión de recepción e historial inmutable de estados.
- **Notificacion**: avisos simulados a los socios.
- **Usuario** y **Parametro**: personal del sistema (con rol y sede) y configuración editable por el ADMIN.

## Conceptos clave y decisiones de modelado

1. **Libro vs. Ejemplar.** Es el punto central del dominio. La disponibilidad, la sede y la condición física son del *ejemplar*, mientras que el catálogo es del *libro*. El requisito "evitar duplicados" se aplica a los tres niveles: socio (DNI y nº de socio), libro (ISBN) y ejemplar (código de inventario).
2. **Sede origen vs. destino.** Origen es la sede propietaria del ejemplar. Destino es donde el socio lo retira y lo devuelve. En un préstamo local son la misma.
3. **Ciclo de vida del remito.** `GENERADO → EMPAQUETADO → EN_TRANSITO → RECIBIDO`, con `EXTRAVIADO` y `CANCELADO`. Al recibir se registra la revisión (`CONFORME`, `DANADO`, `DESTRUIDO`). Hay **un remito por ejemplar y por viaje**: el de ida y el de vuelta son independientes. Sin retrocesos; cada cambio queda en `MovimientoRemito`.
4. **Ciclo de vida del préstamo.** Local: se crea `ACTIVO`. Inter-sedes: `EN_ENVIO → LISTO_PARA_RETIRO → ACTIVO → DEVUELTO`, con `CANCELADO`. El vencimiento corre desde la entrega al socio, y `VENCIDO` se calcula, no se guarda.

Las máquinas de estado completas (remito, préstamo, ejemplar y reserva) y la matriz de efectos de cada evento están en [ARCHITECTURE.md §4.4 y §4.5](ARCHITECTURE.md#44-máquinas-de-estado).

## Reglas de negocio (validaciones obligatorias)

| Regla | Dónde se valida |
|---|---|
| No prestar ejemplares no disponibles | Estado del ejemplar al registrar el préstamo, con respaldo de un índice único en la base |
| No prestar a socios inhabilitados | `Socio.puede_pedir_prestamo()`, al registrar y al entregar |
| Controlar fechas de vencimiento | Vencimiento calculado desde la entrega; multa por atraso al devolver |
| Trazabilidad del remito | Patrón State en `Remito` + historial `MovimientoRemito` |
| Evitar duplicados | Validación en servicios + `UNIQUE` en la base |
| El ejemplar debe pertenecer a la sede origen | Al crear el préstamo (`PrestamoFactory`) |
| Sedes de baja bloqueadas | En préstamos, reservas y envíos; además, no se puede dar de baja una sede con actividad abierta |

Las reglas que el enunciado no fijaba (plazos, máximo de préstamos, multas, reservas, baja de sedes) quedaron definidas en [ARCHITECTURE.md §4.3](ARCHITECTURE.md#43-decisiones-de-modelado) y sus valores iniciales en [§5.5](ARCHITECTURE.md#55-parámetros-del-sistema).

## Reportes

Hay que implementar **al menos 4 no triviales**. Se implementan:

1. Movimiento entre sedes: envíos por origen/destino y **tiempo promedio de tránsito**.
2. Tasa de envíos exitosos e incidencias.
3. Libros más solicitados en préstamos inter-sedes.
4. Vencidos y multas acumuladas.

Además, disponibilidad de catálogo por sede y préstamos activos con material en tránsito, que alimentan el tablero. El cálculo de cada uno está en [ARCHITECTURE.md §8](ARCHITECTURE.md#8-reportes-mínimo-exigido-4-no-triviales).

## Requisitos no funcionales y restricciones del trabajo

- Al menos **2 patrones de diseño**. Se aplican **State** (ciclo de vida del remito), **Strategy** (cálculo de multas), **Factory** (préstamo local vs. inter-sedes), **Observer** (notificaciones) y **Repository + Unit of Work** (persistencia).
- Cumplir todos los procesos obligatorios y las validaciones.
- Como la materia es de objetos, el diseño es orientado a objetos, con la lógica en el dominio y no en la interfaz.

## Ambigüedades del enunciado

| # | Pregunta | Resolución |
|---|---|---|
| 1 | ¿El remito es por préstamo o puede agrupar varios ejemplares? | Un remito por ejemplar y por viaje. Se valida con la cátedra si hace falta agrupar (PENDIENTE-1) |
| 2 | ¿La vuelta lleva remito propio? | Sí: remito de ida y de vuelta independientes |
| 3 | ¿Quién usa el sistema? ¿Hay roles y autenticación? | Solo el personal, con roles ADMIN, BIBLIOTECARIO y LOGISTICA y autenticación con JWT. El acceso de los socios queda abierto (PENDIENTE-3) |
| 4 | ¿GUI, API o consola? ¿Qué tecnología? | API REST con FastAPI y SPA con React; base SQLite con SQLAlchemy y Alembic |
| 5 | ¿La reserva es sobre un libro o un ejemplar? | Sobre el libro, en la sede de retiro, con cola FIFO |
| 6 | ¿Qué pasa con un ejemplar dañado, extraviado o destruido? | Extraviado o destruido pasa a baja; dañado queda en revisión en su sede. El socio no recibe multa por daño ni por incidencias del envío |

Las dudas que siguen abiertas están en [pendientes.md](pendientes.md).
