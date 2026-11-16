# 10. Guía de estilos (design system base)

Design system propio y liviano para el frontend. Es **reemplazable**: todo el aspecto sale de variables CSS (tokens), así que adoptar otro design system implica cambiar los valores de `styles/tokens.css` y revisar los componentes base, sin tocar las pantallas.

## Identidad visual: blanco, turquesa y gris, con libros ilustrados

El aspecto es limpio y amable: fondo blanco con una trama de puntitos muy suave, texto gris pizarra, **turquesa** para los acentos y las franjas, y **gris carbón** para las acciones principales. Los títulos van en mayúscula, con la primera línea fina y la segunda gruesa en turquesa. Las ilustraciones de libros (planas, con colores de tapa variados) y unas pocas formas suaves (cuadrados girados, parches de puntitos) dan el toque decorativo.

| Elemento | Forma |
|----------|-------|
| Fondo y superficies | Blanco con trama de puntitos; tarjetas blancas con borde fino y esquinas de 16 px; gris claro para encabezados de tablas y secciones |
| Barra superior | Blanca, con una línea turquesa abajo: logotipo (libro abierto con marcador), «PRÉSTAMOS» y «Red de Bibliotecas Públicas»; a la derecha, la sede del bibliotecario y el menú de la persona |
| Menú lateral | Turquesa oscuro con puntitos; las secciones con su nombre en celeste claro; cada opción con su ícono dentro de un cuadradito del color de su sección; la actual, en blanco |
| Títulos | Mayúscula gruesa con una rayita turquesa debajo |
| `Button` | Píldoras: gris carbón para la acción principal, contorno gris para las demás y contorno rojizo para dar de baja o bloquear |
| `Table` | Tarjeta con encabezado gris claro en versalitas y filas separadas por un filete |
| `Tabs` | Subrayadas: la actual en tinta con una raya gruesa |
| `FilterBar` | Tarjeta clara; la búsqueda lleva una lupa y un ejemplo |
| `Badge` | Píldora con un punto del color del estado; en una tabla, todas las de la columna miden lo mismo |
| `StatCard` | Rótulo en versalitas, número grande y tres lomos en la esquina |
| `Timeline` | Línea punteada con un lomo de color por movimiento |
| Inicio público | El lema, una biblioteca ilustrada sobre una mancha turquesa (con plantas, pilas y libros que salen volando) y las cifras en una franja turquesa; abajo, los más pedidos con su portada y, al final, una silueta de libros que pasa al pie |
| Ingreso | El lema, las cifras y tres ventajas a la izquierda; la tarjeta con un sello del logo a la derecha; abajo, la misma silueta de libros |

La decoración es siempre `aria-hidden` o CSS: no agrega ni quita información, y el estado nunca depende solo del color o de la forma.

## Principios

1. **Claridad ante todo.** Es un sistema de gestión: la información y el estado van antes que la decoración.
2. **El estado no depende solo del color.** Cada estado lleva texto, y el color refuerza. El ítem activo del menú se pasa a blanco y lleva `aria-current="page"`.
3. **Accesible por defecto.** Contraste AA, foco visible, objetivos táctiles amplios, teclado completo.
4. **Consistente.** Un componente, una forma de usarlo; los tokens son la única fuente de valores.
5. **Limpia y amable.** Blanco, gris y turquesa, con los libros ilustrados como único juego de colores; sin imágenes decorativas ni fuentes externas: todo es CSS y SVG en línea.

## Tokens

Se definen como variables CSS en `:root` (`styles/tokens.css`).

### Color

Los pares de color que siguen se verificaron con la fórmula de contraste de WCAG 2.1 (AA exige 4,5:1 para texto normal y 3:1 para componentes gráficos). Los nombres de los tokens son semánticos; las pantallas nunca usan colores sueltos.

| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary-700` / `-800` / `-100` | `#43484C` / `#33373A` / `#E8EEF0` | Gris carbón: acción principal y su estado «presionado» |
| `--color-turquesa` | `#4BA3A8` | Turquesa de las manchas, líneas y detalles |
| `--color-terracota` | `#3D8F94` | Turquesa oscuro: segunda línea del lema, íconos de las cifras (el nombre del token quedó de la paleta anterior) |
| `--color-marino` | `#2A7075` | Turquesa profundo: menú lateral, franja de cifras, pie (texto blanco) |
| `--color-ink` / `--color-text` | `#2D3236` | Texto |
| `--color-text-muted` | `#5C6368` | Texto secundario, rótulos en versalitas |
| `--color-text-subtle` | `#6C7378` | Marcadores de posición |
| `--color-titulo-fino` | `#7A8085` | Primera línea fina del lema (texto grande) |
| `--color-bg` / `--color-surface` | `#FFFFFF` | Fondo y tarjetas |
| `--color-surface-2` | `#F3F6F7` | Encabezado de tablas, sección de los más pedidos |
| `--color-border` | `#E1E7EA` | Separadores y bordes de tarjetas (decorativos) |
| `--color-border-strong` | `#7A8085` | Bordes de campos y controles |
| `--color-success-700` / `-100` / `-800` | `#3B7A4F` / `#E3F2E7` / `#2B5C3A` | Éxito |
| `--color-warning-700` / `-100` / `-800` | `#946510` / `#FAF0D2` / `#6F4A06` | Atención |
| `--color-danger-700` / `-100` / `-800` | `#B2402C` / `#FBE6E1` / `#8E311F` | Error y acciones que dan de baja |
| `--color-info-700` / `-100` / `-800` | `#2A7075` / `#E3F2F2` / `#1F5559` | Información |
| `--color-neutral-100` / `-700` | `#EEF2F3` / `#4E5559` | Estados neutros o finales |
| `--color-accent-100` / `-800` | `#EEE7F3` / `#5D3F78` | Estados en proceso logístico |

