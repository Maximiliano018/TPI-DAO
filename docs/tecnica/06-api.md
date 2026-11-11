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
| Idempotencia | Las acciones repetidas sobre un estado ya alcanzado devuelven `409 TRANSICION_INVALIDA` (o el código específico del recurso: `SEDE_YA_EN_BAJA`, `SEDE_YA_ACTIVA`) |
| Concurrencia | Los recursos con `version` exigen enviarla al modificar y devuelven `409 CONFLICTO_DE_VERSION` si quedó desactualizada |
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

`username` no distingue mayúsculas. `expires_in` está en segundos (60 minutos).

Errores: `401 CREDENCIALES_INVALIDAS` (sin indicar cuál dato falló; también si el usuario está dado de baja), `422 VALIDACION` si falta un campo.

### `GET /auth/me`

Roles: todos. Devuelve el usuario autenticado con el mismo formato que `usuario` del login, más `permisos` (lista de strings) para que el frontend decida qué mostrar:

```json
{ "id": 4, "nombre": "María López", "rol": "BIBLIOTECARIO", "sede_id": 2,
  "sede": { "id": 2, "codigo": "NORTE", "nombre": "Sede Norte" },
  "permisos": ["SEDE_LEER_BASICO"] }
```

Errores: `401 TOKEN_INVALIDO` (vencido, manipulado o de un usuario dado de baja). Cerrar sesión no tiene endpoint: el cliente descarta el token.

## Resumen de endpoints

`A` = Administrador, `B` = Bibliotecario (en su sede salvo que se indique), `S` = Socio (solo lo propio).

