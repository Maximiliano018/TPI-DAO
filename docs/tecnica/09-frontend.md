# 09. Frontend

Aplicación web en **React 18 con JavaScript** (sin TypeScript), empaquetada con **Vite**. Consume la [API REST](06-api.md) y aplica la [guía de estilos](10-guia-de-estilos.md).

## Bibliotecas

| Necesidad | Biblioteca | Motivo |
|-----------|------------|--------|
| Rutas | React Router | Estándar; permite rutas protegidas por rol |
| Datos del servidor | TanStack Query | Caché, reintentos, recarga tras mutaciones y estados de carga sin escribir código a mano |
| Formularios | React Hook Form + Zod | Validación declarativa y mensajes por campo |
| Peticiones | `fetch` con un cliente propio mínimo | Evita una dependencia; un único lugar para token y errores |
| Estilos | CSS Modules + variables CSS (tokens) | Sin dependencia de una librería de UI; el design system es propio |
| Fechas | date-fns | Formato y cálculo livianos |
| Pruebas | Vitest, React Testing Library, MSW, jest-axe | Ver [Testing](07-testing-y-calidad.md) |

No se usa Redux: el estado del servidor lo maneja TanStack Query, la sesión un contexto y el resto es local a cada pantalla.

## Estructura

```
frontend/
├── src/
│   ├── main.jsx
│   ├── app/                 # providers, rutas, layout principal
│   ├── api/                 # cliente HTTP, manejo de token y de errores
│   ├── components/          # design system: Button, Input, Table, Badge, Modal...
│   ├── features/            # una carpeta por proceso
│   │   ├── sedes/           # páginas, componentes, hooks de datos
│   │   ├── socios/
│   │   ├── catalogo/
│   │   ├── prestamos/
│   │   ├── remitos/
│   │   ├── reservas/
│   │   ├── devoluciones/
│   │   └── reportes/
│   ├── auth/                # contexto de sesión, login, rutas protegidas
│   ├── hooks/               # hooks compartidos
│   ├── utils/               # formateo, constantes, mapas de estados
│   └── styles/              # tokens.css, base.css
├── tests/                   # utilidades de prueba y mocks de MSW
└── index.html
```

Se organiza **por funcionalidad** y no por tipo de archivo: todo lo de remitos vive junto, y los componentes genéricos del design system quedan aparte.

## Cliente de la API

- Un único módulo `api/client.js` agrega el encabezado `Authorization`, convierte las respuestas de error al formato `{ codigo, mensaje, detalles }` y lanza un `ApiError`.
- Una respuesta `401` cierra la sesión y lleva al login; un `403` muestra un aviso de permiso insuficiente.
- Un mapa `codigo → mensaje amigable` (`utils/errores.js`) traduce los códigos de negocio. Si el código no está, se muestra el `mensaje` que envía el backend.
- Los hooks de cada feature (`usePrestamos`, `useRemito`…) envuelven las consultas y mutaciones de TanStack Query; tras una acción de estado se invalida la caché relacionada (por ejemplo, despachar un remito recarga el remito, el préstamo y el ejemplar).

## Sesión y roles

- El token vive en memoria y en `sessionStorage`; se descarta al cerrar la pestaña. Se aceptó `sessionStorage` (y no solo memoria) para sobrevivir a una recarga, a costa de la exposición a XSS; se mitiga con la política de contenido y sin HTML inyectado.
- Al iniciar, si hay token guardado se llama a `GET /auth/me` para restaurar la sesión (con una pantalla de carga); si responde `401`, se descarta.
- `RutaProtegida` recibe los roles permitidos; las rutas y las opciones de menú se muestran según el rol.
- **El frontend no es la barrera de seguridad:** ocultar un botón mejora la experiencia, pero la autorización real está en el backend.

## Rutas

| Ruta | Pantalla | Acceso |
|------|----------|--------|
| `/login` | Inicio de sesión | Público (redirige a `/` si ya hay sesión) |
| `/` | Inicio (dashboard) | Autenticado |
| `/sedes` | Listado de sedes | A, B, S |
| `/sedes/nueva` | Alta de sede | A |
| `/sedes/:id` | Detalle (pestañas Datos, Horarios, Historial) | A, B, S |
| `/sedes/:id/editar` | Edición | A |
| `/usuarios` | Listado de usuarios del personal | A |
| `/usuarios/nuevo` | Alta de personal | A |
| `/usuarios/:id/editar` | Edición y reasignación de sede | A |
| `*` | No encontrado | Autenticado |

