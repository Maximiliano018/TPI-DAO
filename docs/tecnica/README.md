# Documentación técnica

Define cómo se construye el **Sistema de Préstamos Interbibliotecarios**. Se deriva de los requerimientos de [`../funcional/`](../funcional/) y las reglas de [`../negocio/`](../negocio/).

## Documentos

| # | Documento | Contenido |
|---|-----------|-----------|
| 00 | [Stack y decisiones](00-stack-y-decisiones.md) | Tecnologías elegidas, justificación y alternativas descartadas |
| 01 | [Arquitectura del backend](01-arquitectura-backend.md) | Capas, dependencias, estructura de carpetas, transacciones, errores y seguridad |
| 02 | [Modelo de clases](02-modelo-de-clases.md) | Diagramas UML del dominio y de los patrones |
| 03 | [Máquinas de estado](03-maquinas-de-estado.md) | Estados y transiciones de sede, socio, ejemplar, préstamo, remito, reserva y multa |
| 04 | [Modelo de datos](04-modelo-de-datos.md) | Diagrama entidad-relación, tablas, restricciones e índices |
| 05 | [Patrones de diseño](05-patrones-de-diseno.md) | Patrones aplicables, ventajas y justificación |
| 06 | [API REST](06-api.md) | Convenciones, endpoints con request y response, errores |
| 07 | [Testing y calidad](07-testing-y-calidad.md) | Estrategia de pruebas, trazabilidad con los criterios de aceptación, herramientas |
| 08 | [Convenciones de desarrollo](08-convenciones.md) | Estilo, clean code, documentación de código, git |
| 09 | [Frontend](09-frontend.md) | Arquitectura de React, pantallas por rol, estado y formularios |
| 10 | [Guía de estilos](10-guia-de-estilos.md) | Design system base: tokens, componentes y accesibilidad |

## Decisiones ya tomadas

| Tema | Decisión | Quién |
|------|----------|-------|
| Backend | Python con FastAPI, en capas | Maxi |
| Persistencia | ORM (SQLAlchemy 2.0) | Maxi |
| Frontend | React con JavaScript | Maxi |
| Base de datos | PostgreSQL (SQLite en memoria para tests) | Maxi, 2026-10-14 |
| Design system | Crear uno base propio, reemplazable | Maxi, 2026-10-14 |

## Decisiones propuestas, a confirmar

Son recomendaciones técnicas del equipo de trabajo que asumo hasta que se corrijan.

| # | Tema | Propuesta |
|---|------|-----------|
| T1 | Entidades de dominio | Clases de dominio puras, separadas de los modelos del ORM, con mapeo en los repositorios ([ver arquitectura](01-arquitectura-backend.md#entidades-de-dominio-y-modelos-del-orm)) |
| T2 | Idioma del código | Nombres de dominio en español sin tildes (`Prestamo`, `Ejemplar`); sufijos técnicos en inglés (`Repository`, `Service`) |
| T3 | Autenticación | JWT con usuario y contraseña, roles Administrador, Bibliotecario y Socio |
| T4 | Estados de ejemplar | Sumar `Apartado` y `En revisión` a los estados definidos en negocio ([ver máquinas de estado](03-maquinas-de-estado.md#ejemplar)) |
| T5 | Entrega | `docker-compose` con base, backend y frontend; instrucciones también sin Docker |
| T6 | Migraciones | Alembic |
| T7 | Tareas periódicas | Detección de vencimientos y reservas vencidas con un planificador interno (APScheduler) |

## Pendiente

- Los comandos de instalación, tests y linter se agregan a `CLAUDE.md` cuando exista el código.
- El documento de [guía de estilos](10-guia-de-estilos.md) se reemplaza si el equipo aporta un design system propio.
