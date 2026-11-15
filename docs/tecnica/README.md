# Documentación técnica

Define cómo se construye el **Sistema de Préstamos Interbibliotecarios**. Se deriva de los requerimientos de [`../funcional/`](../funcional/) y las reglas de [`../negocio/`](../negocio/).

## Documentos

| # | Documento | Contenido |
|---|-----------|-----------|
| 00 | [Stack y decisiones](00-stack-y-decisiones.md) | Tecnologías elegidas, justificación y alternativas descartadas |
| 01 | [Arquitectura del backend](01-arquitectura-backend.md) | Capas, dependencias, estructura de carpetas, transacciones, errores y seguridad |
| 02 | [Modelo de clases](02-modelo-de-clases.md) | Diagramas UML del dominio y de los patrones |
| 03 | [Máquinas de estado](03-maquinas-de-estado.md) | Estados y transiciones de sede, socio, ejemplar, préstamo, remito, reserva, multa y pago |
| 04 | [Modelo de datos](04-modelo-de-datos.md) | Diseño del modelo de datos: tablas, restricciones, índices, migraciones y seed (los diagramas entidad-relación y el diccionario están en [`database/`](../../database/README.md)) |
| 05 | [Patrones de diseño](05-patrones-de-diseno.md) | Patrones implementados: problema, implementación, ventajas, costos y pruebas |
| 06 | [API REST](06-api.md) | Convenciones, endpoints con request y response, errores |
| 07 | [Testing y calidad](07-testing-y-calidad.md) | Estrategia de pruebas, trazabilidad con los criterios de aceptación, herramientas |
| 08 | [Convenciones de desarrollo](08-convenciones.md) | Estilo, clean code, documentación de código, git |
| 09 | [Frontend](09-frontend.md) | Arquitectura de React, pantallas por rol, estado y formularios |
| 10 | [Guía de estilos](10-guia-de-estilos.md) | Design system base: tokens, componentes y accesibilidad |
| 11 | [Plan de implementación: sedes y acceso](11-plan-sedes-y-acceso.md) | Plan histórico de la primera iteración (completado) |
| 12 | [Pago de multas](12-pago-de-multas.md) | Cobro en el mostrador y pago en línea simulado |

## Decisiones tomadas

| # | Tema | Decisión |
|---|------|----------|
| — | Backend | Python 3.12 con FastAPI, en capas |
| — | Persistencia | ORM (SQLAlchemy 2.0) |
| — | Frontend | React 18 con JavaScript y Vite |
| — | Base de datos | PostgreSQL 16 (las pruebas unitarias y de servicios usan repositorios en memoria; las de integración, una base PostgreSQL de pruebas; sin SQLite) |
| — | Design system | Base propio, reemplazable ([guía de estilos](10-guia-de-estilos.md)) |
| T1 | Entidades de dominio | Clases de dominio puras, separadas de los modelos del ORM, con el mapeo dentro de cada repositorio ([arquitectura](01-arquitectura-backend.md#entidades-de-dominio-y-modelos-del-orm)) |
| T2 | Idioma del código | Nombres de dominio en español sin tildes (`Prestamo`, `Ejemplar`); sufijos técnicos en inglés (`Repository`, `Service`) |
| T3 | Autenticación | JWT con usuario y contraseña, roles fijos Administrador, Bibliotecario y Socio, permisos por rol en código ([decisión D6](00-stack-y-decisiones.md#d6-autenticación-y-permisos)) |
| T4 | Estados de ejemplar | Se sumaron `Apartado` y `En revisión` a los estados de negocio ([máquinas de estado](03-maquinas-de-estado.md#ejemplar)) |
| T5 | Entrega | **Confirmada:** `docker compose up -d --build` levanta base, backend y frontend (`backend/Dockerfile`, `frontend/Dockerfile` con nginx); para desarrollar se levanta solo `db` y se usan los comandos de [`CLAUDE.md`](../../CLAUDE.md) |
| T6 | Migraciones | Alembic (`backend/alembic/versions/`, `0000` a `0017`) |
| T7 | Tareas periódicas | APScheduler dentro del proceso: detección de préstamos vencidos, retiros vencidos y reservas vencidas, todos los días a las 00:05 (hora de negocio) y una vez al iniciar (`app/tareas.py`) |

## Pendiente (no implementado)

- Ganchos de pre-commit (opcional: los mismos controles corren en CI).
- Si el equipo aporta un design system propio, reemplaza la [guía de estilos](10-guia-de-estilos.md).