### Sedes

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /sedes` | A | Alta de sede | RF-SED-01, 06, 07, 11, 12 |
| `GET /sedes` | A, B, S | Listado paginado; `?estado=ACTIVA\|BAJA\|TODAS`, `?q=`, `?localidad_id=`, `?orden=` | RF-SED-08 |
| `GET /sedes/resumen` | A | Cantidad de sedes por estado (inicio del administrador) | RF-SED-08 |
| `GET /sedes/{id}` | A, B, S | Detalle (campos según rol) | RF-SED-08 |
| `PUT /sedes/{id}` | A | Modificar (reemplaza datos y horarios) | RF-SED-02, 06, 07, 13 |
| `POST /sedes/{id}/baja` | A | Baja con motivo | RF-SED-03, 04, 13 |
| `POST /sedes/{id}/reactivar` | A | Reactivar | RF-SED-03, 13 |
| `GET /sedes/{id}/excepciones-horario` | A, B, S | Excepciones vigentes (A: `?incluir_pasadas=true`) | RF-SED-09 |
| `POST /sedes/{id}/excepciones-horario` | A | Alta de cierre por fecha o rango | RF-SED-09 |
| `DELETE /sedes/{id}/excepciones-horario/{excepcion_id}` | A | Quitar un cierre de hoy o futuro | RF-SED-09 |
| `GET /sedes/{id}/historial` | A | Historial de eventos; `?tipo_evento=`, `?desde=`, `?hasta=` | RF-SED-10 |
| `GET /provincias` | A, B, S | Catálogo cerrado de provincias | RF-SED-11 |
| `GET /localidades` | A, B, S | Catálogo cerrado; `?provincia_id=`, `?q=` | RF-SED-11 |

### Socios

| Método y ruta | Roles | Descripción | RF |
|---------------|-------|-------------|----|
| `POST /socios` | A, B | Alta | RF-SOC-01, 02 |
| `GET /socios` | A, B | Búsqueda; `?q=`, `?documento=`, `?estado=` | RF-SOC-04 |
| `GET /socios/{id}` | A, B, S | Detalle y situación | RF-SOC-10 |
| `PUT /socios/{id}` | A, B | Modificar | RF-SOC-03 |
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
| `POST /prestamos` | B | Registrar solicitud (local o interbibliotecario) | RF-PRE-01 a 08 |
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
| `POST /usuarios` | A | Alta de personal (`ADMIN` o `BIBLIOTECARIO`; el bibliotecario exige `sede_id` de una sede activa) | RF-ACC-02, 06, 09 |
| `GET /usuarios` | A | Listado paginado; `?rol=`, `?sede_id=`, `?activo=`, `?q=` | RF-ACC-06 |
| `GET /usuarios/{id}` | A | Detalle | RF-ACC-06 |
| `PUT /usuarios/{id}` | A | Modificar nombre y, si es bibliotecario, **reasignar a otra sede activa**. El rol no se cambia | RF-ACC-06, 09 |
| `POST /usuarios/{id}/baja` | A | Baja lógica (desvincula al bibliotecario de su sede) | RF-ACC-06, 09 |
| `POST /usuarios/{id}/reactivar` | A | Reactivar; rechaza si su sede está en baja | RF-ACC-06, 09 |
| `GET /parametros`, `PUT /parametros/{clave}` | A | Parámetros de negocio | — |

---

## Ejemplos de request y response

### Sedes: formas de respuesta según el rol

`GET /sedes/{id}` devuelve un esquema distinto según el permiso de lectura del usuario. Los campos no autorizados no se serializan.

| Campo | Administrador | Bibliotecario | Socio |
|-------|:---:|:---:|:---:|
| `id`, `codigo`, `nombre` | ✔ | ✔ | ✔ |
| `direccion` (`calle`, `numero`, `localidad`, `provincia`) | ✔ | ✔ | ✔ |
| `contacto.telefono`, `contacto.email` | ✔ | ✔ | ✔ |
| `contacto.responsable` | ✔ | ✔ | — |
| `horarios`, `excepciones` (vigentes), `abierta_ahora` | ✔ | ✔ | ✔ |
| `estado` | ✔ | ✔ | — |
| `baja` (`fecha`, `motivo`, `usuario`) | ✔ | — | — |
| `version`, `creado_en/por`, `actualizado_en/por` | ✔ | — | — |

Respuesta de administrador:

```json
{
  "id": 3,
  "codigo": "NORTE",
  "nombre": "Sede Norte",
  "estado": "ACTIVA",
  "direccion": { "calle": "Av. Colón", "numero": "4500", "localidad_id": 1,
                 "localidad": "Córdoba", "provincia": "Córdoba" },
  "contacto": { "telefono": "+543514000000", "email": "norte@red.example", "responsable": "Ana Pérez" },
  "horarios": [
    { "dia_semana": 1, "apertura": "09:00", "cierre": "13:00" },
    { "dia_semana": 1, "apertura": "15:00", "cierre": "19:00" }
  ],
  "excepciones": [ { "id": 12, "fecha": "2026-12-25", "tipo": "CIERRE_TOTAL", "motivo": "Feriado" } ],
  "abierta_ahora": true,
  "baja": null,
  "version": 4,
  "creado_en": "2026-10-14T15:30:00Z", "creado_por": { "id": 1, "nombre": "Admin" },
  "actualizado_en": "2026-11-02T12:00:00Z", "actualizado_por": { "id": 1, "nombre": "Admin" }
}
```

La respuesta del bibliotecario omite `baja`, `version` y auditoría; la del socio omite además `contacto.responsable` y `estado`. Un socio que pide una sede en `Baja` recibe `404 SEDE_NO_ENCONTRADA` con el mensaje «La sede solicitada no existe o no está disponible».

### `POST /sedes` — alta de sede

Request:

```json
{
  "codigo": "norte",
  "nombre": "Sede Norte",
  "calle": "Av. Colón",
  "numero": "4500",
  "localidad_id": 1,
  "telefono": "+54 351 400-0000",
  "email": "Norte@red.example",
  "responsable": "Ana Pérez",
  "horarios": [
    { "dia_semana": 1, "apertura": "09:00", "cierre": "13:00" },
    { "dia_semana": 1, "apertura": "15:00", "cierre": "19:00" },
    { "dia_semana": 2, "apertura": "09:00", "cierre": "18:00" }
  ],
  "confirmar_direccion_duplicada": false
}
```

Se normalizan: `codigo` a `NORTE`, `telefono` a `+543514000000` y `email` a minúsculas. `confirmar_direccion_duplicada` es opcional (por defecto `false`).

Response `201` (`Location: /api/v1/sedes/3`): el esquema de administrador de arriba.

Errores:

| Estado y código | Cuándo |
|-----------------|--------|
| `422 VALIDACION` | Campo faltante o con formato inválido (`detalles[].campo`: `codigo`, `telefono`, `email`, `numero`…) |
| `422 LOCALIDAD_INVALIDA` | `localidad_id` fuera del catálogo |
| `422 HORARIO_INVALIDO` | Sin franjas, solapadas, cierre no posterior, más de 4 por día; `detalles` indica el día |
| `409 SEDE_CODIGO_DUPLICADO` / `409 SEDE_NOMBRE_DUPLICADO` | Código o nombre repetido; `detalles` lleva la sede existente |
| `409 DIRECCION_DUPLICADA` | Ya existe una sede en esa dirección y no se confirmó (ver abajo) |

Orden de validación: forma (422) → duplicados de código y nombre (409) → dirección repetida (409).

Respuesta `409 DIRECCION_DUPLICADA`:

```json
{
  "error": {
    "codigo": "DIRECCION_DUPLICADA",
    "mensaje": "Ya existe una sede en esa dirección: Sede Central (CEN). Corrija la dirección o confirme que es intencional.",
    "detalles": [
      { "campo": "direccion", "problema": "duplicada",
        "sede": { "id": 1, "codigo": "CEN", "nombre": "Sede Central", "estado": "ACTIVA" } }
    ]
  }
}
```

Con esa respuesta el cliente tiene dos caminos: reenviar **cambiando** los datos de la dirección (u otros campos), o reenviar **el mismo cuerpo con `"confirmar_direccion_duplicada": true`**. La confirmación solo tiene efecto si de verdad hay un duplicado y queda registrada en el historial. Si hay varias sedes en la misma dirección, `detalles` las lista a todas.

### `PUT /sedes/{id}` — modificar sede

Request: igual al alta, **sin `codigo`**, más `version` (obligatoria) con el valor que se leyó:

```json
{ "version": 4, "nombre": "Sede Norte", "calle": "Av. Colón", "numero": "4600", "localidad_id": 1,
  "telefono": "+543514000000", "email": "norte@red.example", "responsable": "Ana Pérez",
  "horarios": [ { "dia_semana": 1, "apertura": "09:00", "cierre": "18:00" } ],
  "confirmar_direccion_duplicada": false }
