# Documentación funcional

Requerimientos funcionales (RF), casos de uso (CU) con flujo normal y flujos alternativos, y criterios de aceptación (CA) del Sistema de Préstamos Interbibliotecarios. Se derivan de las definiciones de [`../negocio/`](../negocio/), que son la fuente de las reglas.

## Documentos

| # | Documento | Prefijo | Negocio de origen |
|---|-----------|---------|-------------------|
| 00 | [Acceso y roles](00-acceso-y-roles.md) | ACC | [Contexto y actores](../negocio/00-contexto-y-actores.md) |
| 01 | [Sedes](01-sedes.md) | SED | [Sedes](../negocio/01-sedes.md) |
| 02 | [Socios](02-socios.md) | SOC | [Socios](../negocio/02-socios.md) |
| 03 | [Catálogo](03-catalogo.md) | CAT | [Catálogo](../negocio/03-catalogo.md) |
| 04 | [Préstamos](04-prestamos.md) | PRE | [Préstamos](../negocio/04-prestamos.md) |
| 05 | [Remitos](05-remitos.md) | REM | [Remitos](../negocio/05-remitos.md) |
| 06 | [Reservas](06-reservas.md) | RES | [Reservas](../negocio/06-reservas.md) |
| 07 | [Devoluciones y multas](07-devoluciones.md) | DEV | [Devoluciones](../negocio/07-devoluciones.md) |
| 08 | [Reportes](08-reportes.md) | REP | [Reportes](../negocio/08-reportes.md) |

## Convenciones

- **Identificadores:** `RF-<PREFIJO>-<nn>` para requerimientos, `CU-<PREFIJO>-<nn>` para casos de uso, `CA-<PREFIJO>-<nn>` para criterios de aceptación. Son estables: no se reutilizan ni se renumeran.
- **Prioridad:** `Obligatorio` (proceso o validación exigidos por el enunciado) u `Opcional` (extensión).
- **Casos de uso:** cada uno indica actor, precondiciones, flujo normal (numerado), flujos alternativos (`A1`, `A2`…, que referencian el paso donde se desvían) y postcondiciones.
- **Criterios de aceptación:** formato *Dado / Cuando / Entonces*, verificables y vinculados al RF que prueban. Son la base de los tests.
- **Parámetros:** plazos, límites y montos son configurables; los valores vigentes están en los [parámetros globales](../negocio/00-contexto-y-actores.md#parámetros-globales-configurables).
- **Baja lógica:** ninguna entidad se elimina físicamente.
- **Trazabilidad:** todo cambio de estado de remito, préstamo y ejemplar registra fecha y hora, usuario y estado anterior.

## Punto abierto

Si el **socio puede pedir un préstamo directamente**. Mientras no se defina, los casos de uso asumen que el préstamo lo registra el bibliotecario en nombre del socio (ver [Préstamos](04-prestamos.md)).
