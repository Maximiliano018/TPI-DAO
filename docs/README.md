# Documentación del proyecto

Documentación funcional, técnica y de negocio del **Sistema de Préstamos Interbibliotecarios** (TPI-DAO, UTN FRC 2026).

Contexto de origen: [`enunciado.md`](../enunciado.md) y [`analisis-enunciado.md`](../analisis-enunciado.md).

## Estructura

| Carpeta | Contenido | Estado |
|---------|-----------|--------|
| [`negocio/`](negocio/) | Dominio, actores, reglas, parámetros, procesos y reportes | En definición |
| [`funcional/`](funcional/) | Requerimientos funcionales y casos de uso | Pendiente |
| [`tecnica/`](tecnica/) | Arquitectura, modelo de clases, patrones, persistencia | Pendiente |

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

Cada documento responde las preguntas abiertas de su proceso. Las respuestas están marcadas así:

- **Definido:** surge directamente del enunciado.
- **Propuesta:** decisión recomendada por el equipo de trabajo que **todavía debe confirmar Maxi (y, cuando corresponda, la cátedra)**. Al confirmarse, se quita la marca.
- **A consultar:** el enunciado no alcanza y conviene preguntar a la cátedra.

Todos los valores numéricos (plazos, montos, límites) son **parámetros configurables**, no constantes del código.
