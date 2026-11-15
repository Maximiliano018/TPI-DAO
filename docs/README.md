# Documentación del proyecto

Documentación funcional, técnica y de negocio del **Sistema de Préstamos Interbibliotecarios** (TPI-DAO, UTN FRC 2026).

Contexto de origen: [`enunciado.md`](../enunciado.md) y [`analisis-enunciado.md`](../analisis-enunciado.md).

## Estructura

| Carpeta | Contenido | Estado |
|---------|-----------|--------|
| [`negocio/`](negocio/) | Dominio, actores, reglas, parámetros, procesos y reportes | Confirmada e implementada |
| [`funcional/`](funcional/) | Requerimientos funcionales, casos de uso (flujos normal y alternativos) y criterios de aceptación, cada uno con su prueba | Confirmada e implementada |
| [`tecnica/`](tecnica/) | Stack, arquitectura, modelo de clases y de datos, máquinas de estado, [patrones de diseño](tecnica/05-patrones-de-diseno.md), API, testing, frontend y guía de estilos | Refleja la implementación |
| [`../database/`](../database/README.md) | Base de datos: diagrama entidad-relación, [diccionario de datos](../database/diccionario-de-datos.md) generado desde la base, integridad, migraciones, datos de demostración y operación | Refleja la implementación |

## Documentos de negocio

| # | Documento | Tema |
|---|-----------|------|
| 00 | [Contexto y actores](negocio/00-contexto-y-actores.md) | Dominio, roles, permisos, parámetros globales y glosario |
| 01 | [Sedes](negocio/01-sedes.md) | Administración de las sedes de la red |
| 02 | [Socios](negocio/02-socios.md) | Administración de socios |
| 03 | [Catálogo](negocio/03-catalogo.md) | Libros y ejemplares |
| 04 | [Préstamos](negocio/04-prestamos.md) | Solicitudes de préstamo local e interbibliotecario |
| 05 | [Remitos](negocio/05-remitos.md) | Envíos entre sedes y su trazabilidad |
| 06 | [Reservas](negocio/06-reservas.md) | Gestión de reservas |
| 07 | [Devoluciones](negocio/07-devoluciones.md) | Devoluciones, vencimientos y multas |
| 08 | [Reportes](negocio/08-reportes.md) | Datos necesarios, roles y utilidad de cada reporte |

## Cómo leer las definiciones

Cada documento de negocio responde las preguntas de su proceso. Todo lo que el enunciado no fijaba ya está decidido e implementado: no quedan puntos abiertos con la cátedra. Los requerimientos funcionales se trazan a sus criterios de aceptación, y cada criterio a las pruebas que lo verifican (ver [funcional](funcional/README.md)).

Los plazos, montos y límites del negocio (ver [parámetros](negocio/00-contexto-y-actores.md#parámetros-globales-configurables)) son **parámetros configurables** que el administrador cambia sin tocar el código. Los límites técnicos (por ejemplo, la duración de la sesión) se configuran por entorno.
