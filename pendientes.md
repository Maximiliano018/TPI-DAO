# Pendientes y dudas abiertas

Todo lo que no está definido y condiciona [ARCHITECTURE.md](ARCHITECTURE.md) o [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md). Cada ítem indica la **propuesta actual** (la que usan los documentos hoy) y quién debe resolverlo.

Estado: ⏳ abierto · ✅ resuelto

## Dominio y reglas de negocio

| ID | Estado | Duda | Propuesta actual | Resuelve |
|---|---|---|---|---|
| PENDIENTE-1 | ⏳ | ¿El remito es por préstamo o puede agrupar varios ejemplares en un envío? | Un remito por préstamo/viaje (más simple, trazabilidad 1 a 1) | Cátedra / equipo |
| PENDIENTE-2 | ⏳ | ¿La devolución inter-sedes lleva remito propio de vuelta? | Sí, `Remito.sentido = VUELTA` hacia la sede propietaria | Cátedra / equipo |
| PENDIENTE-3 | ⏳ | **¿El socio debe poder ingresar al sistema para consultar disponibilidad, ver sus préstamos y crear reservas?** | No en esta versión: solo personal. Si se habilita, `Usuario` tendría `socio_id` opcional y rol `SOCIO`, y habría que sumar un portal y reglas de acceso a datos propios | Equipo |
| PENDIENTE-4 | ⏳ | ¿Qué ocurre con préstamos, reservas y remitos **en curso** cuando una sede se da de baja? | Se bloquea nuevas operaciones; las en curso deben finalizarse. Evaluar impedir la baja si hay remitos/préstamos abiertos | Equipo |
| PENDIENTE-5 | ⏳ | ¿La reserva es sobre un libro (cualquier ejemplar) o sobre un ejemplar concreto? | Sobre el libro, por sede, con cola FIFO | Equipo |
| PENDIENTE-6 | ⏳ | ¿Qué pasa con un ejemplar dañado, extraviado o destruido? ¿Se da de baja y se penaliza al socio? | Extraviado/destruido → ejemplar en `BAJA`. Dañado → `EN_REVISION`/baja según criterio. Penalización al socio sin definir | Equipo |
| PENDIENTE-7 | ⏳ | ¿Mantener "despachado" y "en tránsito" como estados separados? El enunciado habla de "empaquetar, despachar y recibir" y de "estados" | Un único estado `EN_TRANSITO` (despachar = acción). Evaluar con la cátedra, que dice evaluar críticamente el ciclo del remito | Cátedra |
| PENDIENTE-8 | ⏳ | Política de reservas: vigencia, orden, qué pasa si el socio no retira | FIFO; la reserva asignada vence a los N días (valor a definir) | Equipo |
| PENDIENTE-9 | ⏳ | Parámetros numéricos: plazo de préstamo, máx. de préstamos simultáneos por socio, monto de multa por día, tope de multa | Sin valores. Se configurarán como parámetros (`config`/tabla) y no hardcodeados | Equipo |
| PENDIENTE-10 | ⏳ | ¿Una multa pendiente inhabilita automáticamente al socio? ¿Se puede saldar la multa en el sistema? (pagos figuran fuera de alcance) | Multa pendiente inhabilita; saldar = marcar como `SALDADA` manualmente | Equipo |
| PENDIENTE-11 | ⏳ | ¿Se pueden prestar libros de "Consulta"? El enunciado habla de "libros y otros materiales de Consulta" | Solo libros; sin otros tipos de material en v1 | Cátedra |
| PENDIENTE-12 | ⏳ | ¿Se permite renovar un préstamo? | No en v1 | Equipo |
| PENDIENTE-13 | ⏳ | ¿Cómo y cuándo se marca un préstamo como `VENCIDO`? | Se calcula al consultar (`vencido(hoy)`); evaluar tarea programada si se necesita persistir | Equipo |

## Seguridad y usuarios

