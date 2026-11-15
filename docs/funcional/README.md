# Documentación funcional

Requerimientos funcionales (RF), casos de uso (CU) con flujo normal y flujos alternativos, y criterios de aceptación (CA) del Sistema de Préstamos Interbibliotecarios. Se derivan de las definiciones de [`../negocio/`](../negocio/), que son la fuente de las reglas.

## Documentos

| # | Documento | Prefijo | Negocio de origen | RF | CU | CA |
|---|-----------|---------|-------------------|---:|---:|---:|
| 00 | [Acceso y roles](00-acceso-y-roles.md) | ACC | [Contexto y actores](../negocio/00-contexto-y-actores.md) | 12 | 4 | 17 |
| 01 | [Sedes](01-sedes.md) | SED | [Sedes](../negocio/01-sedes.md) | 13 | 7 | 47 |
| 02 | [Socios](02-socios.md) | SOC | [Socios](../negocio/02-socios.md) | 15 | 8 | 20 |
| 03 | [Catálogo](03-catalogo.md) | CAT | [Catálogo](../negocio/03-catalogo.md) | 15 | 9 | 21 |
| 04 | [Préstamos](04-prestamos.md) | PRE | [Préstamos](../negocio/04-prestamos.md) | 22 | 8 | 30 |
| 05 | [Remitos](05-remitos.md) | REM | [Remitos](../negocio/05-remitos.md) | 16 | 7 | 26 |
| 06 | [Reservas](06-reservas.md) | RES | [Reservas](../negocio/06-reservas.md) | 17 | 7 | 22 |
| 07 | [Devoluciones y multas](07-devoluciones.md) | DEV | [Devoluciones](../negocio/07-devoluciones.md) | 24 | 6 | 33 |
| 08 | [Reportes](08-reportes.md) | REP | [Reportes](../negocio/08-reportes.md) | 10 | 2 | 23 |
| | **Total** | | | **144** | **58** | **239** |

## Convenciones

- **Identificadores:** `RF-<PREFIJO>-<nn>` para requerimientos, `CU-<PREFIJO>-<nn>` para casos de uso, `CA-<PREFIJO>-<nn>` para criterios de aceptación. Son estables: no se reutilizan ni se renumeran.
- **Prioridad:** `Obligatorio` (proceso o validación exigidos por el enunciado) u `Opcional` (extensión).
- **Casos de uso:** cada uno indica actor, precondiciones, flujo normal (numerado), flujos alternativos (`A1`, `A2`…, que referencian el paso donde se desvían) y postcondiciones.
- **Criterios de aceptación:** formato *Dado / Cuando / Entonces*, verificables y vinculados al RF que prueban. Son la base de los tests.
- **Parámetros:** plazos, límites y montos son configurables; los valores vigentes están en los [parámetros globales](../negocio/00-contexto-y-actores.md#parámetros-globales-configurables).
- **Baja lógica:** ninguna entidad se elimina físicamente, salvo un libro sin ejemplares cargado por error (RF-CAT-14) y las excepciones de horario de hoy o futuras (CU-SED-06).
- **Historial:** todo cambio de estado de remito, préstamo, ejemplar y reserva, y todo evento de socio y de sede, queda en un historial de solo inserción con fecha y hora, usuario (o «Sistema») y estado anterior.
- **Trazabilidad con las pruebas:** cada CA está citado por al menos una prueba: en el backend con `@pytest.mark.ca("CA-XXX-nn")` y en el frontend en el nombre del test (`it('CA-XXX-nn: …')`). El script `backend/scripts/verificar_trazabilidad_ca.py --estricto` (que corre en CI) falla si algún CA documentado no tiene prueba.

## Decisiones ya tomadas

El único punto que quedaba abierto, si el **socio puede pedir un préstamo directamente**, está decidido: el socio pide préstamos para sí (autogestión, CU-PRE-00) y el personal los registra en el mostrador (CU-PRE-01 y CU-PRE-02). Ver [Préstamos](04-prestamos.md).
