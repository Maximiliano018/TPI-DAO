# 10. Guía de estilos (design system base)

Design system propio y liviano para el frontend. Es **reemplazable**: todo el aspecto sale de variables CSS (tokens), así que adoptar otro design system implica cambiar los valores de `styles/tokens.css` y revisar los componentes base, sin tocar las pantallas.

## Identidad visual: una biblioteca

El aspecto del sistema evoca el dominio del proyecto (bibliotecas, libros, fichas y préstamos) sin perder legibilidad:

| Elemento | Metáfora |
|----------|----------|
| Fondo de la aplicación | Pergamino cálido; las superficies son fichas de catálogo de papel crema |
| Barra superior | Moldura de nogal con un filete de latón y el logotipo (libro abierto con marcador) |
| Menú lateral | **Estantería**: cada ítem es un libro apilado sobre una tabla de madera; el de la página actual sobresale de la pila y lleva un marcador; debajo, estantes decorativos |
| Títulos, encabezados de tabla, etiquetas de campos | Tipografía serif, como en el lomo y las portadas |
| `Card`, `Modal`, `StatCard` | Ficha de catálogo: filete superior verde, cabecera con doble filete; el indicador del inicio lleva una cinta marcadora |
| `Table` | Libro de registro: cabecera de cuero verde con filete de latón, renglones rayados |
| `Tabs` | Separadores de fichero |
| `FilterBar` | Cajón de fichero con borde de madera |
| `Badge` | Etiqueta adhesiva de lomo, con filete del mismo color |
| `Textarea` | Hoja rayada |
| `Timeline` | Hilo con alfileres de latón |
| Carga | Un libro que pasa las hojas; el vacío muestra una estantería vacía |
| Ingreso | Carnet de socio sobre una pared de nogal |

La decoración es siempre `aria-hidden` o CSS: no agrega ni quita información, y el estado nunca depende solo del color o de la forma.

## Principios

1. **Claridad ante todo.** Es un sistema de gestión: la información y el estado van antes que la decoración.
2. **El estado no depende solo del color.** Cada estado lleva texto, y el color refuerza. El ítem activo del menú sobresale, lleva un marcador y `aria-current="page"`.
3. **Accesible por defecto.** Contraste AA, foco visible, objetivos táctiles amplios, teclado completo.
4. **Consistente.** Un componente, una forma de usarlo; los tokens son la única fuente de valores.
5. **Temática pero sobria.** Pocos colores (verde, burdeos, latón sobre papel y madera), sin imágenes ni fuentes externas: todo es CSS y SVG en línea.

## Tokens

Se definen como variables CSS en `:root`. Los pares de color que siguen se verificaron con la fórmula de contraste de WCAG 2.1; la columna indica la relación obtenida (AA exige 4,5:1 para texto normal y 3:1 para componentes gráficos).

### Color

Los pares de color que siguen se verificaron con la fórmula de contraste de WCAG 2.1 (AA exige 4,5:1 para texto normal y 3:1 para componentes gráficos). Los nombres de los tokens son semánticos; las pantallas nunca usan colores sueltos.

| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary-700` | `#1F5C47` | Verde de lámpara de lectura: acciones principales, enlaces, filetes de fichas |
| `--color-primary-800` | `#164433` | Estado «presionado», enlaces visitados, cabecera de tablas |
| `--color-primary-100` | `#DCEBE2` | Fondos de selección y énfasis suave |
| `--color-text` | `#2A1C12` | Texto principal (tinta sepia) |
| `--color-text-muted` | `#5B4636` | Texto secundario |
| `--color-text-subtle` | `#6F5A48` | Marcadores de posición, texto deshabilitado |
| `--color-bg` | `#F3EAD7` | Fondo de la aplicación (pergamino) |
| `--color-surface` | `#FFFBF0` | Tarjetas, tablas, formularios (ficha de catálogo) |
| `--color-border` | `#D9C9A8` | Separadores y bordes decorativos |
| `--color-border-strong` | `#8A7152` | Bordes de campos y controles (4,5:1 sobre las fichas, supera el 3:1 exigido a los componentes) |
| `--color-success-700` / `-100` / `-800` | `#3B6A22` / `#E3EFD3` / `#2C5219` | Éxito |
| `--color-warning-700` / `-100` / `-800` | `#8A5A00` / `#F8E8BD` / `#6B4400` | Atención (ocre) |
| `--color-danger-700` / `-100` / `-800` | `#9B2C1F` / `#F7DCD5` / `#7D2217` | Error y acciones destructivas (cuero burdeos) |
| `--color-info-700` / `-100` / `-800` | `#1F4E79` / `#DCE8F3` / `#183C5E` | Información (tinta azul) |
| `--color-neutral-100` / `-700` | `#ECE3D0` / `#4A3A2C` | Estados neutros o finales |
| `--color-accent-100` / `-800` | `#EADFF0` / `#573069` | Estados en proceso logístico (ciruela) |

Tokens decorativos (no transmiten información): `--color-wood-900/800/600/400` (nogal), `--color-brass` (`#D6AD45`, latón), `--color-cream` (`#FDF6E3`), `--color-marcador` (`#B3261E`, cinta) y los lomos `--lomo-burdeos`, `--lomo-bosque`, `--lomo-marino`, `--lomo-ocre`, `--lomo-ciruela` y `--lomo-petroleo`. Las texturas (`--textura-papel`, `--textura-madera`) son gradientes CSS.

Contrastes verificados:

