# 02. Administración de socios

Proceso obligatorio 2 del enunciado. Los puntos marcados como *A consultar* siguen abiertos con la cátedra.

## ¿Qué datos se modelan?

| Campo | Obligatorio | Regla |
|-------|:---:|-------|
| Número de socio | Automático | Único, generado por el sistema con 5 dígitos (`00045`) |
| Documento | Sí | Tipo `DNI`, `LE`, `LC` o `Pasaporte`, y número. DNI, LE y LC: de 7 a 8 dígitos; pasaporte: de 6 a 9 letras o números. Se guarda sin puntos ni espacios. **Tipo y número únicos** |
| Nombre y apellido | Sí | Hasta 100 caracteres cada uno |
| Fecha de nacimiento | No | Entre 1900 y hoy. Dato informativo y de apoyo para detectar duplicados; no condiciona el alta |
| Correo y teléfono | **Al menos uno** | Correo con formato válido; teléfono en formato internacional E.164 (`+543514221234`) |
| Domicilio | No | Hasta 200 caracteres |
| Sede de alta | Automático | La del bibliotecario que lo registra (el administrador la elige). Es solo un **dato de registro**: no vincula al socio con la sede ni limita dónde puede operar |
| Fecha de alta | Automático | |
| Estado | Automático | `Habilitado`, `Inhabilitado` o `Baja` (ver [Estados](#estados-del-socio)) |
| Causas de inhabilitación | Automático | `Decisión administrativa`, `Préstamo vencido`, `Multa impaga`; puede tener varias a la vez |
| Fecha y motivo de la baja | Automático | Solo si está en baja |

## Estados del socio

| Estado | Significado | Puede pedir préstamos y reservar |
|--------|-------------|:---:|
| `Habilitado` | Sin causas de inhabilitación | Sí |
| `Inhabilitado` | Tiene al menos una causa vigente | No |
| `Baja` | Salió de la red (baja lógica); se conserva su historial y puede reactivarse | No |

El estado **no se elige**: sale de las causas vigentes. Con al menos una causa, el socio está inhabilitado; sin ninguna, habilitado.

| Causa | Origen | Cómo se levanta |
|-------|--------|-----------------|
| **Decisión administrativa** | La decide el administrador, con un motivo de 5 a 300 caracteres | Solo el administrador |
| **Préstamo vencido** | Automática: un préstamo pasa a `Vencido` | Sola, al devolver el material |
| **Multa impaga** | Automática: se genera una multa por atraso | Sola, cuando el personal registra la multa como saldada |

Un socio puede tener varias causas a la vez, y sigue inhabilitado mientras quede alguna. Cuando hay más de una, se muestra primero la de mayor **prioridad**: decisión administrativa, préstamo vencido y multa impaga, en ese orden.

## ¿Quién administra los socios?

El **Bibliotecario** (alta, modificación, creación de la cuenta de acceso) en cualquier sede de la red; el **Administrador** además inhabilita y levanta la inhabilitación administrativa, da de baja y reactiva. Un socio pertenece a la red, no a una sola sede: puede pedir material en cualquier sede activa. No se puede dar de alta un socio en una sede en `Baja`, y la baja de la sede de alta no afecta al socio.

## ¿Quién puede ver esta información?

Personal (administrador y bibliotecario de cualquier sede) ve los datos completos; el socio ve solo los propios.

## Funcionalidades a cubrir

- Alta, modificación y consulta de socios.
- Búsqueda por número de socio, documento o apellido.
- Inhabilitación y rehabilitación.
- Consulta de la situación del socio: préstamos activos, vencidos, multas, reservas.

## ¿Qué acciones puede realizar un socio?

- Consultar el catálogo y la disponibilidad por sede.
- Reservar un libro no disponible.
- Cancelar sus reservas.
- Ver sus préstamos (activos, vencidos, historial), fechas de vencimiento y multas.
- Ver sus propios datos y solicitar su corrección al personal.

La **solicitud de un préstamo** la registra el personal en nombre del socio (en mostrador). *A consultar con la cátedra* si el socio debe poder pedirlo directamente.

## Casos de uso y flujos

1. **Alta:** el bibliotecario carga los datos, el sistema valida duplicados y asigna el número de socio, estado `Habilitado`.
2. **Modificación de datos.**
3. **Inhabilitación:** manual (administrador) o automática por regla (multa impaga o préstamo vencido).
4. **Rehabilitación:** cuando desaparece la causa (se devuelve el material o se salda la multa) o por decisión del administrador.
5. **Baja del socio:** baja lógica, solo si no tiene préstamos activos ni multas.

## Validaciones y reglas

- Documento y datos de contacto obligatorios y con formato válido.
- Un socio `Inhabilitado` **no puede recibir préstamos ni hacer reservas** (regla del enunciado).
- Un socio no puede superar el máximo de préstamos simultáneos (parámetro, valor 3).
- No se elimina físicamente un socio con historial.

## ¿Se debe inhabilitar a un socio con devoluciones o multas pendientes?

**Sí.**

- Con un **préstamo vencido** sin devolver: queda inhabilitado hasta devolver.
- Con una **multa impaga**: queda inhabilitado hasta saldarla. El sistema solo registra la multa como saldada (el cobro real queda fuera del alcance).
- La inhabilitación no borra los préstamos en curso: el socio sigue obligado a devolver.

## ¿Cómo evitamos socios duplicados?

- Número y tipo de documento únicos.
- Búsqueda previa obligatoria en el alta (por documento y por nombre + fecha de nacimiento).
- Si el socio existe en estado de baja, se **reactiva** en lugar de crear uno nuevo.
