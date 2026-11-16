# 10. Guía de estilos (design system base)

Design system propio y liviano para el frontend. Es **reemplazable**: todo el aspecto sale de variables CSS (tokens), así que adoptar otro design system implica cambiar los valores de `styles/tokens.css` y revisar los componentes base, sin tocar las pantallas.

## Identidad visual: editorial, con lomos de colores

El aspecto es el de una editorial moderna: papel crema claro, tinta casi negra, títulos de palo seco muy gruesos en mayúscula y el terracota para las acciones principales. El sello de la red son los **lomos de colores planos** (terracota, azul, mostaza, salvia, ciruela, celeste), que aparecen en el estante, las franjas del menú, las fichas y las portadas dibujadas.

| Elemento | Forma |
|----------|-------|
| Fondo y superficies | Papel crema plano; las tarjetas son un tono más claro, con borde fino y esquinas de 16 px |
| Barra superior | Clara, con el logotipo (tres lomos), «PRÉSTAMOS» y «Red de Bibliotecas Públicas»; a la derecha la sede y la persona, en píldoras |
| Menú lateral | Claro, con secciones nombradas en versalitas y un lomo de color; cada opción con su ícono; la actual, en tinta con texto blanco |
| Títulos | Palo seco en su peso más grueso, en mayúscula y con el interletrado cerrado |
| `Button` | Píldoras: terracota para la acción principal, contorno de tinta para las demás, contorno terracota oscuro para dar de baja o bloquear |
| `Table` | Tarjeta con encabezado claro en versalitas grises y filas separadas por un filete |
| `Tabs` | Subrayadas: la actual en tinta con una raya gruesa |
| `FilterBar` | Tarjeta clara; la búsqueda lleva una lupa y un ejemplo |
| `Badge` | Píldora con un punto del color del estado; en una tabla, todas las de la columna miden lo mismo |
| `StatCard` | Rótulo en versalitas, número enorme y tres lomos en la esquina |
| `Timeline` | Línea punteada con un lomo de color por movimiento |
| Inicio público e ingreso | El lema «Pedilo acá. Retiralo allá.», el estante de la red con los más pedidos y las cifras; los más pedidos con su portada en una franja oscura |

La decoración es siempre `aria-hidden` o CSS: no agrega ni quita información, y el estado nunca depende solo del color o de la forma.

## Principios

1. **Claridad ante todo.** Es un sistema de gestión: la información y el estado van antes que la decoración.
2. **El estado no depende solo del color.** Cada estado lleva texto, y el color refuerza. El ítem activo del menú se invierte (tinta con texto blanco) y lleva `aria-current="page"`.
3. **Accesible por defecto.** Contraste AA, foco visible, objetivos táctiles amplios, teclado completo.
4. **Consistente.** Un componente, una forma de usarlo; los tokens son la única fuente de valores.
5. **Editorial y sobria.** Papel, tinta y terracota, con los lomos de colores como único juego; sin imágenes decorativas ni fuentes externas: todo es CSS y SVG en línea.

## Tokens

Se definen como variables CSS en `:root` (`styles/tokens.css`).

### Color

Los pares de color que siguen se verificaron con la fórmula de contraste de WCAG 2.1 (AA exige 4,5:1 para texto normal y 3:1 para componentes gráficos). Los nombres de los tokens son semánticos; las pantallas nunca usan colores sueltos.

| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary-700` | `#B04A27` | Terracota: acción principal, segunda línea del lema, énfasis |
| `--color-primary-800` | `#8F3A1D` | Estado «presionado» de la acción principal |
| `--color-primary-100` | `#F5E1D7` | Fondos de énfasis suave |
| `--color-ink` / `--color-text` | `#1D1B17` | Tinta: texto, enlaces, botones de contorno y la opción actual del menú |
| `--color-text-muted` | `#5C554B` | Texto secundario, rótulos en versalitas |
| `--color-text-subtle` | `#6F675B` | Marcadores de posición, texto deshabilitado |
| `--color-bg` | `#F4EFE7` | Fondo de la aplicación |
| `--color-surface` | `#FBF8F3` | Tarjetas, tablas, formularios |
| `--color-surface-2` | `#EEE7DB` | Encabezado de tablas, píldora de la sede, fondos al pasar el mouse |
| `--color-border` | `#E3D9C9` | Separadores y bordes de tarjetas (decorativos) |
| `--color-border-strong` | `#8C8172` | Bordes de campos y controles (3,8:1 sobre los campos, supera el 3:1 exigido a los componentes) |
| `--color-success-700` / `-100` / `-800` | `#3D6A4C` / `#E1EBE2` / `#2D5139` | Éxito |
| `--color-warning-700` / `-100` / `-800` | `#946510` / `#F6E9C9` / `#6F4A06` | Atención |
| `--color-danger-700` / `-100` / `-800` | `#B23F26` / `#F7E0D8` / `#8E3019` | Error y acciones que dan de baja |
| `--color-info-700` / `-100` / `-800` | `#2C5B7A` / `#DFE8EF` / `#22465E` | Información |
| `--color-neutral-100` / `-700` | `#ECE5D9` / `#4D463D` | Estados neutros o finales |
| `--color-accent-100` / `-800` | `#EFE1EA` / `#613552` | Estados en proceso logístico (ciruela) |

Lomos (decorativos, no transmiten información): `--lomo-burdeos` (terracota `#AD4F2D`), `--lomo-marino` (azul), `--lomo-ocre` (mostaza), `--lomo-bosque` (salvia), `--lomo-ciruela`, `--lomo-petroleo` (celeste), `--lomo-rosa`, `--lomo-negro` y `--lomo-crema`. Sobre los claros (mostaza, celeste, rosa, crema) el texto va en tinta; sobre los demás, en blanco. Los nombres heredados `--color-wood-*`, `--color-brass` y `--color-cream` apuntan a la paleta nueva.

Contrastes verificados:

| Combinación | Relación |
|-------------|----------|
| Texto principal sobre tarjeta / sobre fondo | 16,2:1 / 15,0:1 |
| Texto secundario sobre tarjeta / sobre fondo / sobre encabezado de tabla | 6,9:1 / 6,4:1 / 6,0:1 |
| Texto sutil sobre tarjeta / sobre campo | 5,3:1 / 5,5:1 |
| Borde de campo sobre campo / sobre tarjeta | 3,8:1 / 3,6:1 |
| Blanco sobre primario 700 (acción principal) | 5,4:1 |
| Primario 700 sobre fondo (segunda línea del lema) | 4,8:1 |
| Peligro 700 sobre tarjeta (botones de baja) | 5,5:1 |
| Etiqueta de éxito, atención, peligro, información | 7,3:1 / 6,6:1 / 6,4:1 / 8,0:1 |
| Etiqueta neutra / primaria / de proceso | 7,4:1 / 6,0:1 / 7,8:1 |
| Blanco y gris claro sobre tinta (franja de los más pedidos) | 17,2:1 / 9,6:1 |
| Tinta sobre lomos claros (mostaza, celeste, rosa, crema) | de 6,8:1 a 12,6:1 |
| Blanco sobre lomos oscuros (terracota, salvia, azul, ciruela) | de 5,3:1 a 8,8:1 |

Todas cumplen AA. Como jest-axe no mide contraste en jsdom, estos valores se calcularon aparte: al cambiar un token hay que volver a verificarlos. Los campos usan `--color-border-strong`; `--color-border` queda solo para separadores y tarjetas, que no son necesarios para identificar un control. En foco el borde pasa a tinta con un halo terracota.

### Tipografía

| Token | Valor |
|-------|-------|
| `--font-sans` | `Inter`, `Segoe UI`, `system-ui`, `sans-serif` (texto; sin descargas: usa la del sistema) |
| `--font-titulo` | La misma familia en su peso más grueso (800 y 900), en mayúscula y con interletrado cerrado (títulos, cifras, lema) |
| `--font-mono` | `ui-monospace`, `Consolas`, `monospace` (códigos de inventario, números de remito) |
| Escala (`--text-xs` … `--text-3xl`) | 12, 14, 16, 18, 20, 24 y 30 px; los títulos de pantalla van de 32 a 50 px y el lema de la portada, hasta 136 px |
| Cuerpo | 16 px, interlineado 1,5 |
| Pesos | 400 (texto), 600 (botones, etiquetas), 800 y 900 (títulos y cifras) |
| Versalitas | Rótulos de tablas, secciones del menú e indicadores: 12 px, mayúscula y 0,1–0,16 em de interletrado |