| ID | Estado | Duda | Propuesta actual | Resuelve |
|---|---|---|---|---|
| PENDIENTE-14 | ⏳ | Alta de usuarios: ¿quién los crea y cómo se crea el primer ADMIN? | ADMIN crea usuarios; el primer ADMIN se siembra con un script/migración | Equipo |
| PENDIENTE-15 | ⏳ | ¿Hay refresh token / cierre de sesión forzado / recuperación de contraseña? | Solo access token de vida corta; sin recuperación de contraseña en v1 | Equipo |
| PENDIENTE-16 | ⏳ | ¿Un usuario puede pertenecer a más de una sede o operar sobre varias? | Una sola sede por usuario (ADMIN sin restricción) | Equipo |
| PENDIENTE-17 | ⏳ | ¿Se requiere auditoría de acciones más allá del historial de remitos? | No en v1 | Equipo |

## Técnico

| ID | Estado | Duda | Propuesta actual | Resuelve |
|---|---|---|---|---|
| PENDIENTE-18 | ⏳ | Notificaciones: ¿canal real (email) o simulado? | Simuladas (registro en BD + log); sin envío real | Equipo |
| PENDIENTE-19 | ⏳ | ¿Hay despliegue / entrega con requisitos específicos (Docker, hosting)? | Ejecución local; `docker compose` opcional | Cátedra |
| PENDIENTE-20 | ⏳ | ¿La cátedra exige tests, diagramas UML o documentación específica en la entrega? | Tests de dominio + diagramas Mermaid en ARCHITECTURE.md | Cátedra |
| PENDIENTE-21 | ⏳ | Concurrencia: SQLite admite poca escritura simultánea. ¿Es relevante para la demo? | No; migrar a PostgreSQL si hiciera falta | Equipo |
| PENDIENTE-22 | ⏳ | Idioma de la API y la BD (español en nombres de entidades/tablas vs. inglés) | Dominio y UI en español; infraestructura genérica en inglés | Equipo |
| PENDIENTE-23 | ⏳ | Versiones exactas de Python, FastAPI, SQLAlchemy, React, Vite | Se fijan al crear el proyecto | Equipo |
| PENDIENTE-24 | ⏳ | Inventario con códigos (opcional): ¿generar códigos de barra/QR o solo texto único? | Código de inventario de texto único; sin barras/QR (opcional descartado) | Equipo |

## Design system

| ID | Estado | Duda | Propuesta actual | Resuelve |
|---|---|---|---|---|
| PENDIENTE-D1 | ⏳ | ¿Hay identidad visual previa (logo, colores institucionales)? | Paleta propia azul petróleo | Equipo |
| PENDIENTE-D2 | ⏳ | Validar contraste AA de todos los pares de colores (claro y oscuro) | Valores propuestos sin medir | Equipo |
| PENDIENTE-D3 | ⏳ | Librería de íconos | Lucide | Equipo |
| PENDIENTE-D4 | ⏳ | Fuentes: ¿Google Fonts o autoalojadas (offline)? | Google Fonts con fallback del sistema | Equipo |
| PENDIENTE-D5 | ⏳ | Idioma/formato de fechas y moneda en la UI (es-AR) | `es-AR`, fechas `dd/mm/aaaa`, moneda ARS | Equipo |
| PENDIENTE-D6 | ⏳ | ¿Dispositivos objetivo? (¿uso en tablet/móvil en mostrador?) | Escritorio primero, responsive básico | Equipo |
| PENDIENTE-D7 | ⏳ | ¿Se necesita documentar los componentes (Storybook) o basta con este documento? | Solo este documento | Equipo |

## Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React + Vite + TypeScript |
| Base de datos | SQLite + SQLAlchemy (+ Alembic) |
| Arquitectura backend | Capas con dominio puro (domain / application / infrastructure / api) |
| Estilos | CSS puro con tokens (custom properties) + CSS Modules |
| Estética | Sobria institucional, tema claro y oscuro |
| Usuarios (v1) | Solo personal: ADMIN, BIBLIOTECARIO, LOGISTICA |
| Alcance | Obligatorios + notificaciones + revisión de recepción; 4+ reportes |
