# DESIGN SYSTEM — Sistema de Préstamos Interbibliotecarios

> Estado: **borrador v1**. Decisiones pendientes en [pendientes.md](pendientes.md) (`[PENDIENTE-D*]`).
> Implementación: CSS puro con custom properties (`frontend/src/styles/tokens.css`) + CSS Modules. Sin librería de componentes externa.

## 1. Principios de diseño (UX/UI)

Es una herramienta de **trabajo diario del personal**: se usa durante horas, con muchos datos y tareas repetitivas. Estética sobria institucional.

1. **Claridad antes que decoración.** Cada elemento tiene una función. Poco color, mucho contraste, jerarquía evidente.
2. **Densidad legible.** Tablas y formularios compactos pero con aire suficiente; el personal ve muchas filas sin fatiga.
3. **El estado siempre visible.** Estado de remito, préstamo y ejemplar se comunican con color **y** texto/ícono, nunca solo color.
4. **Prevenir antes que corregir.** Las acciones no permitidas (p. ej. prestar a un socio inhabilitado) se deshabilitan con explicación, y los errores de negocio del backend se muestran en lenguaje claro.
5. **Acciones destructivas o irreversibles piden confirmación** (dar de baja una sede, marcar un remito como extraviado).
6. **Consistencia.** Mismo componente para mismo problema; un solo lugar para cada decisión visual (los tokens).
7. **Accesible por defecto.** Contraste WCAG AA, navegación por teclado, foco visible, HTML semántico, `prefers-reduced-motion` respetado.
8. **Tema claro y oscuro** desde los tokens, sin duplicar estilos.

## 2. Tipografías

| Uso | Familia | Fallback |
|---|---|---|
| Interfaz y títulos | **Inter** | `system-ui, -apple-system, "Segoe UI", sans-serif` |
| Código, números de remito, ISBN, códigos de inventario | **JetBrains Mono** | `ui-monospace, "SF Mono", Consolas, monospace` |

- Se cargan desde Google Fonts (o autoalojadas) con `font-display: swap`.
- Los identificadores (nº de remito, ISBN, código de inventario) usan la monoespaciada con `font-variant-numeric: tabular-nums` para alinear columnas.
- Pesos usados: 400 (texto), 500 (énfasis/etiquetas), 600 (títulos).

## 3. Color

Paleta sobria: primario **azul petróleo**, neutros fríos y cuatro colores semánticos. Los valores son propuestos y se ajustan al validar contraste.

### Primario (azul petróleo)
| Token | Claro | Uso |
|---|---|---|
| `--color-primary-50` | `#E8F4F6` | Fondos sutiles, hover de filas |
| `--color-primary-100` | `#C9E4E9` | |
| `--color-primary-500` | `#1F7A8C` | Elementos secundarios |
| `--color-primary-600` | `#17606F` | **Botón primario, enlaces** |
| `--color-primary-700` | `#114A56` | Hover/activo |

### Neutros
| Token | Claro |
|---|---|
| `--color-neutral-0` | `#FFFFFF` |
| `--color-neutral-50` | `#F6F8F9` |
| `--color-neutral-100` | `#EAEEF0` |
| `--color-neutral-300` | `#C5CED3` |
| `--color-neutral-500` | `#6B7A83` |
| `--color-neutral-700` | `#34424A` |
| `--color-neutral-900` | `#16202A` |

### Semánticos
| Significado | Fondo | Texto/borde | Uso en el dominio |
|---|---|---|---|
| Éxito | `#E6F4EA` | `#1E7B3A` | Recibido conforme, Devuelto, Disponible |
| Advertencia | `#FFF4DB` | `#8A5A00` | Vencido próximo, Reservado, En revisión |
| Error | `#FDE8E8` | `#B3261E` | Extraviado, Destruido, Inhabilitado, Vencido |
| Información | `#E3F0FB` | `#1A5C99` | En tránsito, Solicitado, En envío |

