# Análisis del dominio: Sistema de Préstamos Interbibliotecarios

## Objetivo

Reemplazar la gestión manual de una **red de bibliotecas públicas** por un sistema que controle préstamos, devoluciones y disponibilidad. El rasgo distintivo es el **préstamo interbibliotecario**. Un socio puede pedir un ejemplar que está físicamente en otra sede, y el sistema debe gestionar su traslado logístico con trazabilidad.

El sistema sirve a dos tipos de usuario: el personal (operación y administración) y los socios (consulta y reservas).

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

**Opcional (extensiones):** notificaciones, historial de lecturas, recomendaciones, inventario por códigos y revisión de recepción (extravío, daño, destrucción).

**Fuera de alcance (implícito):** adquisiciones, catalogación bibliográfica avanzada (MARC), pagos de multas y logística externa real.

## Entidades candidatas

- **Sede**: nombre, dirección, contacto, horarios, activa/baja.
- **Socio**: datos personales, número de socio, estado (habilitado/inhabilitado).
- **Libro** (obra/título): ISBN, título, autor(es), editorial, categoría.
- **Ejemplar**: código de inventario, libro, sede propietaria, estado físico, estado de disponibilidad.
- **Préstamo**: socio, ejemplar, sede origen, sede destino, fecha de solicitud, fecha de vencimiento, fecha de devolución, estado, tipo (local/inter-sedes).
- **Remito**: número, préstamo o ejemplar asociado, sede origen y destino, estado actual y fechas.
- **MovimientoRemito** (historial de estados): remito, estado, fecha/hora, responsable. Es lo que da la trazabilidad.
- **Reserva**: socio, libro o ejemplar, sede, fecha, estado (pendiente, cumplida, cancelada, vencida).
- **Devolución**: préstamo, fecha, estado físico del material.
- **Multa**: préstamo, días de atraso, monto, estado.
- **Personal/Usuario del sistema** (si se modela autenticación).

## Conceptos clave y decisiones de modelado

1. **Libro vs. Ejemplar.** Es el punto central del dominio. La disponibilidad, la sede y el estado físico son del *ejemplar*, mientras que el catálogo es del *libro*. El requisito "evitar duplicados" se aplica a los tres niveles: socio (DNI o nº socio), libro (ISBN) y ejemplar (código único).
2. **Sede origen vs. destino.** Origen es donde está el ejemplar. Destino es donde el socio lo retira y devuelve. En un préstamo local son la misma.
3. **Ciclo de vida del remito.** La consigna dice que se evaluará de forma crítica. Una propuesta inicial:
   `Generado → Empaquetado → Despachado → En tránsito → Recibido` (con ramas `Extraviado`, `Dañado` y `Destruido` para la revisión de recepción).
   Habría que definir las transiciones válidas, que no se pueda retroceder y qué efecto tiene cada estado sobre el préstamo y el ejemplar. El camino de vuelta (devolución a la sede dueña) también necesita remito.
4. **Ciclo de vida del préstamo.** `Solicitado → (En envío) → Activo → Devuelto`, con `Vencido` y `Cancelado`. Está acoplado al del remito y al del ejemplar (`Disponible / Prestado / En tránsito / Reservado / Baja`).

## Reglas de negocio (validaciones obligatorias)

| Regla | Dónde se valida |
|-------|-----------------|
| No prestar ejemplares no disponibles | Al crear el préstamo |
| No prestar a socios inhabilitados | Al crear el préstamo y la reserva |
| Controlar vencimientos | Cálculo de fecha de vencimiento y detección de vencidos, que además alimenta las multas |
| Trazabilidad del remito | Registrar cada cambio de estado con fecha, sin saltos ni retrocesos |
| Evitar duplicados | Unicidad en socios, libros y ejemplares |
| El ejemplar debe pertenecer a la sede origen | Al crear el préstamo |
| Sedes de baja bloqueadas | En préstamos, reservas y envíos, tanto como origen como destino |

**Reglas que hay que definir nosotros** (el enunciado no las fija): plazo de préstamo, máximo de préstamos simultáneos por socio, monto de multa por día, si una multa pendiente inhabilita al socio, la política de reservas (orden FIFO, vigencia) y qué pasa con préstamos o remitos en curso cuando una sede se da de baja.

## Reportes

Hay que implementar **al menos 4 no triviales**. Los sugeridos, de mayor a menor complejidad:

1. Movimiento entre sedes: envíos por origen/destino y **tiempo promedio de tránsito**. Requiere agregación sobre el historial de estados.
2. Tasa de envíos exitosos e incidencias.
3. Libros más solicitados en préstamos inter-sedes.
4. Vencidos y multas acumuladas.
5. Disponibilidad de catálogo por sede.
6. Préstamos activos y material en tránsito.

Los reportes 1 y 2 dependen de guardar bien el historial de estados del remito. Conviene decidirlo desde el modelo.

## Requisitos no funcionales y restricciones del trabajo

- Al menos **2 patrones de diseño**. Encajan naturalmente:
  - **State** para el ciclo de vida de remito, préstamo y ejemplar.
  - **Observer** para notificaciones.
  - **Strategy** para el cálculo de multas o las políticas de plazo.
  - **Factory** para préstamo local vs. inter-sedes.
  - **Repository** para la persistencia.
- Cumplir todos los procesos obligatorios y las validaciones.
- Como la materia es de objetos, el diseño tiene que ser orientado a objetos, con la lógica en el dominio y no en la interfaz.

## Ambigüedades a resolver con la cátedra o el equipo

1. ¿El remito es por préstamo o puede agrupar varios ejemplares en un mismo envío?
2. ¿El viaje de vuelta (devolución a la sede propietaria) lleva remito propio?
3. ¿Quién es el usuario del sistema? ¿Hay roles (bibliotecario, administrador, socio) y autenticación, o solo una consola o GUI para el personal?
4. ¿Se espera una GUI, una API o una consola? ¿Qué tecnología y persistencia se usa?
5. ¿Una reserva es sobre un libro (cualquier ejemplar) o sobre un ejemplar concreto?
6. ¿Qué ocurre con un ejemplar dañado, extraviado o destruido? ¿Se da de baja y se penaliza al socio?

## Próximo paso sugerido

Armar el **modelo de clases (diagrama UML)** y las **máquinas de estado** del remito, el préstamo y el ejemplar. Son el núcleo del dominio y lo que la cátedra va a evaluar.
