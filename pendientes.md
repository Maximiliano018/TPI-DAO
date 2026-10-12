# Pendientes y dudas abiertas

Solo lo que todavía no está definido y condiciona [ARCHITECTURE.md](ARCHITECTURE.md) o [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md). Cada ítem indica la **propuesta actual**, que es la que usan hoy los documentos. Las decisiones ya tomadas están en el [registro de decisiones de ARCHITECTURE.md](ARCHITECTURE.md#10-registro-de-decisiones).

## Para consultar con la cátedra

| ID | Duda | Propuesta actual |
|---|---|---|
| PENDIENTE-1 | **¿Es necesario implementar un lote de ejemplares por remito** (remito con líneas de detalle)? La consigna dice "asignando un remito" para "ejemplares" y admite ambas lecturas | **v1: un remito por ejemplar y por viaje.** Si exigen lotes, evolucionar a `DetalleRemito`: la revisión de recepción pasa a ser por línea y hay que definir el estado parcial (p. ej. 2 de 3 llegaron bien). Encapsular desde ahora el acceso al ejemplar del remito |
| PENDIENTE-7 | ¿Mantener "despachado" y "en tránsito" como estados separados del remito? La consigna habla de "empaquetar, despachar y recibir" y dice que evaluará críticamente el ciclo del remito | Un único estado `EN_TRANSITO` (despachar es la acción): no hay un transportista externo que justifique dos estados |
| PENDIENTE-29 | ¿El "movimiento de ejemplares entre sedes" (reporte sugerido) se refiere solo a préstamos o también a **traslados** sin socio (redistribución de stock, desvío a la sede de una reserva)? | Solo préstamos; traslados fuera de alcance. `Remito.prestamo_id` es opcional para habilitarlos. Si se incluyen, definir si cambia la sede propietaria, quién los autoriza y si puede trasladarse un ejemplar reservado |
| PENDIENTE-38 | ¿La solicitud de un préstamo inter-sedes requiere **aprobación de la sede origen**, o alcanza con que el ejemplar esté disponible? | Sin aprobación: si el ejemplar está disponible, el préstamo se registra y el remito de ida se genera en el acto. Si se exige aprobación, agregar un estado `SOLICITADO` previo a `EN_ENVIO` y las transiciones de aprobar y rechazar |
| PENDIENTE-19 | ¿Hay requisitos de despliegue o de entrega (Docker, hosting)? | Ejecución local; `docker compose` opcional |
| PENDIENTE-20 | ¿Exigen tests, diagramas UML o documentación específica en la entrega? | Tests de dominio + diagramas Mermaid en ARCHITECTURE.md |

Conviene hacer las consultas 1, 7, 29 y 38 juntas: todas afectan al ciclo de vida del remito y del préstamo.

## Para decidir en el equipo

| ID | Duda | Propuesta actual |
|---|---|---|
| PENDIENTE-3 | **¿El socio debe poder ingresar al sistema** para consultar disponibilidad, ver sus préstamos y crear reservas? | No en esta versión: solo personal. Si se habilita, `Usuario` tendría `socio_id` opcional y un rol `SOCIO`, y habría que sumar un portal y reglas de acceso a los datos propios |

## Design system

| ID | Duda | Propuesta actual |
|---|---|---|
| PENDIENTE-D1 | ¿Hay identidad visual previa (logo, colores institucionales)? | Paleta propia azul petróleo |
| PENDIENTE-D2 | Validar contraste AA de todos los pares de colores (claro y oscuro) | Valores propuestos sin medir |
| PENDIENTE-D3 | Librería de íconos | Lucide |
| PENDIENTE-D4 | Fuentes: ¿Google Fonts o autoalojadas (offline)? | Google Fonts con fallback del sistema |
| PENDIENTE-D5 | Idioma y formato de fechas y moneda en la UI | `es-AR`, fechas `dd/mm/aaaa`, moneda ARS |
| PENDIENTE-D6 | ¿Dispositivos objetivo? (¿uso en tablet o móvil en mostrador?) | Escritorio primero, responsive básico |
| PENDIENTE-D7 | ¿Se necesita documentar los componentes (Storybook) o basta con DESIGN-SYSTEM.md? | Solo DESIGN-SYSTEM.md |
