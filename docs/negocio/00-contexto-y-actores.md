# 00. Contexto, actores y parámetros globales

## Dominio

Una **biblioteca** organizada como **red de sedes**. Cada sede conserva ejemplares físicos de un catálogo común de libros. El sistema reemplaza la gestión manual de socios, catálogo, préstamos, devoluciones y disponibilidad, y agrega el rasgo distintivo del dominio: el **préstamo interbibliotecario**, en el que un socio pide un ejemplar que está en otra sede y el sistema gestiona su traslado con trazabilidad.

Tareas habituales: controlar préstamos, devoluciones y disponibilidad de ejemplares.

## Actores

El enunciado distingue dos tipos de usuarios; el personal se divide en dos roles.

| Actor | Descripción | Estado |
|-------|-------------|--------|
| **Administrador** (personal de administración) | Gestiona la red: sedes, catálogo global, parámetros, usuarios del personal y reportes globales | Propuesta |
| **Bibliotecario** (personal operativo) | Opera en una sede: socios, préstamos, devoluciones, empaque y recepción de envíos | Propuesta |
| **Socio** | Consulta disponibilidad, reserva, ve sus préstamos y multas | Propuesta |

El bibliotecario siempre está asociado a **una sede**. El administrador no pertenece a ninguna y ve toda la red.

## Matriz de permisos (resumen)

`A` = administra (alta/baja/modificación), `V` = consulta, `R` = registra la operación, `-` = sin acceso. «Su sede» = la sede del usuario.

| Recurso / acción | Administrador | Bibliotecario | Socio |
|------------------|:---:|:---:|:---:|
| Sedes | A | V (todas, datos básicos) | V (datos de contacto y horarios) |
| Socios | A | A (alta/modificación), V | V (solo sus propios datos) |
| Libros (catálogo) | A | V | V |
| Ejemplares | A | A (de su sede) | V (disponibilidad) |
| Préstamos | V (todos) | R (su sede) | V (los propios) |
| Remitos | V (todos) | R (su sede) | V (los de sus préstamos) |
| Reservas | V (todas) | R (en nombre del socio), V (su sede) | R (propias) |
| Devoluciones | V | R (su sede) | - |
| Reportes | todos | los operativos de su sede | - |

Esta matriz se detalla en cada documento por proceso.

## Parámetros globales (configurables)

Valores iniciales **propuestos**. Se guardan como configuración, no en el código.

| Parámetro | Valor propuesto |
|-----------|-----------------|
| Plazo de préstamo local | 14 días corridos |
| Plazo de préstamo interbibliotecario | 21 días corridos, contados desde la recepción en la sede destino |
| Renovaciones permitidas por préstamo | 1 (solo si no hay reservas pendientes sobre el libro) |
| Máximo de préstamos simultáneos por socio | 3 |
| Multa por día de atraso | monto fijo por día (valor a definir por el equipo) |
| Vigencia de una reserva cumplida (retiro) | 3 días corridos |
| Días de atraso que inhabilitan al socio | el socio queda inhabilitado mientras tenga un préstamo vencido o una multa impaga |

## Principios transversales

1. **Libro ≠ ejemplar.** El libro es la obra (ISBN); el ejemplar es la copia física, con sede, código y estado propios.
2. **Origen y destino.** Origen = sede donde está el ejemplar. Destino = sede donde el socio lo retira y devuelve. En un préstamo local coinciden.
3. **Baja lógica.** Nada se borra físicamente: sedes, socios y ejemplares se dan de baja con estado, conservando el historial.
4. **Trazabilidad.** Cada cambio de estado de remito, préstamo y ejemplar queda registrado con fecha, hora y responsable.
5. **Lógica en el dominio.** Las reglas viven en el modelo, no en la interfaz.

## Glosario

| Término | Significado |
|---------|-------------|
| Sede | Biblioteca física que integra la red |
| Socio | Persona registrada que puede pedir material |
| Libro | Obra del catálogo, identificada por ISBN |
| Ejemplar | Copia física de un libro, con código de inventario único y sede propietaria |
| Préstamo local | Origen y destino son la misma sede |
| Préstamo interbibliotecario | Origen y destino distintos; requiere envío |
| Remito | Comprobante del envío de ejemplares entre sedes, con estados y trazabilidad |
| Reserva | Espera ordenada por un libro no disponible |
| Multa | Sanción económica por devolución fuera de término |
| Incidencia | Extravío, daño o destrucción de un ejemplar o envío |
