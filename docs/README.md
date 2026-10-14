# Documentación del proyecto

Documentación funcional, técnica y de negocio del **Sistema de Préstamos Interbibliotecarios** (TPI-DAO, UTN FRC 2026).

Contexto de origen: [`enunciado.md`](../enunciado.md) y [`analisis-enunciado.md`](../analisis-enunciado.md).

## Estructura

| Carpeta | Contenido | Estado |
|---------|-----------|--------|
| [`negocio/`](negocio/) | Dominio, actores, reglas, parámetros, procesos y reportes | Confirmada |
| [`funcional/`](funcional/) | Requerimientos funcionales, casos de uso (flujos normal y alternativos) y criterios de aceptación | Confirmada |
| [`tecnica/`](tecnica/) | Stack, arquitectura, modelo de clases y de datos, máquinas de estado, patrones, API, testing, frontend y guía de estilos | En definición |

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

Cada documento responde las preguntas de su proceso. Los puntos que siguen abiertos están marcados así:

- **Definido:** surge del enunciado o fue confirmado por Maxi (la documentación de negocio fue revisada y confirmada el 2026-10-14).
- **A consultar:** el enunciado no alcanza y conviene preguntar a la cátedra; sigue abierto. Hoy hay un único punto: si el socio puede pedir el préstamo directamente.

Todos los valores numéricos (plazos, montos, límites) son **parámetros configurables**, no constantes del código.