`RutaProtegida` redirige a `/login` guardando la ruta de origen (se vuelve a ella tras ingresar) y muestra «sin permiso» si el rol no alcanza. Las rutas se cargan con `React.lazy`.

## Layout base

Estructura de toda pantalla autenticada (`app/AppLayout.jsx`):

```
┌─────────────────────────────────────────────────────────────┐
│ AppBar:  ☰   Sistema de Préstamos      [Sede] [Usuario ▾]  │
├──────────────┬──────────────────────────────────────────────┤
│ Menú lateral │  Main: PageHeader (título, migas, acciones)  │
│  Inicio      │        contenido de la pantalla              │
│  Sedes       │                                              │
│  (más según  │                                              │
│   el rol)    │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

| Pieza | Comportamiento |
|-------|----------------|
| **AppBar** | Botón de menú (en pantallas chicas), nombre del sistema, **sede del bibliotecario** (el administrador muestra «Toda la red»), menú de usuario con nombre, rol y «Cerrar sesión» |
| **Menú lateral** | Elementos según rol y permisos (`/auth/me`). Resalta la ruta activa con `aria-current="page"`. Fijo desde 1024 px; por debajo es un panel que se abre y cierra con el botón y con Escape, y atrapa el foco |
| **Main** | Región `<main>` con salto de contenido, ancho máximo 1200 px y `PageHeader` |
| **Salir** | Descarta el token, limpia la caché de TanStack Query y lleva a `/login` |

Los ítems que todavía no tienen módulo (socios, catálogo, préstamos…) **no se muestran**: el menú crece con cada iteración.

## Inicio de sesión

- Campos usuario y contraseña (con mostrar u ocultar), botón «Ingresar» que se deshabilita mientras se procesa.
- Error `CREDENCIALES_INVALIDAS`: aviso general «Usuario o contraseña incorrectos» (no indica cuál). `422`: error por campo. Error de red: «No se pudo conectar. Reintente».
- Si la sesión vence (`401` en cualquier pantalla), se vuelve al login con el aviso «Su sesión venció. Ingrese de nuevo».
- Foco inicial en el usuario; `Enter` envía; el formulario es accesible por teclado.

## Inicio (dashboard) por rol

Se compone de tarjetas con los datos que ya expone la API; las tarjetas de procesos que no existen aún no se muestran.

| Rol | Contenido |
|-----|-----------|
| Administrador | Tarjetas **Sedes activas**, **Sedes en baja** y **Total** (`GET /sedes/resumen`); acceso directo a «Nueva sede» y a «Sedes»; lista de las sedes con el indicador «abierta ahora» |
| Bibliotecario | Tarjeta de **su sede** (nombre, dirección, contacto, horario de hoy, abierta ahora, excepciones próximas) con enlace al detalle; lista de las demás sedes de la red |
| Socio | Sedes activas con «abierta ahora», horario de hoy y contacto |

Cada tarjeta resuelve los estados de carga, vacío y error por separado: que falle una no rompe el resto.

## Módulo de sedes

### Listado (`/sedes`)

- **Filtros:** estado (Todas, Activas, En baja; el socio no lo ve), búsqueda por texto (con espera de 300 ms), localidad. Se reflejan en la URL (`?estado=ACTIVA&q=centro&page=2`) para poder compartir y volver con «atrás».
- **Tabla** (tarjetas bajo 768 px): código (monoespaciado), nombre, localidad, teléfono, estado (`Badge`), abierta ahora. Orden por columna (nombre, código). Paginación con tamaño de página.
- **Acciones por fila** según rol y estado: *Ver* (todos); *Editar* y *Dar de baja* (A, sede activa); *Reactivar* (A, sede en baja). Las acciones no válidas no aparecen.
- «Nueva sede» en el encabezado (A).
- Estados: cargando (esqueleto), vacío («No hay sedes que coincidan», con acción para limpiar filtros), error con reintento.

### Detalle (`/sedes/:id`)

- Encabezado con nombre, código, estado y las acciones permitidas.
- **Datos:** dirección, contacto y responsable (no para el socio). El administrador ve además un bloque de baja (fecha, motivo, quién) cuando corresponde.
- **Horarios:** semana de lunes a domingo, cada día con sus franjas o «Cerrado»; resalta hoy; lista de **excepciones** vigentes con motivo. El administrador puede **agregar** y **quitar** excepciones desde aquí (formulario en un `Modal`: fecha o rango, tipo de cierre, horas si es parcial, motivo opcional).
- **Historial** (solo A): línea de tiempo (`Timeline`) con tipo de evento, usuario, fecha y hora, motivo y los cambios «antes → después»; paginado y filtro por tipo.
- Un socio que abre una sede en baja ve «La sede solicitada no existe o no está disponible».

### Formulario de alta y edición

Una sola pantalla con secciones, validada con Zod y React Hook Form:

| Sección | Campos |
|---------|--------|
| Identificación | Código (solo en el alta; en la edición se muestra bloqueado con la ayuda «El código no se puede cambiar»), nombre |
| Domicilio | Calle, número, **localidad** (lista desplegable con búsqueda; la provincia se muestra como dato de solo lectura) |
| Contacto | Teléfono (ayuda con el formato `+54 351 …`; se normaliza al enviar), correo, responsable |
| Horarios | **Editor semanal**: una fila por día (lunes a domingo) con sus franjas (apertura y cierre); «Agregar franja», «Quitar», «Cerrado» (sin franjas) y «Copiar a otros días». Marca los solapamientos y los cierres anteriores a la apertura mientras se escribe |

- El código se muestra en mayúsculas mientras se escribe.
- En la edición, el formulario envía la `version` leída; si el servidor responde `CONFLICTO_DE_VERSION`, se muestra un diálogo «Otra persona modificó esta sede» con la acción **Recargar** (descarta los cambios y trae la versión nueva).
- Las excepciones **no** forman parte de este formulario: se gestionan en el detalle.
- Una sede en baja no puede abrirse en edición: la ruta redirige al detalle con el aviso «Reactive la sede para poder editarla».
- Los errores de campo del servidor (`detalles[].campo`) se muestran junto al campo y se enfoca el primero; los demás van en un `Alert` arriba.
- Al guardar con éxito: `Toast` «Sede guardada» y vuelta al detalle.

### Diálogos de confirmación y error

| Diálogo | Cuándo | Contenido y acciones |
|---------|--------|----------------------|
| **Dirección duplicada** | `409 DIRECCION_DUPLICADA` al guardar | Muestra la sede que ya está en esa dirección (con enlace). Acciones: **Volver y corregir** (cierra y deja el formulario) y **Guardar de todas formas** (reenvía con `confirmar_direccion_duplicada: true`) |
| **Dar de baja** | Acción «Dar de baja» | Describe el efecto («La sede dejará de operar. No se cancelan préstamos ni envíos: la baja se bloquea si hay actividad pendiente»). Campo **motivo** obligatorio (5 a 300 caracteres, con contador). Botón de peligro «Dar de baja» |
| **Baja bloqueada** | `409 SEDE_CON_ACTIVIDAD_PENDIENTE` | Muestra el mensaje del servidor y una **lista por tipo** con su cantidad y los primeros elementos («Préstamos en curso (2): P-2026-000118…»); si `hay_mas`, indica «y N más». No ofrece forzar la baja. Acción única: «Entendido» |
| **Reactivar** | Acción «Reactivar» | Confirmación con el efecto («La sede volverá a operar. Se conserva su historial»). No pide datos |
| **Conflicto de versión** | `409 CONFLICTO_DE_VERSION` | Ver arriba |
| **Error general** | Cualquier otro error de una mutación | `Alert` o `Toast` con el `mensaje` del servidor y, para códigos conocidos, el texto de `utils/errores.js` |

Todos son `Modal` accesibles: foco atrapado, Escape cierra (salvo mientras se procesa), el botón principal se deshabilita al enviar y el resultado se anuncia con `aria-live`.

### Tabla de códigos de error del módulo (`utils/errores.js`)

| Código | Mensaje al usuario |
|--------|--------------------|
| `SEDE_CODIGO_DUPLICADO` | Ya existe una sede con ese código |
| `SEDE_NOMBRE_DUPLICADO` | Ya existe una sede con ese nombre |
| `SEDE_EN_BAJA` | La sede está dada de baja. Reactívela para continuar |
| `SEDE_YA_EN_BAJA` / `SEDE_YA_ACTIVA` | La sede ya estaba en ese estado. Se actualizó la pantalla |
| `SEDE_NO_ENCONTRADA` | La sede solicitada no existe o no está disponible |
| `HORARIO_INVALIDO` | Revise los horarios: las franjas no pueden solaparse y el cierre debe ser posterior a la apertura |
| `EXCEPCION_HORARIO_SUPERPUESTA` | Ya hay un cierre cargado para esa fecha y horario |
| `EXCEPCION_HORARIO_INVALIDA` | Revise la fecha y las horas del cierre |
| `LOCALIDAD_INVALIDA` | Elija una localidad de la lista |
| `CONFLICTO_DE_VERSION` | Otra persona modificó la sede. Recargue para ver los cambios |

### Datos y caché

Hooks en `features/sedes/hooks/`: `useSedes(filtros)`, `useSede(id)`, `useCrearSede`, `useModificarSede`, `useBajaSede`, `useReactivarSede`, `useExcepciones(id)`, `useHistorialSede(id, filtros)`, `useLocalidades()`. Tras cualquier mutación se invalidan el listado, el detalle y el resumen. Las localidades se cachean por sesión (cambian muy rara vez).

Detalles de implementación:

- Las mutaciones (`useCrearSede`, `useModificarSede`, `useBajaSede`, `useReactivarSede`, `useAgregarExcepciones`, `useQuitarExcepcion`) están en `useSedesMutaciones.js` y refrescan la caché también cuando fallan, para que un conflicto («la sede ya estaba en ese estado») deje la pantalla con los datos vigentes.
- El detalle muestra los cierres de `sede.excepciones` (los vigentes que ya devuelve `GET /sedes/{id}`); `useExcepciones` queda para consultas que necesiten los cierres pasados.
- Los filtros del listado viven en la URL (`useFiltrosUrl`); el filtro de estado se omite de la URL cuando coincide con el valor por defecto del rol (Todas para el administrador, Activas para el bibliotecario).
- En la edición, la versión que se envía es la leída **al abrir** el formulario, aunque la caché se refresque por detrás: así un cambio ajeno se detecta (`CONFLICTO_DE_VERSION`) en lugar de pisarse. «Recargar» vuelve a leer la sede y reinicia el formulario.
- Componentes nuevos del design system: `FilterBar` (con `BusquedaConEspera` y `FiltroSelect`), `Combobox`, `Timeline` y `WeekScheduleEditor`; los campos de fecha y hora usan los controles nativos.

## Módulo de usuarios del personal

Acceso solo del administrador (`USUARIO_ADMINISTRAR`).

- **Listado (`/usuarios`):** filtros por rol, sede, estado (activos, dados de baja) y texto (nombre o usuario), reflejados en la URL; tabla paginada con usuario, nombre, rol, sede (o «Toda la red» para administradores) y estado. Acciones por fila: *Editar*, *Dar de baja* (usuario activo) y *Reactivar* (usuario dado de baja).
- **Alta (`/usuarios/nuevo`):** usuario, nombre, contraseña (con confirmación), rol (Administrador o Bibliotecario) y, si es bibliotecario, **sede** (solo se ofrecen sedes activas). Al elegir administrador, el campo sede desaparece.
- **Edición (`/usuarios/:id/editar`):** nombre y, para un bibliotecario, **reasignación de sede** (solo sedes activas). El usuario y el rol se muestran bloqueados. El texto aclara que el cambio rige desde la siguiente solicitud del usuario.
- **Baja:** confirmación que explica el efecto («Dejará de poder ingresar. Se conserva su historial. Si es bibliotecario, deja de contar como asignado a su sede»).
- **Reactivar:** confirmación; si la sede del bibliotecario está en baja, el servidor responde `SEDE_EN_BAJA` y se explica que debe reasignarse primero.
- **Desde la baja de sede:** en el diálogo de baja bloqueada, los impedimentos de tipo `BIBLIOTECARIOS_ASIGNADOS` enlazan a `/usuarios?sede_id=…&estado=activos`.
- Un administrador no puede darse de baja a sí mismo (el servidor responde `422 VALIDACION`).

Códigos propios del módulo: `DUPLICADO` («Ya existe un usuario con ese nombre de usuario») y `SEDE_EN_BAJA` (con el texto de sedes).

Detalles de implementación:

- El filtro de estado de la URL usa `estado=activos` o `estado=baja` (así lo arma el enlace de la baja de sede); la pantalla lo traduce a `activo=true|false` de la API.
- Los formularios cargan primero las sedes activas y recién entonces se muestran: un `<select>` nativo no puede reflejar una sede precargada si todavía no existen sus opciones.
- Se puede editar a un usuario dado de baja: sirve para reasignarlo a una sede activa cuando la anterior está en baja y poder reactivarlo. Si su sede actual no figura entre las activas, el campo queda vacío con un aviso y debe elegirse otra.
- La confirmación de contraseña solo se valida en la pantalla; no se envía a la API.
- Las mutaciones (`useCrearUsuario`, `useModificarUsuario`, `useBajaUsuario`, `useReactivarUsuario`) refrescan listado y detalle aunque fallen. Al reactivar con `SEDE_EN_BAJA` el diálogo enlaza a la edición del usuario.

## Pruebas del frontend

- Cada pantalla con MSW: listado con filtros y paginación, formulario (validaciones, errores del servidor, advertencia de dirección duplicada, conflicto de versión), baja bloqueada y baja correcta, reactivación y vistas por rol (administrador, bibliotecario, socio).
- Cada componente base y cada pantalla con una comprobación de `jest-axe`.
- Lo que se verifica es lo que el usuario ve: textos, roles ARIA y resultados de interacción con `user-event`.

## Pantallas por rol

| Pantalla | Administrador | Bibliotecario | Socio |
|----------|:---:|:---:|:---:|
| Inicio con indicadores (vencidos, remitos abiertos, reservas por retirar) | ✔ | ✔ (su sede) | resumen propio |
| Sedes: listado, alta, edición, baja | ✔ | consulta | consulta |
| Socios: búsqueda, alta, ficha, inhabilitación | ✔ | ✔ | su ficha |
| Catálogo: libros y disponibilidad por sede | ✔ | ✔ | ✔ |
| Ejemplares: alta, estado, baja, historial | ✔ | ✔ (su sede) | |
| Préstamos: registrar, detalle con historial y remito, entregar, renovar, cancelar | consulta | ✔ | los propios |
| Devolución: registro con estado físico y resultado (multa, retorno) | consulta | ✔ | |
| Remitos: listado, generar, empaquetar, despachar, recibir, anular | consulta | ✔ | estado del propio |
| Reservas: reservar, cola, cancelar, retirar | consulta | ✔ | ✔ |
| Multas: listado y saldar | ✔ | ✔ | las propias |
| Reportes R1 a R6 | ✔ | R1, R4, R5, R6 | R5 |
| Usuarios y parámetros | ✔ | | |

### Flujos que merecen diseño propio

1. **Registrar un préstamo.** Buscar socio → buscar libro → elegir ejemplar (mostrando disponibilidad por sede) → el sistema indica si es local o interbibliotecario → confirmar. Si el socio está inhabilitado se informa antes de avanzar.
2. **Detalle de remito.** Línea de tiempo con cada movimiento (estado, fecha y hora, responsable) y botones que aparecen solo para las acciones válidas en ese estado y para el rol y la sede del usuario.
3. **Recepción de remito.** Lista de ejemplares con estado físico por línea y observación obligatoria si hay daño.
4. **Devolución.** Resume el resultado: días de atraso, multa, remito de retorno y cambios en el socio.
5. **Baja de sede.** Si el backend responde `SEDE_CON_ACTIVIDAD_PENDIENTE`, muestra la lista de elementos que lo impiden con enlace a cada uno.

## Estados de carga, vacío y error

Toda pantalla de datos resuelve los cuatro estados: **cargando** (esqueleto o indicador), **vacío** (mensaje con la acción siguiente), **error** (mensaje con reintento) y **con datos**. Las mutaciones muestran el resultado con una notificación y errores de campo en el propio formulario.

## Formularios

- Validación en el cliente de formato y obligatoriedad con Zod; las reglas de negocio las decide el backend y sus errores se muestran junto al campo (`detalles[].campo`) o en un aviso general.
- Botón de envío deshabilitado mientras se procesa, para evitar duplicados.
- Acciones destructivas o irreversibles (baja, anulación, extravío) piden confirmación con el efecto descrito en una frase.

## Accesibilidad

- HTML semántico, etiquetas asociadas a cada campo, mensajes de error anunciados (`aria-live`) y navegación completa por teclado.
- Foco visible y orden lógico; los modales atrapan el foco y se cierran con Escape.
- Contraste mínimo AA verificado en la [guía de estilos](10-guia-de-estilos.md); el estado nunca se indica solo con color (siempre hay texto).
- Pruebas automáticas con jest-axe y revisión manual con teclado.

## Diseño adaptable

Mobile first con puntos de corte 640, 768, 1024 y 1280 px. Las tablas se convierten en tarjetas bajo 768 px. El personal usa sobre todo escritorio; el socio, también teléfono.

## Internacionalización

Interfaz en español (Argentina). Los textos se centralizan en un archivo de mensajes para facilitar el mantenimiento; fechas en formato `dd/mm/aaaa` y montos en pesos (`$ 1.000,00`) con `Intl`.