```

Los `horarios` **reemplazan** por completo los anteriores. Response `200`: esquema de administrador con `version` incrementada. La advertencia de dirección solo se evalúa si cambió `calle`, `numero` o `localidad_id`.

Errores adicionales: `422 CODIGO_INMUTABLE` (si el cuerpo trae un `codigo` distinto del actual), `409 SEDE_EN_BAJA` (la sede está en baja: hay que reactivarla), `409 CONFLICTO_DE_VERSION` (`detalles` informa la versión actual; el cliente debe recargar), `404 SEDE_NO_ENCONTRADA`.

### `POST /sedes/{id}/baja` — baja de sede

Request: `{ "motivo": "Cierre por obras", "version": 4 }` (el motivo tiene de 5 a 300 caracteres)

Response `200`: esquema de administrador con `"estado": "BAJA"` y `baja` completo:

```json
{ "id": 3, "estado": "BAJA", "baja": { "fecha": "2026-10-14T15:30:00Z", "motivo": "Cierre por obras",
  "usuario": { "id": 1, "nombre": "Admin" } }, "version": 5 }
```

Errores: `409 SEDE_YA_EN_BAJA`, `409 CONFLICTO_DE_VERSION`, `422 VALIDACION` (motivo vacío o fuera de rango) y `409 SEDE_CON_ACTIVIDAD_PENDIENTE`:

```json
{
  "error": {
    "codigo": "SEDE_CON_ACTIVIDAD_PENDIENTE",
    "mensaje": "No se puede dar de baja la sede Sede Norte: tiene actividad pendiente (2 préstamos en curso, 1 remito abierto, 1 bibliotecario asignado). Finalice o transfiera esa actividad y vuelva a intentar.",
    "detalles": [
      { "tipo": "PRESTAMOS_EN_CURSO", "cantidad": 2, "hay_mas": false,
        "elementos": [ { "id": 118, "referencia": "P-2026-000118", "estado": "ACTIVO" },
                       { "id": 121, "referencia": "P-2026-000121", "estado": "VENCIDO" } ] },
      { "tipo": "REMITOS_ABIERTOS", "cantidad": 1, "hay_mas": false,
        "elementos": [ { "id": 44, "referencia": "R-2026-000044", "estado": "EN_TRANSITO" } ] },
      { "tipo": "BIBLIOTECARIOS_ASIGNADOS", "cantidad": 1, "hay_mas": false,
        "elementos": [ { "id": 7, "referencia": "bibliotecario.norte", "estado": "ACTIVO" } ] }
    ]
  }
}
```

`tipo` toma uno de: `PRESTAMOS_EN_CURSO`, `REMITOS_ABIERTOS`, `RESERVAS_PENDIENTES`, `EJEMPLARES_EN_SEDE`, `EJEMPLARES_PROPIOS_FUERA`, `BIBLIOTECARIOS_ASIGNADOS`. `elementos` trae hasta 10 por tipo y `hay_mas` indica si `cantidad` es mayor. Solo aparecen los tipos con impedimentos; la respuesta no modifica ningún dato.

### `POST /sedes/{id}/reactivar`

Request: `{ "version": 5 }`. Response `200`: esquema de administrador con `"estado": "ACTIVA"` y `baja: null`. Errores: `409 SEDE_YA_ACTIVA`, `409 CONFLICTO_DE_VERSION`.

### `GET /sedes` — listado

Parámetros: `page`, `size`, `estado` (`ACTIVA`, `BAJA` o `TODAS`), `q` (texto en nombre, código, calle o localidad, sin distinguir mayúsculas ni tildes), `localidad_id`, `orden` (`nombre`, `-nombre`, `codigo`, `-codigo`, `creado_en`, `-creado_en`; por defecto `nombre`).

| Rol | Estado por defecto | Estados que puede pedir |
|-----|--------------------|-------------------------|
| Administrador | `TODAS` | todos |
| Bibliotecario | `ACTIVA` | todos |
| Socio | `ACTIVA` | solo `ACTIVA`: el parámetro se ignora |

Response `200`: `{ "items": [ ...esquema según rol... ], "total": 4, "page": 1, "size": 20 }`.

### `GET /sedes/resumen`

Roles: A. Response `200`: `{ "total": 4, "activas": 3, "en_baja": 1 }`.

### Excepciones de horario

`POST /sedes/{id}/excepciones-horario`:

```json
{ "fecha_desde": "2026-12-24", "fecha_hasta": "2026-12-26", "tipo": "CIERRE_TOTAL", "motivo": "Feriados de fin de año" }
```

```json
{ "fecha_desde": "2026-11-20", "tipo": "CIERRE_PARCIAL", "hora_desde": "14:00", "hora_hasta": "18:00", "motivo": "Mantenimiento" }
```

`fecha_hasta` es opcional (por defecto igual a `fecha_desde`; máximo 31 días de rango). `hora_desde` y `hora_hasta` solo van en el cierre parcial. `motivo` es opcional, hasta 150 caracteres. Response `201`: la lista de excepciones creadas, una por día:

```json
[ { "id": 12, "fecha": "2026-12-24", "tipo": "CIERRE_TOTAL", "motivo": "Feriados de fin de año" },
  { "id": 13, "fecha": "2026-12-25", "tipo": "CIERRE_TOTAL", "motivo": "Feriados de fin de año" },
  { "id": 14, "fecha": "2026-12-26", "tipo": "CIERRE_TOTAL", "motivo": "Feriados de fin de año" } ]
