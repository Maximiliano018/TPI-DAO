# 06. API REST

Contrato de la API del backend. La especificación completa e interactiva se genera automáticamente con FastAPI (OpenAPI) y queda disponible en `/docs` (Swagger UI) y `/openapi.json`. Este documento fija las convenciones y los endpoints antes de implementarlos; los esquemas Pydantic deben incluir `examples` que coincidan con los ejemplos de acá.

## Convenciones

| Tema | Regla |
|------|-------|
| Base | `/api/v1` |
| Formato | JSON, codificación UTF-8 |
| Nombres | Recursos en plural y en español (`/sedes`, `/prestamos`), `snake_case` en los campos |
| Fechas | ISO 8601: fecha `2026-10-14`, fecha y hora en UTC `2026-10-14T15:30:00Z` |
| Dinero | Cadena decimal (`"1000.00"`) para no perder precisión |
| Identificadores | Enteros |
| Autenticación | `Authorization: Bearer <token>` en todo salvo el login |
| Paginación | `?page=1&size=20` (máximo 100). Respuesta `{ "items": [...], "total": 125, "page": 1, "size": 20 }` |
| Filtros y orden | Parámetros de consulta (`?estado=ACTIVA&q=centro&orden=nombre`) |
| Acciones de estado | `POST /recursos/{id}/accion` (por ejemplo `/remitos/7/despachar`); nunca se edita el estado con `PATCH` |
| Idempotencia | Las acciones repetidas sobre un estado ya alcanzado devuelven `409 TRANSICION_INVALIDA` |
| Versionado | Prefijo `/v1`; los cambios incompatibles van a `/v2` |

### Códigos HTTP

| Código | Uso |
|--------|-----|
| 200 | Consulta o acción correcta |
| 201 | Recurso creado (con encabezado `Location`) |
| 204 | Sin contenido (bajas lógicas que no devuelven recurso) |
| 400 | Solicitud mal formada |
| 401 | Falta autenticación o el token es inválido |
| 403 | Autenticado pero sin permiso para la acción o la sede |
| 404 | El recurso no existe o no es visible para ese usuario |
| 409 | Conflicto con una regla de negocio o con el estado actual |
| 422 | Datos con forma válida pero inválidos (validación de campos) |

### Errores

Todas las respuestas de error usan el mismo cuerpo:

```json
{
  "error": {
    "codigo": "SOCIO_INHABILITADO",
    "mensaje": "El socio 00045 está inhabilitado por préstamo vencido.",
    "detalles": [{ "campo": "socio_id", "problema": "inhabilitado" }]
  }
}
```

