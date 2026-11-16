# Análisis del dominio: Sistema de Préstamos Interbibliotecarios

## Objetivo

Reemplazar la gestión manual de una **red de bibliotecas públicas** por un sistema que controle préstamos, devoluciones y disponibilidad. El rasgo distintivo es el **préstamo interbibliotecario**. Un socio puede pedir un ejemplar que está físicamente en otra sede, y el sistema debe gestionar su traslado logístico con trazabilidad.

El sistema sirve a dos tipos de usuario: el personal (operación y administración) y los socios (consulta, pedido de préstamos para sí, reservas y pago de sus multas en línea).

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

**Opcional (extensiones).** Implementadas: **revisión de recepción** (extravío, daño, destrucción y faltantes, con recuperación del ejemplar extraviado), **multas por daño o extravío del ejemplar** (monto fijo configurable, 0 = no se cobra; ver [negocio/07](docs/negocio/07-devoluciones.md#qué-pasa-si-se-devuelve-en-mal-estado)) y **pago de multas** (en el mostrador con su medio de pago, o en línea de forma simulada, con comprobante; ver [técnica/12](docs/tecnica/12-pago-de-multas.md)). Para la presentación se agregaron, fuera del enunciado, el **inicio público** sin sesión (cifras de la red y libros más pedidos, RF-ACC-14) y la **portada del libro** (RF-CAT-16). No implementadas: envío de notificaciones, historial de lecturas como función propia (el socio ve sus préstamos devueltos), recomendaciones e inventario con lectura de códigos (el código de inventario único del ejemplar es parte del catálogo obligatorio).

**Fuera de alcance (implícito):** adquisiciones, catalogación bibliográfica avanzada (MARC), cobros reales con una pasarela de pagos, devoluciones de dinero y logística externa real.

## Entidades candidatas

- **Sede**: nombre, dirección, contacto, horarios, activa/baja.
- **Socio**: datos personales, número de socio, estado (habilitado/inhabilitado).
- **Libro** (obra/título): ISBN, título, autor(es), editorial, categoría.
- **Ejemplar**: código de inventario, libro, sede propietaria, estado físico, estado de disponibilidad.
- **Préstamo**: socio, ejemplar, sede origen, sede destino, fecha de solicitud, fecha de vencimiento, fecha de devolución, estado, tipo (local/inter-sedes).
- **Remito**: número, préstamo o ejemplar asociado, sede origen y destino, estado actual y fechas.
- **MovimientoRemito** (historial de estados): remito, estado, fecha/hora, responsable. Es lo que da la trazabilidad.
- **Reserva**: socio, libro (cualquier ejemplar), sede de retiro, fecha, estado (pendiente, disponible para retiro, cumplida, cancelada, vencida).
- **Devolución**: préstamo, fecha, estado físico del material.
- **Multa**: préstamo, tipo (atraso, daño o extravío), días de atraso (solo la de atraso), monto, estado.
- **Usuario del sistema**: administrador, bibliotecario (con su sede) o socio (con su ficha), con autenticación.
- **Pago**: multa, medio, estado y comprobante (extensión opcional).

## Conceptos clave y decisiones de modelado

1. **Libro vs. Ejemplar.** Es el punto central del dominio. La disponibilidad, la sede y el estado físico son del *ejemplar*, mientras que el catálogo es del *libro*. El requisito "evitar duplicados" se aplica a los tres niveles: socio (DNI o nº socio), libro (ISBN) y ejemplar (código único).
2. **Sede origen vs. destino.** Origen es donde está el ejemplar. Destino es donde el socio lo retira y devuelve. En un préstamo local son la misma.
3. **Ciclo de vida del remito.** La consigna dice que se evaluará de forma crítica. Quedó definido así:
   `Generado → Empaquetado → Despachado → En tránsito → Recibido`, con las ramas `Extraviado`, `Dañado`, `Destruido` e `Incompleto` (recibido con faltantes) y `Anulado` antes del despacho; sin saltos ni retrocesos, y cada transición con su efecto sobre el préstamo y el ejemplar. El camino de vuelta lleva su propio remito de retorno. Ver [negocio/05](docs/negocio/05-remitos.md) y [máquinas de estado](docs/tecnica/03-maquinas-de-estado.md).
4. **Ciclo de vida del préstamo.** `Solicitado → (En envío) → Activo → Devuelto`, con `Vencido` y `Cancelado`. Está acoplado al del remito y al del ejemplar (`Disponible / Apartado / Reservado / Prestado / En tránsito / En revisión / Baja`).

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

**Reglas que el enunciado no fija**, ya definidas: plazos, máximo de préstamos y reservas por socio y montos de multa ([parámetros](docs/negocio/00-contexto-y-actores.md#parámetros-globales-configurables)); una multa pendiente inhabilita al socio ([socios](docs/negocio/02-socios.md)); la cola de reservas es FIFO con vigencia de retiro ([reservas](docs/negocio/06-reservas.md)); una sede no se da de baja mientras tenga actividad pendiente ([sedes](docs/negocio/01-sedes.md)).

## Reportes

Hay que implementar **al menos 4 no triviales**. Los sugeridos, de mayor a menor complejidad:

1. Movimiento entre sedes: envíos por origen/destino y **tiempo promedio de tránsito**. Requiere agregar las fechas de despacho y recepción de los remitos.
2. Tasa de envíos exitosos e incidencias.
3. Libros más solicitados en préstamos inter-sedes.
4. Vencidos y multas acumuladas.
5. Disponibilidad de catálogo por sede.
6. Préstamos activos y material en tránsito.

Los reportes 1 y 2 dependen de guardar bien el historial del remito y sus fechas. Los seis están implementados; ver [negocio/08](docs/negocio/08-reportes.md).

## Requisitos no funcionales y restricciones del trabajo

- Al menos **2 patrones de diseño**. Se implementaron, entre otros:
  - **State** para el ciclo de vida de remito, préstamo, ejemplar y reserva.
  - **Strategy** para el plazo de préstamo y el cálculo de multas.
  - **Factory** para préstamo local vs. inter-sedes.
  - **Repository** y **Unit of Work** para la persistencia.

  Observer se evaluó para notificaciones y se descartó (las notificaciones no se implementaron). Detalle en [patrones de diseño](docs/tecnica/05-patrones-de-diseno.md).
- Cumplir todos los procesos obligatorios y las validaciones.
- Como la materia es de objetos, el diseño tiene que ser orientado a objetos, con la lógica en el dominio y no en la interfaz.

## Ambigüedades (resueltas)

1. ¿El remito es por préstamo o puede agrupar varios ejemplares en un mismo envío? *Decidido: un remito agrupa varios ejemplares con el mismo origen y destino, con una línea por ejemplar ([negocio/05](docs/negocio/05-remitos.md)).*
2. ¿El viaje de vuelta (devolución a la sede propietaria) lleva remito propio? *Decidido: sí, un remito de retorno que genera el sistema ([negocio/05](docs/negocio/05-remitos.md)).*
3. ¿Quién es el usuario del sistema? ¿Hay roles (bibliotecario, administrador, socio) y autenticación, o solo una consola o GUI para el personal? *Decidido: tres roles fijos (administrador, bibliotecario y socio) con usuario, contraseña y permisos por rol ([negocio/00](docs/negocio/00-contexto-y-actores.md)).*
4. ¿Se espera una GUI, una API o una consola? ¿Qué tecnología y persistencia se usa? *Decidido: aplicación web con frontend React, API REST con FastAPI y PostgreSQL ([técnica/00](docs/tecnica/00-stack-y-decisiones.md)).*
5. ¿Una reserva es sobre un libro (cualquier ejemplar) o sobre un ejemplar concreto? *Decidido: sobre el libro; el sistema asigna el primer ejemplar que se libera ([negocio/06](docs/negocio/06-reservas.md)).*
6. ¿Qué ocurre con un ejemplar dañado, extraviado o destruido? ¿Se da de baja y se penaliza al socio? *Decidido: el dañado pasa a revisión y el extraviado a baja, con una incidencia del socio; la multa por daño o extravío es un monto fijo configurable (0 = no se cobra), ver [negocio/07](docs/negocio/07-devoluciones.md#qué-pasa-si-se-devuelve-en-mal-estado).*

## Documentación

El análisis se desarrolla en [`docs/`](docs/README.md): negocio (reglas por proceso), funcional (requerimientos, casos de uso y criterios de aceptación) y técnica (arquitectura, [modelo de clases](docs/tecnica/02-modelo-de-clases.md), [máquinas de estado](docs/tecnica/03-maquinas-de-estado.md), [patrones](docs/tecnica/05-patrones-de-diseno.md) y API). La base de datos está documentada en [`database/`](database/README.md).