| Combinación | Relación |
|-------------|----------|
| Texto principal sobre ficha / sobre fondo | 16,0:1 / 13,8:1 |
| Texto secundario sobre ficha | 8,6:1 |
| Texto sutil sobre ficha / sobre fondo | 6,3:1 / 5,4:1 |
| Borde de campo sobre ficha | 4,5:1 |
| Blanco sobre primario 700 | 7,8:1 |
| Enlace (primario 700) sobre ficha / sobre fondo | 7,6:1 / 6,6:1 |
| Blanco sobre peligro 700 | 7,6:1 |
| Blanco sobre éxito 800, peligro 800 e información 800 (avisos) | 9,0:1 / 9,9:1 / 11,4:1 |
| Etiqueta de éxito, atención, peligro, información | 7,5:1 / 7,0:1 / 7,6:1 / 9,1:1 |
| Etiqueta neutra / primaria / de proceso | 8,5:1 / 8,9:1 / 8,0:1 |
| Crema sobre madera (barra superior) | 13,6:1 |
| Latón sobre madera (foco y detalles) | 6,9:1 |
| Crema sobre los lomos del menú | de 5,5:1 (ocre) a 10,7:1 (marino) |

Todas cumplen AA. Como jest-axe no mide contraste en jsdom, estos valores se calcularon aparte: al cambiar un token hay que volver a verificarlos. Los campos usan `--color-border-strong`; `--color-border` queda solo para separadores que no son necesarios para identificar un control. En foco y en error el borde se engrosa y cambia de color.

### Tipografía

| Token | Valor |
|-------|-------|
| `--font-sans` | `Inter`, `system-ui`, `sans-serif` |
| `--font-serif` | `Iowan Old Style`, `Palatino Linotype`, `Palatino`, `Georgia`, `serif` (títulos, lomos del menú, encabezados de tabla y etiquetas de campos; sin descargas) |
| `--font-mono` | `ui-monospace`, `monospace` (códigos de inventario, números de remito) |
| Escala (`--text-xs` … `--text-3xl`) | 12, 14, 16, 18, 20, 24 y 30 px |
| Cuerpo | 16 px, interlineado 1,5 |
| Pesos | 400 (texto), 600 (botones, etiquetas de estado), 700 (títulos serif) |

Los números de remito, préstamo y código de inventario se muestran en tipografía monoespaciada para leerlos sin ambigüedad.

### Espaciado, forma y elevación

| Token | Valor |
|-------|-------|
| Escala de espacio | Múltiplos de 4 px: 4, 8, 12, 16, 24, 32, 48 |
| `--radius-sm` / `--radius-md` / `--radius-lg` | 3 / 6 / 10 px (esquinas poco redondeadas, como el papel) |
| `--shadow-sm` | `0 1px 2px rgba(59,35,20,.14)` (sombras tibias, marrones) |
| `--shadow-md` | `0 6px 16px rgba(59,35,20,.22)` (menús y modales) |
| Puntos de corte | 640, 768, 1024 y 1280 px |
| Ancho de contenido | Máximo 1200 px |

### Foco e interacción

- Anillo de foco: 3 px de `--color-primary-700` con 2 px de separación; sobre madera (menú y barra superior) es de latón (`--color-brass`). Nunca se elimina el contorno sin reemplazarlo.
- Altura mínima de controles: 40 px (el criterio AA de objetivos táctiles pide 24 px).
- Estados de cada control: normal, hover, foco, presionado, deshabilitado y, si corresponde, error.
- Se respeta `prefers-reduced-motion`: las transiciones duran 150 ms y se desactivan si el usuario lo pide.

## Componentes base

| Componente | Variantes y notas |
|------------|-------------------|
| `Button` | Primario (cuero verde con filete de latón), secundario, peligro (burdeos) y enlace; tamaños medio y chico; estado «cargando» que deshabilita |
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
| `AppLayout`, `AppBar`, `Sidebar` | Estructura de las pantallas autenticadas: barra superior, menú lateral con forma de estantería (fijo desde 1024 px, panel deslizable debajo) y `<main>` |
| `StatCard` | Tarjeta de indicador del inicio: valor, etiqueta y enlace; con estados de carga y error propios |
| `FilterBar` | Filtros del listado: búsqueda con espera, selectores y botón «Limpiar» |
| `Combobox` | Lista desplegable con búsqueda (por ejemplo, localidades); accesible con teclado y `aria-activedescendant` |
| `WeekScheduleEditor` | Editor semanal de franjas horarias (una fila por día, agregar, quitar, copiar, cerrado) |
| `DatePicker` y `TimeInput` | Fecha (`dd/mm/aaaa`) y hora (`HH:mm`) con teclado y etiquetas |

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

## Estructura de pantallas autenticadas

- **Menú lateral** de 248 px, de nogal con veta y laterales sombreados. Los ítems son libros apilados sobre una tabla de madera (colores y anchos distintos, con cartela de latón y canto de hojas); al pasar el cursor el libro se desplaza y el de la página actual sobresale con un marcador y `aria-current="page"`. Debajo hay estantes decorativos (`aria-hidden`) que se recortan según la altura de la ventana. Por debajo de 1024 px es un panel deslizable que atrapa el foco, con la misma estantería.
- **AppBar** de 60 px, de nogal con filete de latón: logotipo, nombre del sistema en serif, sede del usuario en cursiva y menú de usuario.
- Contenido principal con padding de 24 px (16 px en pantallas chicas) y ancho máximo de 1200 px. Cada pantalla abre con un `PageHeader` (título serif, descripción en cursiva y doble filete).
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