```

La operación es atómica: si algún día falla, no se crea ninguno. Errores: `422 EXCEPCION_HORARIO_INVALIDA` (fecha pasada, rango mayor a 31 días, horas inconsistentes), `409 EXCEPCION_HORARIO_SUPERPUESTA` (indica la excepción existente), `409 SEDE_EN_BAJA`.

`DELETE /sedes/{id}/excepciones-horario/{excepcion_id}`: `204`. Solo excepciones de hoy o futuras; una pasada devuelve `422 EXCEPCION_HORARIO_INVALIDA`. Estas operaciones bloquean la sede pero no cambian su `version`.

### `GET /sedes/{id}/historial`

Roles: A. Paginado, del más reciente al más antiguo.

```json
{
  "items": [
    { "id": 31, "tipo_evento": "MODIFICACION", "fecha_hora": "2026-11-02T12:00:00Z",
      "usuario": { "id": 1, "nombre": "Admin" }, "estado_anterior": null, "estado_nuevo": null,
      "motivo": null, "version_resultante": 4,
      "cambios": [ { "campo": "telefono", "antes": "+543514221234", "despues": "+543514000000" } ] },
    { "id": 30, "tipo_evento": "BAJA", "fecha_hora": "2026-10-20T10:00:00Z",
      "usuario": { "id": 1, "nombre": "Admin" }, "estado_anterior": "ACTIVA", "estado_nuevo": "BAJA",
      "motivo": "Cierre por obras", "version_resultante": 3, "cambios": [] }
  ],
  "total": 12, "page": 1, "size": 20
}
```

### `GET /localidades`

Roles: A, B, S. `?provincia_id=` y `?q=` (sin distinguir mayúsculas ni tildes); no paginado cuando se filtra por provincia (lista cerrada ordenada por nombre).

```json
[ { "id": 1, "nombre": "Córdoba", "departamento": "Capital", "provincia_id": 1, "provincia": "Córdoba" } ]
```

### Usuarios del personal

`POST /usuarios`:

```json
{ "username": "bibliotecario.norte", "password": "••••••••••", "nombre": "Lucía Gómez",
  "rol": "BIBLIOTECARIO", "sede_id": 2 }