`codigo` es estable y lo usa el frontend para decidir qué mostrar; `mensaje` está en español y es legible por una persona. La lista de códigos está en [Arquitectura](01-arquitectura-backend.md#errores).

## Autenticación

### `POST /auth/login`

Roles: público.

Request:

```json
{ "username": "mlopez", "password": "••••••••" }
```

Response `200`:

```json
{
  "access_token": "<token-jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "usuario": { "id": 4, "nombre": "María López", "rol": "BIBLIOTECARIO", "sede_id": 2 }
}
```

Errores: `401 CREDENCIALES_INVALIDAS` (sin indicar cuál dato falló).

### `GET /auth/me`

Roles: todos. Devuelve el usuario autenticado.

## Resumen de endpoints

`A` = Administrador, `B` = Bibliotecario (en su sede salvo que se indique), `S` = Socio (solo lo propio).

### Sedes

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /sedes` | A | Alta de sede | RF-SED-01 |
| `GET /sedes` | A, B, S | Listado; `?estado=` | RF-SED-08 |
| `GET /sedes/{id}` | A, B, S | Detalle | RF-SED-08 |
| `PUT /sedes/{id}` | A | Modificar | RF-SED-02 |
| `POST /sedes/{id}/baja` | A | Baja con motivo | RF-SED-03, 04 |
| `POST /sedes/{id}/reactivar` | A | Reactivar | RF-SED-03 |

### Socios

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /socios` | A, B | Alta | RF-SOC-01, 02 |
| `GET /socios` | A, B | Búsqueda; `?q=`, `?documento=`, `?estado=` | RF-SOC-04 |
| `GET /socios/{id}` | A, B, S | Detalle y situación | RF-SOC-10 |
| `PUT /socios/{id}` | A, B | Modificar | RF-SOC-03 |
| `PUT /socios/{id}/sede` | A, B, S | Cambiar la sede del socio (el socio, solo la propia) | RF-SOC-11 |
| `POST /socios/{id}/inhabilitar` | A | Inhabilitación administrativa | RF-SOC-06 |
| `POST /socios/{id}/rehabilitar` | A, B | Rehabilita si no hay causas vigentes | RF-SOC-05, 06 |
| `POST /socios/{id}/baja` | A | Baja lógica | RF-SOC-09 |
| `POST /socios/{id}/reactivar` | A | Reactivar | RF-SOC-09 |

### Catálogo

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /libros` | A | Alta de libro | RF-CAT-01, 02 |
| `GET /libros` | A, B, S | Búsqueda; `?q=`, `?isbn=`, `?categoria_id=` | RF-CAT-09 |
| `GET /libros/{id}` | A, B, S | Detalle | RF-CAT-09 |
| `PUT /libros/{id}` | A | Modificar | RF-CAT-01 |
| `GET /libros/{id}/disponibilidad` | A, B, S | Disponibilidad por sede | RF-CAT-09, 10 |
| `POST /ejemplares` | A, B | Alta de ejemplar | RF-CAT-03, 04 |
| `GET /ejemplares` | A, B | Listado; `?sede_id=`, `?estado=`, `?libro_id=` | RF-CAT-04 |
| `GET /ejemplares/{id}` | A, B | Detalle e historial | RF-CAT-06 |
| `PUT /ejemplares/{id}` | A, B | Modificar estado físico u observaciones | RF-CAT-04 |
| `POST /ejemplares/{id}/baja` | A, B | Baja lógica con motivo | RF-CAT-07 |
| `POST /ejemplares/{id}/reparado` | A, B | Sale de revisión y queda disponible | RF-DEV-10 |

### Préstamos

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /prestamos/previsualizar` | B, S | Simula la determinación (tipo, sede origen, plazo) sin registrar ni apartar | RF-PRE-16, 17 |
| `POST /prestamos` | B, S | Registrar solicitud; el sistema determina el tipo. El socio, solo interbibliotecarios propios | RF-PRE-01 a 08, 16 a 19 |
| `GET /prestamos` | A, B, S | Listado; `?estado=`, `?tipo=`, `?socio_id=` | RF-PRE-15 |
| `GET /prestamos/{id}` | A, B, S | Detalle, historial y remito | RF-PRE-15 |
| `POST /prestamos/{id}/entregar` | B | Entrega al socio; inicia el plazo | RF-PRE-09 |
| `POST /prestamos/{id}/renovar` | B | Renovación | RF-PRE-14 |
| `POST /prestamos/{id}/cancelar` | B | Cancelar antes de la entrega | RF-PRE-13 |
| `POST /prestamos/{id}/devolucion` | B | Registrar devolución | RF-DEV-01 a 11 |
| `POST /admin/tareas/detectar-vencidos` | A | Ejecuta la detección de vencidos (también corre sola cada día) | RF-PRE-12 |

### Remitos

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /remitos` | B (sede origen) | Generar remito | RF-REM-01 a 04, 10 |
| `GET /remitos` | A, B, S | Listado; `?estado=`, `?sede_id=` | RF-REM-14 |
| `GET /remitos/{id}` | A, B, S | Detalle y movimientos | RF-REM-14 |
| `POST /remitos/{id}/empaquetar` | B (sede origen) | | RF-REM-05, 07 |
| `POST /remitos/{id}/despachar` | B (sede origen) | | RF-REM-08 |
| `POST /remitos/{id}/recibir` | B (sede destino) | Recepción con estado por línea | RF-REM-09, 13 |
| `POST /remitos/{id}/anular` | B (sede origen) | Antes del despacho | RF-REM-11 |
| `POST /remitos/{id}/extraviado` | A, B | Si venció el plazo de tránsito | RF-REM-12 |

### Reservas

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /reservas` | B, S | Reservar un libro | RF-RES-01 a 05 |
| `GET /reservas` | A, B, S | Listado; `?libro_id=`, `?estado=` | RF-RES-12 |
| `GET /reservas/{id}` | A, B, S | Detalle y posición en la cola | RF-RES-12 |
| `POST /reservas/{id}/cancelar` | B, S | | RF-RES-10 |
| `POST /reservas/{id}/retirar` | B | Entrega y crea el préstamo | RF-RES-11 |

### Multas

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `GET /multas` | A, B, S | Listado; `?socio_id=`, `?estado=` | RF-DEV-13 |
| `POST /multas/{id}/saldar` | A, B | Marca como saldada | RF-DEV-06 |

### Reportes

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `GET /reportes/movimiento-entre-sedes` | A, B | R1 | RF-REP-01 |
| `GET /reportes/envios-e-incidencias` | A | R2 | RF-REP-02 |
| `GET /reportes/libros-mas-solicitados` | A | R3 | RF-REP-03 |
| `GET /reportes/vencidos-y-multas` | A, B | R4 | RF-REP-04 |
| `GET /reportes/disponibilidad-por-sede` | A, B, S | R5 | RF-REP-05 |
| `GET /reportes/prestamos-activos-y-en-transito` | A, B | R6 | RF-REP-06 |

Todos aceptan `?desde=`, `?hasta=` y `?sede_id=` donde corresponda; un bibliotecario queda limitado a su sede. Con `Accept: text/csv` exportan CSV (opcional, RF-REP-10).

### Usuarios y parámetros

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /usuarios`, `GET /usuarios`, `PUT /usuarios/{id}`, `POST /usuarios/{id}/baja` | A | Usuarios del personal | RF-ACC-06 |
| `GET /parametros`, `PUT /parametros/{clave}` | A | Parámetros de negocio | — |

---

## Ejemplos de request y response

### `POST /sedes` — alta de sede

Request:

```json
{
  "codigo": "NORTE",
  "nombre": "Biblioteca Norte",
  "direccion": { "calle": "Av. Colón", "numero": "4500", "localidad": "Córdoba", "provincia": "Córdoba" },
  "contacto": { "telefono": "351-4000000", "email": "norte@red.example", "responsable": "Ana Pérez" },
  "horarios": [
    { "dia_semana": 1, "hora_apertura": "09:00", "hora_cierre": "18:00" },
    { "dia_semana": 2, "hora_apertura": "09:00", "hora_cierre": "18:00" }
  ]
}
```

Response `201` (`Location: /api/v1/sedes/3`):

```json
{ "id": 3, "codigo": "NORTE", "nombre": "Biblioteca Norte", "estado": "ACTIVA" }
```

Errores: `409 DUPLICADO` (código o nombre repetido), `422 HORARIO_INVALIDO`.

### `POST /sedes/{id}/baja` — baja de sede

Request: `{ "motivo": "Cierre por obras" }`

Response `200`: `{ "id": 3, "estado": "BAJA", "fecha_baja": "2026-10-14T15:30:00Z" }`

Error `409 SEDE_CON_ACTIVIDAD_PENDIENTE`:

```json
{
  "error": {
    "codigo": "SEDE_CON_ACTIVIDAD_PENDIENTE",
    "mensaje": "La sede tiene actividad pendiente y no puede darse de baja.",
    "detalles": [
      { "tipo": "prestamo", "id": 118, "estado": "ACTIVO" },
      { "tipo": "remito", "id": 44, "estado": "EN_TRANSITO" },
      { "tipo": "reserva", "id": 9, "estado": "PENDIENTE" }
    ]
  }
}
```

### `POST /socios` — alta de socio

Request:

```json
{
  "tipo_documento": "DNI",
  "nro_documento": "30111222",
  "nombre": "Lucía",
  "apellido": "Gómez",
  "fecha_nacimiento": "1995-04-12",
  "email": "lucia@example.com",
  "telefono": "351-5000000",
  "domicilio": "San Martín 123"
}
```

Response `201`:

```json
{ "id": 45, "numero_socio": "00045", "estado": "HABILITADO", "sede_alta_id": 2, "sede_id": 2 }
```

`sede_id` (sede del socio) se inicializa con la sede de alta. La modifican el personal o el propio socio con `PUT /socios/{id}/sede` (`{ "sede_id": 3 }`; debe ser una sede activa).

Errores: `409 DUPLICADO` (devuelve el socio existente en `detalles`; si estaba dado de baja, indica que puede reactivarse).

### `POST /libros` y `POST /ejemplares`

Request de libro:

```json
{
  "isbn": "9780132350884",
  "titulo": "Clean Code",
  "autores": ["Robert C. Martin"],
  "editorial": "Prentice Hall",
  "anio_edicion": 2008,
  "categoria_id": 7,
  "tipo_material": "LIBRO"
}
```

Response `201`: `{ "id": 12, "isbn": "9780132350884", "titulo": "Clean Code" }`

Request de ejemplar (la sede propietaria es la del bibliotecario; el administrador la indica):

```json
{ "libro_id": 12, "codigo_inventario": "CEN-000123", "estado_fisico": "BUENO" }
```

Response `201`:

```json
{ "id": 301, "codigo_inventario": "CEN-000123", "sede_propietaria_id": 2, "estado": "DISPONIBLE" }
```

### `GET /libros/{id}/disponibilidad`

Response `200`:

```json
{
  "libro_id": 12,
  "titulo": "Clean Code",
  "total_red": { "totales": 5, "disponibles": 2 },
  "por_sede": [
    { "sede_id": 1, "sede": "Central", "totales": 3, "disponibles": 1, "prestados": 1, "reservados": 0, "en_transito": 1 },
    { "sede_id": 2, "sede": "Norte", "totales": 2, "disponibles": 1, "prestados": 1, "reservados": 0, "en_transito": 0 }
  ]
}
```

### `POST /prestamos` — solicitud de préstamo

Request: el usuario indica el libro, no el ejemplar ni el tipo.

```json
{ "socio_id": 45, "libro_id": 12, "sede_destino_id": 2 }
```

- **Bibliotecario:** `sede_destino_id` se ignora; se usa la sede de su usuario.
- **Socio:** omite `socio_id`, que se toma de su sesión. `sede_destino_id` es opcional y, si no se envía, se usa la sede del socio.

El sistema asigna el ejemplar. Si hay disponibles en la sede destino, el préstamo es local. Si no, el origen es la sede activa con más disponibles, y con empate la de menor id. En este ejemplo no hay disponibles en la sede 2 y sí en la 1:

Response `201`:

```json
{
  "id": 118,
  "numero": "P-2026-000118",
  "tipo": "INTERBIBLIOTECARIO",
  "estado": "SOLICITADO",
  "socio_id": 45,
  "ejemplar_id": 301,
  "sede_origen_id": 1,
  "sede_destino_id": 2,
  "fecha_solicitud": "2026-10-14T15:30:00Z",
  "fecha_vencimiento": null
}
```

Errores posibles: `409 SOCIO_INHABILITADO`, `409 SEDE_EN_BAJA`, `409 LIMITE_PRESTAMOS`, `409 SIN_DISPONIBILIDAD`, `409 CORRESPONDE_PRESTAMO_LOCAL` (solo socio), `403 FORBIDDEN` (socio que pide a nombre de otro, o administrador).

Para un préstamo local, `sede_origen_id` coincide con `sede_destino_id` y el préstamo nace sin remito.

`409 SIN_DISPONIBILIDAD` incluye en `detalles` la oferta de reserva para que el frontend la presente:

```json
{
  "error": {
    "codigo": "SIN_DISPONIBILIDAD",
    "mensaje": "No hay ejemplares disponibles del libro en ninguna sede activa.",
    "detalles": [{ "accion_sugerida": "RESERVAR", "libro_id": 12, "sede_retiro_id": 2 }]
  }
}
```

`409 CORRESPONDE_PRESTAMO_LOCAL`:

```json
{
  "error": {
    "codigo": "CORRESPONDE_PRESTAMO_LOCAL",
    "mensaje": "Hay ejemplares disponibles en la sede Norte. Acercate al mostrador para solicitar el préstamo.",
    "detalles": [{ "sede_id": 2, "sede": "Norte" }]
  }
}
```

### `POST /prestamos/previsualizar`

Mismo request que `POST /prestamos`. No registra el préstamo ni aparta el ejemplar; sirve para mostrar el resumen antes de confirmar. Devuelve los mismos errores de validación.

Response `200`:

```json
{ "tipo": "INTERBIBLIOTECARIO", "sede_origen_id": 1, "sede_destino_id": 2, "plazo_dias": 21 }
```

La asignación definitiva ocurre en `POST /prestamos`. Si cambió la disponibilidad entre la vista previa y la confirmación, la respuesta refleja el tipo y la sede origen vigentes.

### `POST /prestamos/{id}/entregar`

Request: sin cuerpo. Response `200`:

```json
{ "id": 118, "estado": "ACTIVO", "fecha_inicio": "2026-10-20", "fecha_vencimiento": "2026-11-10" }
```

### `POST /prestamos/{id}/devolucion`

Request:

```json
{ "estado_fisico": "BUENO", "observaciones": "Sin daños" }
```

Response `201`:

```json
{
  "prestamo": { "id": 118, "estado": "DEVUELTO" },
  "devolucion": { "id": 60, "dias_atraso": 5, "estado_fisico_recibido": "BUENO" },
  "multa": { "id": 14, "dias_atraso": 5, "monto_por_dia": "200.00", "monto_total": "1000.00", "estado": "PENDIENTE" },
  "remito_retorno": { "id": 52, "estado": "GENERADO" },
  "socio": { "id": 45, "estado": "INHABILITADO", "motivo": "MULTA_IMPAGA" }
}
```

`multa` y `remito_retorno` son `null` cuando no corresponden (devolución en término o préstamo local). Errores: `409 TRANSICION_INVALIDA` (préstamo ya devuelto), `403 FORBIDDEN` (sede distinta de la de destino), `422` (fecha o estado físico inválidos).

### `POST /remitos` — generar remito

Request:

```json
{
  "sede_origen_id": 1,
  "sede_destino_id": 2,
  "motivo": "ENVIO",
  "lineas": [
    { "ejemplar_id": 301, "prestamo_id": 118 },
    { "ejemplar_id": 305, "prestamo_id": 120 }
  ]
}
```

Response `201`:

```json
{
  "id": 51,
  "numero": "R-2026-000051",
  "estado": "GENERADO",
  "sede_origen_id": 1,
  "sede_destino_id": 2,
  "lineas": [
    { "ejemplar_id": 301, "prestamo_id": 118 },
    { "ejemplar_id": 305, "prestamo_id": 120 }
  ]
}
```

Errores: `409 SEDE_EN_BAJA`, `422 EJEMPLAR_FUERA_DE_SEDE_ORIGEN`, `409 EJEMPLAR_EN_OTRO_REMITO`.

### `POST /remitos/{id}/despachar`

Request: sin cuerpo. Response `200`: `{ "id": 51, "estado": "DESPACHADO", "fecha_despacho": "2026-10-15T12:00:00Z" }`

Error `409 TRANSICION_INVALIDA` si el remito sigue en `GENERADO`:

```json
{ "error": { "codigo": "TRANSICION_INVALIDA", "mensaje": "No se puede despachar un remito en estado GENERADO.", "detalles": [] } }
```

### `POST /remitos/{id}/recibir`

Request (estado por línea):

```json
{
  "lineas": [
    { "ejemplar_id": 301, "estado_fisico": "BUENO" },
    { "ejemplar_id": 305, "estado_fisico": "DANADO", "observacion": "Tapa rota" }
  ]
}
```

Response `200`: `{ "id": 51, "estado": "RECIBIDO", "incidencias": [{ "ejemplar_id": 305, "tipo": "DANIO" }] }`

### `GET /remitos/{id}` — con trazabilidad

Response `200`:

```json
{
  "id": 51,
  "numero": "R-2026-000051",
  "estado": "RECIBIDO",
  "movimientos": [
    { "estado_anterior": null, "estado_nuevo": "GENERADO", "fecha_hora": "2026-10-14T16:00:00Z", "usuario": "mlopez" },
    { "estado_anterior": "GENERADO", "estado_nuevo": "EMPAQUETADO", "fecha_hora": "2026-10-15T11:00:00Z", "usuario": "mlopez" },
    { "estado_anterior": "EMPAQUETADO", "estado_nuevo": "DESPACHADO", "fecha_hora": "2026-10-15T12:00:00Z", "usuario": "mlopez" },
    { "estado_anterior": "DESPACHADO", "estado_nuevo": "EN_TRANSITO", "fecha_hora": "2026-10-15T12:00:00Z", "usuario": "mlopez" },
    { "estado_anterior": "EN_TRANSITO", "estado_nuevo": "RECIBIDO", "fecha_hora": "2026-10-17T14:30:00Z", "usuario": "jperez" }
  ]
}
```

### `POST /reservas`

Request: `{ "libro_id": 12, "sede_retiro_id": 2, "socio_id": 45 }` (el socio omite `socio_id`; se toma de su sesión). `sede_retiro_id` es opcional: si se omite, se usa la sede del socio (cuando reserva el socio) o la sede del usuario (cuando reserva el bibliotecario). Ambos pueden enviar otra sede activa.

Response `201`: `{ "id": 9, "numero": "RS-2026-000009", "estado": "PENDIENTE", "posicion_en_cola": 3 }`

Errores: `409 HAY_EJEMPLARES_DISPONIBLES`, `409 SOCIO_INHABILITADO`, `409 SEDE_EN_BAJA`, `409 RESERVA_DUPLICADA`, `409 LIMITE_RESERVAS`.

### `GET /reportes/movimiento-entre-sedes` (R1)

Request: `?desde=2026-09-01&hasta=2026-09-30`

Response `200`:

```json
{
  "desde": "2026-09-01",
  "hasta": "2026-09-30",
  "rutas": [
    {
      "sede_origen": "Central",
      "sede_destino": "Norte",
      "envios": 8,
      "ejemplares": 11,
      "tiempo_promedio_transito_dias": 2.4
    }
  ]
}
```

### `GET /reportes/envios-e-incidencias` (R2)

Response `200`:

```json
{
  "total_envios": 10,
  "recibidos": 8,
  "extraviados": 1,
  "danados": 1,
  "destruidos": 0,
  "tasa_exito": 0.8
}
```

## Documentación de endpoints en el código

Cada endpoint de FastAPI debe declarar, además de la ruta:

- `summary` y `description` en español,
- `response_model` con el esquema de salida,
- `responses={...}` con los errores posibles (409, 403, 404…) y su esquema,
- `examples` en los esquemas Pydantic de entrada y salida,
- `tags` por recurso.

Así `/docs` queda completo y un test verifica que ningún endpoint carezca de descripción ni de modelo de respuesta (ver [Testing](07-testing-y-calidad.md)).