Los números de remito, préstamo y código de inventario se muestran en tipografía monoespaciada para leerlos sin ambigüedad.

### Espaciado, forma y elevación

| Token | Valor |
|-------|-------|
| Escala de espacio | Múltiplos de 4 px: 4, 8, 12, 16, 24, 32, 48 |
| `--radius-sm` / `--radius-md` / `--radius-lg` / `--radius-pill` | 6 / 10 / 16 px y píldora (botones, etiquetas, sede y persona) |
| `--shadow-sm` | `0 1px 2px rgba(29,27,23,.05)` (tarjetas, casi planas) |
| `--shadow-md` | `0 12px 32px rgba(29,27,23,.12)` (menús, modales y la tarjeta de ingreso) |
| Puntos de corte | 640, 768, 1024 y 1280 px |
| Ancho de contenido | Máximo 1240 px |

### Foco e interacción

- Anillo de foco: 3 px de `--color-primary-700` con 2 px de separación; en los campos, borde de tinta con un halo terracota. Nunca se elimina el contorno sin reemplazarlo.
- Altura mínima de controles: 42 px (el criterio AA de objetivos táctiles pide 24 px).
- Estados de cada control: normal, hover, foco, presionado, deshabilitado y, si corresponde, error.
- Se respeta `prefers-reduced-motion`: las transiciones duran 150 ms y se desactivan si el usuario lo pide.

## Componentes base

| Componente | Variantes y notas |
|------------|-------------------|
| `Button` | Píldora: primario (terracota), secundario (contorno de tinta), peligro (contorno terracota oscuro) y enlace; tamaños medio y chico; con `icono` lleva un dibujo antes del texto y con `soloIcono` es un círculo con la ayuda al pasar el mouse; estado «cargando» que deshabilita |
| `Input`, `Select`, `Textarea`, `Checkbox` | Siempre con `FormField` (etiqueta, ayuda y error asociados por `aria-describedby`) |
| `Table` | Cabecera fija opcional, orden por columna, acciones por fila; se convierte en tarjetas bajo 768 px |
| `Pagination` | Anterior/siguiente, tamaño de página, total |
| `Badge` | Etiqueta de estado con color y texto (ver mapa de estados) |
| `Modal` y `ConfirmDialog` | Atrapa el foco, Escape cierra; el diálogo de confirmación describe el efecto |
| `Alert` | Éxito, atención, error, información; con rol `alert` o `status` |
| `Toast` | Resultado de una acción; desaparece solo, sin ocultar información necesaria |
| `Timeline` | Línea de tiempo vertical para los movimientos de remito y préstamo |
| `EmptyState` / `Spinner` / `Skeleton` | Estados vacío (estantería vacía) y de carga (libro que pasa las hojas) |
| `Logo` / `EstanteriaVacia` | Ilustraciones SVG en línea y decorativas |
| `PageHeader` | Título, descripción y acciones de la pantalla |
| `Tabs`, `Card`, `Breadcrumb` | Estructura de pantallas de detalle |
| `AppLayout`, `AppBar`, `Sidebar` | Estructura de las pantallas autenticadas: barra superior, menú lateral por secciones (fijo desde 1024 px, panel deslizable debajo) y `<main>` |
| `Icono` | Juego de íconos de trazo fino (SVG en línea, decorativos): acciones, menú y avisos |
| `Estante` | Lomos de colores planos con los títulos, sobre una tabla; decorativo (inicio público e ingreso) |
| `Portada` | Tapa del libro: la imagen o, si no hay, una tapa plana dibujada con el autor y el título |
| `StatCard` | Tarjeta de indicador del inicio: valor, etiqueta y enlace; con estados de carga y error propios |
| `FilterBar` | Filtros del listado: búsqueda con espera, selectores y botón «Limpiar» |
| `Combobox` | Lista desplegable con búsqueda (por ejemplo, localidades); accesible con teclado y `aria-activedescendant` |
| `WeekScheduleEditor` | Editor semanal de franjas horarias (una fila por día, agregar, quitar, copiar, cerrado) |
| `FiltroFecha` y controles nativos | Fecha y hora con los controles nativos del navegador (`type="date"`, `type="time"`, `type="datetime-local"`), accesibles con teclado y con etiqueta; se muestran como `dd/mm/aaaa` y `HH:mm` |

## Mapa de estados a etiquetas