Lomos (decorativos, no transmiten información): `--lomo-rojo`, `--lomo-naranja`, `--lomo-amarillo`, `--lomo-verde`, `--lomo-turquesa`, `--lomo-azul`, `--lomo-indigo`, `--lomo-violeta` y `--lomo-rosa`; se usan en las franjas del menú, las fichas y las portadas dibujadas. Las ilustraciones (`Biblioteca`, `SiluetaLibros`) usan su propia paleta armónica con el turquesa (coral, arena, mostaza, salvia, petróleo, rosa viejo y crema). Los nombres heredados `--color-wood-*`, `--color-brass` y `--color-cream` apuntan a la paleta.

Contrastes verificados:

| Combinación | Relación |
|-------------|----------|
| Texto sobre blanco / sobre gris claro | 13,0:1 / 11,9:1 |
| Texto secundario sobre blanco / sobre gris claro | 6,1:1 / 5,6:1 |
| Texto sutil sobre blanco | 4,8:1 |
| Primera línea fina del lema (texto grande) / borde de campo | 4,0:1 / 4,0:1 |
| Blanco sobre la acción principal | 9,3:1 |
| Turquesa oscuro sobre blanco (texto grande e íconos) | 3,8:1 |
| Peligro 700 sobre blanco (botones de baja) | 5,7:1 |
| Etiqueta de éxito, atención, peligro, información | 6,7:1 / 6,9:1 / 6,7:1 / 7,3:1 |
| Etiqueta neutra / primaria / de proceso | 6,7:1 / 10,2:1 / 7,1:1 |
| Blanco / celeste claro sobre el menú y las franjas | 5,7:1 / 4,6:1 |

Todas cumplen AA. Como jest-axe no mide contraste en jsdom, estos valores se calcularon aparte: al cambiar un token hay que volver a verificarlos. Los campos usan `--color-border-strong`; `--color-border` queda solo para separadores y tarjetas, que no son necesarios para identificar un control. En foco el borde pasa a tinta con un halo terracota.

### Tipografía

| Token | Valor |
|-------|-------|
| `--font-sans` | `Inter`, `Segoe UI`, `system-ui`, `sans-serif` (texto; sin descargas: usa la del sistema) |
| `--font-titulo` | La misma familia en su peso más grueso (800 y 900), en mayúscula y con interletrado cerrado (títulos, cifras, lema) |
| `--font-mono` | `ui-monospace`, `Consolas`, `monospace` (códigos de inventario, números de remito) |
| Escala (`--text-xs` … `--text-3xl`) | 12, 14, 16, 18, 20, 24 y 30 px; los títulos de pantalla van de 24 a 32 px y el lema de la portada, hasta 70 px |
| Cuerpo | 15 px, interlineado 1,55 |
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
| Ancho de contenido | Máximo 1180 px |

### Foco e interacción

- Anillo de foco: 3 px de `--color-primary-700` con 2 px de separación; en los campos, borde de tinta con un halo terracota. Nunca se elimina el contorno sin reemplazarlo.
- Altura mínima de controles: 40 px (el criterio AA de objetivos táctiles pide 24 px).
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
| `Biblioteca` | Ilustración del inicio público: biblioteca de madera clara con lomos, plantas, pilas y libros volando; decorativa |
| `SiluetaLibros` | Silueta de lomos en dos capas sobre el pie (inicio público e ingreso); decorativa |
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

- **Menú lateral** de 236 px, turquesa oscuro con puntitos. Cada sección tiene su nombre en celeste claro; cada opción, su ícono dentro de un cuadradito del color de su sección. La opción actual se pasa a blanco y lleva `aria-current="page"`. Por debajo de 1024 px es un panel deslizable que atrapa el foco.
- **AppBar** de 64 px, blanca con una línea turquesa abajo: logotipo (libro abierto con marcador), «PRÉSTAMOS» con «Red de Bibliotecas Públicas» debajo, la sede del bibliotecario (el administrador no tiene una) y el menú de la persona.
- Contenido principal sobre una trama de puntitos suave, con una forma turquesa arriba a la derecha; márgenes de 32 px en escritorio (16 px en pantallas chicas) y ancho máximo de 1180 px. Cada pantalla abre con un `PageHeader`: título en mayúscula gruesa con una rayita turquesa, bajada en gris y las acciones a la derecha.
- Indicador «abierta ahora»: `Badge` de éxito con el texto «Abierta» o neutro con «Cerrada» (siempre con texto).

## Voz y contenido

- Español neutro rioplatense, directo y sin tecnicismos: «El socio está inhabilitado por un préstamo vencido», no «Error 409».
- Se trata de **usted** en toda la interfaz, también en el inicio público y el login: «Ingrese de nuevo», «Pídalo acá. Retírelo allá.», no «Ingresá» ni «Pedilo».
- Los mensajes de error dicen **qué pasó y qué hacer**.
- Botones con verbos concretos: «Registrar préstamo», «Despachar remito», no «Aceptar».
- Fechas `dd/mm/aaaa`, hora `HH:mm`, montos con el símbolo `$` y separadores locales.

## Cómo reemplazarlo por otro design system

1. Mapear los tokens de esta guía a los del otro sistema en `styles/tokens.css`.
2. Reemplazar internamente los componentes de `components/` conservando su interfaz (las pantallas no cambian).
3. Mantener `utils/estados.js` y volver a verificar los contrastes con la tabla de arriba.

Si el equipo ya tiene un design system (por ejemplo, en Figma), pasar el enlace o los tokens y esta guía se actualiza para reflejarlo.