### Mapeo de estados a color
Los estados son los de [ARCHITECTURE.md §4.4](ARCHITECTURE.md#44-máquinas-de-estado). Las condiciones derivadas (no son estados guardados) se muestran como un badge adicional junto al estado.

| Entidad | Estado → variante |
|---|---|
| Remito | Generado / Empaquetado → neutral · En tránsito → info · Recibido → éxito · Extraviado → error · Cancelado → neutral |
| Remito (revisión) | Conforme → éxito · Dañado → advertencia · Destruido → error |
| Préstamo | En envío → info · Listo para retiro → advertencia · Activo → primario · Devuelto → éxito · Cancelado → neutral |
| Ejemplar | Disponible → éxito · Reservado → advertencia · Pendiente de despacho → info · En tránsito → info · Prestado → primario · En revisión → advertencia · Baja → error |
| Reserva | Pendiente → neutral · Asignada → advertencia · Cumplida → éxito · Vencida → error · Cancelada → neutral |
| Multa | Pendiente → error · Saldada → éxito |
| Socio | Habilitado → éxito · Inhabilitado → error · Baja → neutral |
| Sede | Activa → éxito · Baja → neutral |

**Condiciones derivadas** (badge adicional):

| Condición | Se muestra sobre | Variante |
|---|---|---|
| Vencido | Préstamo activo con la fecha de vencimiento pasada | error |
| Retiro vencido | Préstamo listo para retiro con el plazo de retiro pasado | error |
| Demorado | Remito en tránsito más días que `dias_max_transito` | advertencia |
| Consulta en sala | Ejemplar no prestable | neutral |

### Tema oscuro
Se redefinen los **tokens semánticos** (`--surface`, `--text`, `--border`, etc.) bajo `prefers-color-scheme: dark` y `[data-theme="dark"]`; los componentes solo usan tokens semánticos, por lo que no cambian.

## 4. Type scale

Escala modular (~1.2) con base de 16 px.

| Token | Tamaño | Line-height | Peso | Uso |
|---|---|---|---|---|
| `--text-xs` | 0.75rem (12px) | 1.4 | 400/500 | Ayudas, badges, pie de tabla |
| `--text-sm` | 0.875rem (14px) | 1.5 | 400/500 | **Tablas, formularios, cuerpo denso** |
| `--text-md` | 1rem (16px) | 1.5 | 400 | Cuerpo general |
| `--text-lg` | 1.125rem (18px) | 1.4 | 600 | Subtítulos de sección |
| `--text-xl` | 1.25rem (20px) | 1.3 | 600 | Título de tarjeta/diálogo |
| `--text-2xl` | 1.5rem (24px) | 1.25 | 600 | Título de página |
| `--text-3xl` | 1.875rem (30px) | 1.2 | 600 | Cifras destacadas (tablero) |

## 5. Spacing

Base de **4 px**. Solo se usan estos valores.

| Token | Valor |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 24px |
| `--space-6` | 32px |
| `--space-7` | 48px |
| `--space-8` | 64px |

Reglas: separación entre campos de formulario `--space-4`; padding de tarjeta `--space-5`; gutter de página `--space-4` (móvil) y `--space-6` (escritorio); celdas de tabla `--space-2`/`--space-3`.

## 6. Radius y elevation

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | 4px | Inputs, badges |
| `--radius-md` | 8px | Botones, tarjetas |
| `--radius-lg` | 12px | Diálogos, paneles |
| `--radius-full` | 9999px | Avatares, pills |

| Token | Valor | Uso |
|---|---|---|
| `--shadow-0` | `none` | Contenido plano, tablas |
| `--shadow-1` | `0 1px 2px rgb(22 32 42 / 0.08)` | Tarjetas |
| `--shadow-2` | `0 4px 12px rgb(22 32 42 / 0.12)` | Menús desplegables, popovers |
| `--shadow-3` | `0 12px 32px rgb(22 32 42 / 0.20)` | Diálogos modales |

La elevación se usa con moderación; la jerarquía se logra primero con borde y color de superficie.

## 7. Tokens CSS

Archivo `frontend/src/styles/tokens.css`. Dos capas: **primitivos** (valores crudos) y **semánticos** (significado). Los componentes consumen solo los semánticos.

```css
:root {
  /* ---------- Primitivos ---------- */
  --color-primary-50:  #E8F4F6;
  --color-primary-100: #C9E4E9;
  --color-primary-500: #1F7A8C;
  --color-primary-600: #17606F;
  --color-primary-700: #114A56;

  --color-neutral-0:   #FFFFFF;
  --color-neutral-50:  #F6F8F9;
  --color-neutral-100: #EAEEF0;
  --color-neutral-300: #C5CED3;
  --color-neutral-500: #6B7A83;
  --color-neutral-700: #34424A;
  --color-neutral-900: #16202A;

  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Consolas, monospace;

  --text-xs: 0.75rem;   --text-sm: 0.875rem; --text-md: 1rem;
  --text-lg: 1.125rem;  --text-xl: 1.25rem;  --text-2xl: 1.5rem; --text-3xl: 1.875rem;

  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;

  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 9999px;

  --shadow-1: 0 1px 2px rgb(22 32 42 / 0.08);
  --shadow-2: 0 4px 12px rgb(22 32 42 / 0.12);
  --shadow-3: 0 12px 32px rgb(22 32 42 / 0.20);

  --duration-fast: 120ms; --duration-base: 200ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);

  /* ---------- Semánticos (tema claro) ---------- */
  --surface:        var(--color-neutral-0);
  --surface-subtle: var(--color-neutral-50);
  --surface-hover:  var(--color-primary-50);
  --border:         var(--color-neutral-300);
  --text:           var(--color-neutral-900);
  --text-muted:     var(--color-neutral-500);
  --accent:         var(--color-primary-600);
  --accent-hover:   var(--color-primary-700);
  --on-accent:      #FFFFFF;
  --focus-ring:     0 0 0 3px rgb(31 122 140 / 0.45);

  --success-bg: #E6F4EA; --success-fg: #1E7B3A;
  --warning-bg: #FFF4DB; --warning-fg: #8A5A00;
  --danger-bg:  #FDE8E8; --danger-fg:  #B3261E;
  --info-bg:    #E3F0FB; --info-fg:    #1A5C99;
}

/* ---------- Tema oscuro ---------- */
:root[data-theme="dark"] {
  --surface:        #16202A;
  --surface-subtle: #1D2A35;
  --surface-hover:  #22404A;
  --border:         #34424A;
  --text:           #EAEEF0;
  --text-muted:     #9AA9B2;
  --accent:         #4FB3C6;
  --accent-hover:   #7CC9D8;
  --on-accent:      #0B1A20;
  --focus-ring:     0 0 0 3px rgb(79 179 198 / 0.5);

  --success-bg: #12301C; --success-fg: #6FD08C;
  --warning-bg: #3A2C08; --warning-fg: #F0C265;
  --danger-bg:  #3D1512; --danger-fg:  #F28B82;
  --info-bg:    #0F2A42; --info-fg:    #7DB8EC;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* mismos valores que [data-theme="dark"] */ }
}
@media (prefers-reduced-motion: reduce) {
  :root { --duration-fast: 0ms; --duration-base: 0ms; }
}
```

Reglas de uso: ningún componente usa un hex, `px` de espaciado o sombra literal; todo sale de un token. Los pares texto/fondo deben cumplir **AA** (4.5:1 texto normal, 3:1 texto grande y bordes de controles); validar al cerrar la paleta.

## 8. Core components

Componentes base en `frontend/src/components/`. Cada uno documenta variantes, estados (hover, foco, deshabilitado, cargando, error) y es accesible.

| Componente | Variantes / notas |
|---|---|
| **Button** | `primary`, `secondary`, `ghost`, `danger`; tamaños `sm`/`md`; estado `loading`; con ícono |
| **Input / Textarea** | Etiqueta, ayuda, error; prefijo/sufijo |
| **Select / Combobox** | Búsqueda para elegir socio, libro, sede |
| **Checkbox / Radio / Switch** | Switch para activo/baja |
| **DatePicker** | Fechas de vencimiento, filtros de reporte |
| **FormField** | Compone etiqueta + control + ayuda + error |
| **Badge / StatusBadge** | Muestra estado con color **y** texto/ícono; usa el mapeo de §3 |
| **Table (DataTable)** | Cabecera fija, ordenamiento, paginación, filas seleccionables, estado vacío y de carga |
| **Card** | Contenedor con borde/sombra `shadow-1` |
| **Modal / ConfirmDialog** | Confirmaciones de acciones irreversibles; foco atrapado |
| **Toast / Alert** | Resultado de acciones y errores de negocio del backend (`info`/`success`/`warning`/`danger`) |
| **Tabs** | Secciones de una ficha |
| **Pagination** | Con `limit`/`offset` de la API |
| **Tooltip** | Explicar controles deshabilitados |
| **EmptyState / Skeleton / Spinner** | Estados vacío y de carga |
| **AppShell** (Sidebar + Topbar) | Navegación por rol; selector de tema; usuario y sede actuales |
| **Stepper / Timeline** | **Trazabilidad del remito**: línea de tiempo con `MovimientoRemito` (estado, fecha, responsable) |
| **StatCard** | Cifra + etiqueta para el tablero de reportes |

Componentes específicos del dominio (en `features/`, construidos sobre los core): `RemitoTimeline`, `EstadoBadge` (recibe entidad y estado, y aplica el mapeo de §3), `CondicionBadge` (vencido, retiro vencido, demorado, consulta en sala), `DisponibilidadPorSede`, `ColaReservas`.

### Layout
- Escritorio: sidebar fija (240 px) + área de contenido con ancho máximo de 1280 px.
- Móvil/tablet: sidebar colapsable; tablas con scroll horizontal contenido, nunca scroll de página.
- Breakpoints: `sm 640px`, `md 768px`, `lg 1024px`, `xl 1280px`.

### Íconos
Conjunto único y consistente (p. ej. Lucide), trazo de 1.5–2 px, tamaños 16/20/24 px. `[PENDIENTE-D3]`