```

`rol` es `ADMIN` o `BIBLIOTECARIO` (los usuarios `SOCIO` los crea el proceso de socios). Reglas de los campos:

| Campo | Regla |
|-------|-------|
| `username` | 3 a 50 caracteres entre `a-z`, `0-9`, `.`, `_` y `-`; se guarda en minúsculas y es único sin distinguir mayúsculas |
| `password` | 10 a 128 caracteres con al menos una letra y un número; se guarda con Argon2id y nunca se devuelve |
| `nombre` | 3 a 100 caracteres |
| `sede_id` | Obligatoria para `BIBLIOTECARIO` y de una sede **activa**; no se admite para `ADMIN` |

Response `201` (`Location: /api/v1/usuarios/7`) y detalle `GET /usuarios/{id}`:

```json
{ "id": 7, "username": "bibliotecario.norte", "nombre": "Lucía Gómez", "rol": "BIBLIOTECARIO", "activo": true,
  "sede_id": 2, "sede": { "id": 2, "codigo": "NORTE", "nombre": "Sede Norte" },
  "creado_en": "2026-11-10T15:00:00Z", "creado_por": { "id": 1, "nombre": "Admin" },
  "actualizado_en": "2026-11-10T15:00:00Z", "actualizado_por": { "id": 1, "nombre": "Admin" } }
```

Errores del alta: `409 DUPLICADO` (username repetido), `422 VALIDACION` (formato inválido, bibliotecario sin sede, `ADMIN` con sede, rol que no es de personal), `409 SEDE_EN_BAJA` (sede destino en baja), `404 SEDE_NO_ENCONTRADA`. El orden de validación es forma (422) → username repetido (409) → sede (404/409).

`GET /usuarios` devuelve solo personal (los socios no aparecen) ordenado por nombre; `q` busca en nombre (sin distinguir mayúsculas ni tildes) y en usuario. Un socio o un id inexistente responden `404 USUARIO_NO_ENCONTRADO` en todas las rutas de `/usuarios/{id}`.

Un administrador no puede darse de baja a sí mismo (`422 VALIDACION`, `detalles[0].campo = "id"`).

`PUT /usuarios/{id}` con `{ "nombre": "Lucía Gómez", "sede_id": 3 }` reasigna al bibliotecario a otra sede activa; rige desde su siguiente solicitud, porque cada solicitud recarga al usuario. El `sede_id` es obligatorio para un bibliotecario y no se admite para un administrador (`422 VALIDACION`); si no cambia, la sede no se vuelve a validar, de modo que se puede corregir el nombre de alguien cuya sede está en baja. También se puede reasignar a un usuario dado de baja, para poder reactivarlo.

`POST /usuarios/{id}/baja` lo desvincula y deja de contar como asignado a la sede (`409 USUARIO_YA_EN_BAJA` si ya lo estaba). `POST /usuarios/{id}/reactivar` devuelve `409 SEDE_EN_BAJA` si su sede está dada de baja (hay que reasignarlo primero) y `409 USUARIO_YA_ACTIVO` si ya estaba activo.

Los bibliotecarios **activos** asignados a una sede son un impedimento de baja de esa sede (`BIBLIOTECARIOS_ASIGNADOS`, hasta 10 elementos con `referencia` = usuario). Asignar o reasignar toma la sede en modo compartido, así que no puede cruzarse con su baja: si gana la baja, la asignación recibe `SEDE_EN_BAJA`; si gana la asignación, la baja ve al bibliotecario nuevo.

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
{ "id": 45, "numero_socio": "00045", "estado": "HABILITADO", "sede_alta_id": 2 }
```

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

### `POST /prestamos` — préstamo interbibliotecario

Request (el tipo se deduce de las sedes):

```json
{ "socio_id": 45, "ejemplar_id": 301, "sede_destino_id": 2 }
```

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

Errores posibles: `409 SOCIO_INHABILITADO`, `409 EJEMPLAR_NO_DISPONIBLE`, `409 SEDE_EN_BAJA`, `409 LIMITE_PRESTAMOS`, `422 EJEMPLAR_FUERA_DE_SEDE_ORIGEN`.

Para un préstamo local, `sede_destino_id` coincide con la sede del ejemplar y el préstamo nace sin remito.

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

Request: `{ "libro_id": 12, "sede_retiro_id": 2, "socio_id": 45 }` (el socio omite `socio_id`; se toma de su sesión).

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
