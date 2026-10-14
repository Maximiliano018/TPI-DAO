# 02. Administración de socios

Proceso obligatorio 2 del enunciado. Las definiciones fueron confirmadas por Maxi; los puntos marcados como *A consultar* siguen abiertos con la cátedra.

## ¿Qué datos se modelan?

| Campo | Detalle |
|-------|---------|
| Número de socio | Único, generado por el sistema |
| Documento | Tipo y número (DNI); único |
| Nombre y apellido | Obligatorios |
| Fecha de nacimiento | Para validar que el socio sea mayor de edad |
| Contacto | Correo, teléfono, domicilio |
| Sede de alta | Sede donde se registró el socio |
| Fecha de alta | Automática |
| Estado | `Habilitado` / `Inhabilitado` |
| Motivo de inhabilitación | Texto o causa (`Multa impaga`, `Préstamo vencido`, `Decisión administrativa`) |

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
