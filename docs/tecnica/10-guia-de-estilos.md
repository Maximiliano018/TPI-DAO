# 10. Guía de estilos (design system base)

Design system propio y liviano para el frontend, definido por Maxi como «crear uno base». Es **reemplazable**: todo el aspecto sale de variables CSS (tokens), así que adoptar otro design system implica cambiar los valores de `styles/tokens.css` y revisar los componentes base, sin tocar las pantallas.

## Principios

1. **Claridad ante todo.** Es un sistema de gestión: la información y el estado van antes que la decoración.
2. **El estado no depende solo del color.** Cada estado lleva texto, y el color refuerza.
3. **Accesible por defecto.** Contraste AA, foco visible, objetivos táctiles amplios, teclado completo.
4. **Consistente.** Un componente, una forma de usarlo; los tokens son la única fuente de valores.
5. **Sobrio.** Pocos colores, pocas sombras, tipografía legible.

## Tokens

Se definen como variables CSS en `:root`. Los pares de color que siguen se verificaron con la fórmula de contraste de WCAG 2.1; la columna indica la relación obtenida (AA exige 4,5:1 para texto normal y 3:1 para componentes gráficos).

### Color

| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary-700` | `#1D4ED8` | Acciones principales, enlaces |
| `--color-primary-800` | `#1E40AF` | Estado «presionado» y enlaces visitados |
| `--color-primary-100` | `#DBEAFE` | Fondos de selección y énfasis suave |
| `--color-text` | `#111827` | Texto principal |
| `--color-text-muted` | `#4B5563` | Texto secundario |
| `--color-text-subtle` | `#6B7280` | Marcadores de posición, texto deshabilitado |
| `--color-bg` | `#F9FAFB` | Fondo de la aplicación |
| `--color-surface` | `#FFFFFF` | Tarjetas, tablas, formularios |
| `--color-border` | `#D1D5DB` | Separadores y bordes decorativos |
| `--color-border-strong` | `#6B7280` | Bordes de campos y controles (4,8:1 sobre blanco, supera el 3:1 exigido a los componentes) |
| `--color-success-700` / `-100` / `-800` | `#15803D` / `#DCFCE7` / `#166534` | Éxito |
| `--color-warning-700` / `-100` / `-800` | `#B45309` / `#FEF3C7` / `#92400E` | Atención |
| `--color-danger-700` / `-100` / `-800` | `#B91C1C` / `#FEE2E2` / `#991B1B` | Error y acciones destructivas |
| `--color-info-700` / `-100` / `-800` | `#0369A1` / `#E0F2FE` / `#075985` | Información |
| `--color-neutral-100` / `-700` | `#F3F4F6` / `#374151` | Estados neutros o finales |
| `--color-accent-100` / `-800` | `#F3E8FF` / `#6B21A8` | Estados en proceso logístico |

Contrastes verificados:

| Combinación | Relación |
|-------------|----------|
| Texto principal sobre superficie blanca | 17,7:1 |
| Texto principal sobre fondo de la aplicación | 17,0:1 |
| Texto secundario sobre blanco | 7,6:1 |
| Texto sutil sobre blanco | 4,8:1 |
| Blanco sobre primario 700 | 6,7:1 |
| Blanco sobre éxito 700 | 5,0:1 |
| Blanco sobre atención 700 | 5,0:1 |
| Blanco sobre peligro 700 | 6,5:1 |
| Blanco sobre información 700 | 5,9:1 |
| Etiqueta de éxito (800 sobre 100) | 6,5:1 |
| Etiqueta de atención | 6,4:1 |
| Etiqueta de peligro | 6,8:1 |
| Etiqueta de información | 6,6:1 |
| Etiqueta neutra | 9,4:1 |
| Etiqueta primaria | 7,2:1 |
| Etiqueta de proceso (acento) | 7,4:1 |

Todas cumplen AA. Los campos usan `--color-border-strong`; `--color-border` queda solo para separadores que no son necesarios para identificar un control. En foco y en error el borde se engrosa y cambia de color.

### Tipografía

| Token | Valor |
|-------|-------|
| `--font-sans` | `Inter`, `system-ui`, `sans-serif` |
| `--font-mono` | `ui-monospace`, `monospace` (códigos de inventario, números de remito) |
| Escala (`--text-xs` … `--text-3xl`) | 12, 14, 16, 18, 20, 24 y 30 px |
| Cuerpo | 16 px, interlineado 1,5 |
| Pesos | 400 (texto), 500 (etiquetas), 600 (títulos) |

Los números de remito, préstamo y código de inventario se muestran en tipografía monoespaciada para leerlos sin ambigüedad.

### Espaciado, forma y elevación

| Token | Valor |
|-------|-------|
| Escala de espacio | Múltiplos de 4 px: 4, 8, 12, 16, 24, 32, 48 |
| `--radius-sm` / `--radius-md` / `--radius-lg` | 4 / 8 / 12 px |
| `--shadow-sm` | `0 1px 2px rgba(17,24,39,.08)` |
| `--shadow-md` | `0 4px 12px rgba(17,24,39,.12)` (menús y modales) |
| Puntos de corte | 640, 768, 1024 y 1280 px |
| Ancho de contenido | Máximo 1200 px |

