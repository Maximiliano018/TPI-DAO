# 02. Administración de socios

Proceso obligatorio 2 del enunciado. Los puntos marcados como *A consultar* siguen abiertos con la cátedra.

## ¿Qué datos se modelan?

| Campo | Detalle |
|-------|---------|
| Número de socio | Único, generado por el sistema |
| Documento | Tipo y número (DNI); único |
| Nombre y apellido | Obligatorios |
| Fecha de nacimiento | Dato informativo y de apoyo para detectar duplicados; no condiciona el alta |
| Contacto | Correo, teléfono, domicilio |
| Sede de alta | Sede donde se registró el socio |
| Sede | Sede habitual del socio. Al dar de alta al socio se inicializa con la sede de alta; la pueden modificar el personal y el propio socio desde su cuenta. Se propone por defecto al iniciar una solicitud de préstamo o una reserva; el socio puede cambiarla en esa operación antes de confirmar |
| Fecha de alta | Automática |
| Cantidad de préstamos activos | Entero o bool |
| Estado | `Habilitado` / `Inhabilitado` |
| Motivo de inhabilitación | Texto o causa (`Multa impaga`, `Préstamo vencido`, `Decisión administrativa`) |
| Préstamos históricos | Listado de historial de préstamos solicitados |

## ¿Quién administra los socios?

El **Bibliotecario** (alta, modificación, habilitación) en cualquier sede de la red; el **Administrador** además puede corregir datos y resolver conflictos. Un socio pertenece a la red, no a una sola sede: puede pedir material en cualquier sede activa.

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
- Solicitar préstamos interbibliotecarios. El socio inicia una solicitud de préstamo y el sistema determina el tipo (ver [Préstamos](04-prestamos.md#inicio-del-flujo)).
- Ver sus préstamos (activos, vencidos, historial), fechas de vencimiento y multas.
- Ver sus propios datos y solicitar su corrección al personal.
- Cambiar su sede (la que se propone por defecto en sus préstamos y reservas).

La **solicitud de un préstamo** la registra el personal en nombre del socio cuando sea requerido por el socio. El **socio** solo puede solicitar préstamos interbibliotecarios. Si hay ejemplares disponibles en la sede elegida, el sistema rechaza la solicitud y le indica que se acerque al mostrador. Se debe contemplar la incorporación de la funcionalidad de solicitud de préstamos locales para un evolutivo.

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


## ¿Cómo controlamos que un socio solicite más préstamos de los permitidos?

- Consulta previa obligatoria en la generación de préstamos (consulta parámetro `Cantidad de préstamos activos` del usuario y valida que sea menor que la cantidad permitida).
- Si el socio ya tiene el máximo de préstamos permitidos, se cancela la generación de preéstamo y se muestra en pantalla el mensaje de error indicando el motivo.
- El control se debe realizar al comienzo del flujo de generación de préstamo.