Una sola tabla de correspondencia (`utils/estados.js`) define cómo se muestra cada estado en toda la aplicación:

| Entidad | Estado | Tono | Texto |
|---------|--------|------|-------|
| Sede | `ACTIVA` | éxito (`success`) | Activa |
|  | `BAJA` | neutro (`neutral`) | Baja |
| Usuario | `ACTIVO` | éxito (`success`) | Activo |
|  | `BAJA` | neutro (`neutral`) | Dado de baja |
| Socio | `HABILITADO` | éxito (`success`) | Habilitado |
|  | `INHABILITADO` | peligro (`danger`) | Inhabilitado |
|  | `BAJA` | neutro (`neutral`) | Dado de baja |
| Ejemplar | `DISPONIBLE` | éxito (`success`) | Disponible |
|  | `APARTADO` | información (`info`) | Apartado |
|  | `RESERVADO` | información (`info`) | Reservado |
|  | `PRESTADO` | atención (`warning`) | Prestado |
|  | `EN_TRANSITO` | información (`info`) | En tránsito |
|  | `EN_REVISION` | peligro (`danger`) | En revisión |
|  | `BAJA` | neutro (`neutral`) | Dado de baja |
| Préstamo | `SOLICITADO` | información (`info`) | Solicitado |
|  | `EN_ENVIO` | información (`info`) | En envío |
|  | `ACTIVO` | éxito (`success`) | Activo |
|  | `VENCIDO` | peligro (`danger`) | Vencido |
|  | `DEVUELTO` | neutro (`neutral`) | Devuelto |
|  | `CANCELADO` | neutro (`neutral`) | Cancelado |
| Remito | `GENERADO` | información (`info`) | Generado |
|  | `EMPAQUETADO` | información (`info`) | Empaquetado |
|  | `DESPACHADO` | atención (`warning`) | Despachado |
|  | `EN_TRANSITO` | atención (`warning`) | En tránsito |
|  | `RECIBIDO` | éxito (`success`) | Recibido |
|  | `EXTRAVIADO` | peligro (`danger`) | Extraviado |
|  | `DANADO` | peligro (`danger`) | Recibido con daño |
|  | `DESTRUIDO` | peligro (`danger`) | Recibido destruido |
|  | `INCOMPLETO` | peligro (`danger`) | Recibido con faltantes |
|  | `ANULADO` | neutro (`neutral`) | Anulado |
| Reserva | `PENDIENTE` | información (`info`) | En espera |
|  | `DISPONIBLE_PARA_RETIRO` | éxito (`success`) | Lista para retirar |
|  | `CUMPLIDA` | neutro (`neutral`) | Cumplida |
|  | `CANCELADA` | neutro (`neutral`) | Cancelada |
|  | `VENCIDA` | atención (`warning`) | Vencida |
| Multa | `PENDIENTE` | peligro (`danger`) | Pendiente |
|  | `SALDADA` | éxito (`success`) | Saldada |
| Pago | `PENDIENTE` | información (`info`) | En curso |
|  | `APROBADO` | éxito (`success`) | Aprobado |
|  | `RECHAZADO` | peligro (`danger`) | Rechazado |
|  | `CANCELADO` | neutro (`neutral`) | Cancelado |

Si se cambia un tono o un texto, se cambia en `utils/estados.js` y esta tabla se actualiza con él.

## Estructura de pantallas autenticadas

- **Menú lateral** de 260 px, claro y separado del contenido por un filete. Cada sección tiene su nombre en versalitas con un lomo de color; cada opción, su ícono. La opción actual se invierte (tinta con texto blanco) y lleva `aria-current="page"`. Por debajo de 1024 px es un panel deslizable que atrapa el foco.
- **AppBar** de 72 px, clara: logotipo de tres lomos, «PRÉSTAMOS» con «Red de Bibliotecas Públicas» debajo, la sede del usuario en una píldora con un ícono de ubicación y la persona en otra, con su inicial en un círculo.
- Contenido principal con márgenes amplios (48 px en escritorio, 16 px en pantallas chicas) y ancho máximo de 1240 px. Cada pantalla abre con un `PageHeader`: título enorme en mayúscula, bajada en gris y las acciones a la derecha.
- Indicador «abierta ahora»: `Badge` de éxito con el texto «Abierta» o neutro con «Cerrada» (siempre con texto).

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