### Foco e interacción

- Anillo de foco: 2 px de `--color-primary-700` con 2 px de separación, visible sobre cualquier fondo. Nunca se elimina el contorno sin reemplazarlo.
- Altura mínima de controles: 40 px (el criterio AA de objetivos táctiles pide 24 px).
- Estados de cada control: normal, hover, foco, presionado, deshabilitado y, si corresponde, error.
- Se respeta `prefers-reduced-motion`: las transiciones duran 150 ms y se desactivan si el usuario lo pide.

## Componentes base

| Componente | Variantes y notas |
|------------|-------------------|
| `Button` | Primario, secundario, peligro y enlace; tamaños medio y chico; estado «cargando» que deshabilita |
| `Input`, `Select`, `Textarea`, `Checkbox` | Siempre con `FormField` (etiqueta, ayuda y error asociados por `aria-describedby`) |
| `Table` | Cabecera fija opcional, orden por columna, acciones por fila; se convierte en tarjetas bajo 768 px |
| `Pagination` | Anterior/siguiente, tamaño de página, total |
| `Badge` | Etiqueta de estado con color y texto (ver mapa de estados) |
| `Modal` y `ConfirmDialog` | Atrapa el foco, Escape cierra; el diálogo de confirmación describe el efecto |
| `Alert` | Éxito, atención, error, información; con rol `alert` o `status` |
| `Toast` | Resultado de una acción; desaparece solo, sin ocultar información necesaria |
| `Timeline` | Línea de tiempo vertical para los movimientos de remito y préstamo |
| `EmptyState` / `Spinner` / `Skeleton` | Estados vacío y de carga |
| `PageHeader` | Título, descripción y acciones de la pantalla |
| `Tabs`, `Card`, `Breadcrumb` | Estructura de pantallas de detalle |

## Mapa de estados a etiquetas

Una sola tabla de correspondencia (`utils/estados.js`) define cómo se muestra cada estado en toda la aplicación:

| Entidad | Estado | Tono | Texto |
|---------|--------|------|-------|
| Sede | `ACTIVA` | éxito | Activa |
| | `BAJA` | neutro | Baja |
| Socio | `HABILITADO` | éxito | Habilitado |
| | `INHABILITADO` | peligro | Inhabilitado |
| Ejemplar | `DISPONIBLE` | éxito | Disponible |
| | `RESERVADO`, `APARTADO` | información | Reservado, Apartado |
| | `PRESTADO` | primario | Prestado |
| | `EN_TRANSITO` | proceso | En tránsito |
| | `EN_REVISION` | atención | En revisión |
| | `BAJA` | neutro | Baja |
| Préstamo | `SOLICITADO` | información | Solicitado |
| | `EN_ENVIO` | proceso | En envío |
| | `ACTIVO` | primario | Activo |
| | `VENCIDO` | peligro | Vencido |
| | `DEVUELTO` | éxito | Devuelto |
| | `CANCELADO` | neutro | Cancelado |
| Remito | `GENERADO`, `EMPAQUETADO` | información | Generado, Empaquetado |
| | `DESPACHADO`, `EN_TRANSITO` | proceso | Despachado, En tránsito |
| | `RECIBIDO` | éxito | Recibido |
| | `EXTRAVIADO`, `DESTRUIDO` | peligro | Extraviado, Destruido |
| | `DANADO` | atención | Dañado |
| | `ANULADO` | neutro | Anulado |
| Reserva | `PENDIENTE` | información | Pendiente |
| | `DISPONIBLE_PARA_RETIRO` | atención | Para retirar |
| | `CUMPLIDA` | éxito | Cumplida |
| | `VENCIDA`, `CANCELADA` | neutro | Vencida, Cancelada |
| Multa | `PENDIENTE` | peligro | Pendiente |
| | `SALDADA` | éxito | Saldada |

## Voz y contenido

- Español neutro rioplatense, directo y sin tecnicismos: «El socio está inhabilitado por un préstamo vencido», no «Error 409».
- Los mensajes de error dicen **qué pasó y qué hacer**.
- Botones con verbos concretos: «Registrar préstamo», «Despachar remito», no «Aceptar».
- Fechas `dd/mm/aaaa`, hora `HH:mm`, montos con el símbolo `$` y separadores locales.

## Cómo reemplazarlo por otro design system

1. Mapear los tokens de esta guía a los del otro sistema en `styles/tokens.css`.
2. Reemplazar internamente los componentes de `components/` conservando su interfaz (las pantallas no cambian).
3. Mantener `utils/estados.js` y volver a verificar los contrastes con la tabla de arriba.

Si el equipo ya tiene un design system (por ejemplo, en Figma), pasar el enlace o los tokens y esta guía se actualiza para reflejarlo.
