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

- El token vive en memoria y en `sessionStorage`; se descarta al cerrar la pestaña.
- `RutaProtegida` recibe los roles permitidos; las rutas y las opciones de menú se muestran según el rol.
- **El frontend no es la barrera de seguridad:** ocultar un botón mejora la experiencia, pero la autorización real está en el backend.

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
