# 01. Administración de sedes

Proceso obligatorio 1 del enunciado.

## ¿Qué datos se modelan?

**Definido** por el enunciado: dirección, datos de contacto, horarios y estado activo/baja.

| Campo | Detalle |
|-------|---------|
| Código de sede | Identificador único corto (ej. `CEN`, `NORTE`) |
| Nombre | Único en la red |
| Dirección | Calle, número, localidad, provincia |
| Contacto | Teléfono, correo, nombre del responsable de la sede |
| Horarios | Días y franjas de atención |
| Estado | `Activa` / `Baja` |
| Fecha y motivo de baja | Solo si está en baja |

## ¿Quién administra las sedes?

El **Administrador**. El bibliotecario no da de alta ni de baja sedes.

## Funcionalidades a cubrir

- Alta, modificación y consulta de sedes.
- Baja y reactivación.
- Listado con filtro por estado.
- Consulta de horarios y contacto.

## ¿Quién puede ver esta información?

| Rol | Acceso |
|-----|--------|
| Administrador | Todo, incluidos motivo y fecha de baja |
| Bibliotecario | Datos básicos de todas las sedes (necesarios para armar envíos) |
| Socio | Dirección, contacto y horarios de sedes activas |

## ¿El personal de una sede ve las otras sedes?

Sí, en modo **solo lectura** y con datos básicos (nombre, dirección, contacto, horarios, estado). Es necesario para operar préstamos interbibliotecarios. La gestión operativa (socios en trámite, préstamos, remitos) queda limitada a su propia sede, salvo los remitos entrantes y salientes que la involucran.

## Casos de uso y flujos

1. **Alta de sede:** el administrador carga los datos; el sistema valida unicidad y crea la sede `Activa`.
2. **Modificación:** actualiza datos de contacto, dirección u horarios.
3. **Baja de sede:** el administrador la solicita; el sistema verifica que no haya actividad pendiente (ver abajo) y la pasa a `Baja` con fecha y motivo.
4. **Reactivación:** vuelve a `Activa`; conserva el historial.
5. **Consulta:** listado y detalle.

## Validaciones y reglas

- Código y nombre obligatorios y únicos.
- Los horarios no pueden solaparse en un mismo día y la hora de cierre es posterior a la de apertura.
- Una sede en `Baja` **no puede ser origen ni destino** de préstamos, reservas ni envíos (regla del enunciado).
- Una sede en `Baja` no recibe altas de ejemplares nuevos ni de socios.
- Nunca se elimina físicamente una sede.

## ¿Bajo qué criterio se habilita o deshabilita una sede?

El administrador decide. Motivos habituales: cierre definitivo, cierre temporal, obras o fusión con otra sede. Siempre queda registrado el motivo.

## ¿Se puede dar de baja una sede con actividad pendiente?

**No.** La baja se bloquea si la sede tiene:

- préstamos activos o vencidos (como origen o destino),
- remitos no cerrados (en cualquier estado distinto de `Recibido`, `Extraviado`, `Dañado` o `Destruido`),
- reservas pendientes,
- ejemplares propios que no estén en otra sede o en tránsito.

El sistema informa qué elementos impiden la baja. Para darla de baja hay que cerrar esas operaciones o **trasladar los ejemplares** a otra sede mediante remito, antes de la baja.

La baja **nunca cancela automáticamente** las operaciones en curso: se bloquea hasta que finalicen.

## ¿Cómo evitamos sedes duplicadas?

- Código de sede único.
- Nombre único, comparado sin distinguir mayúsculas ni tildes.
- Advertencia si ya existe otra sede con la misma dirección.
