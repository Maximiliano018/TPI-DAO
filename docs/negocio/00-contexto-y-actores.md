# 00. Contexto, actores y parámetros globales

## Dominio

Una **biblioteca** organizada como **red de sedes**. Cada sede conserva ejemplares físicos de un catálogo común de libros. El sistema reemplaza la gestión manual de socios, catálogo, préstamos, devoluciones y disponibilidad, y agrega el rasgo distintivo del dominio: el **préstamo interbibliotecario**, en el que un socio pide un ejemplar que está en otra sede y el sistema gestiona su traslado con trazabilidad.

Tareas habituales: controlar préstamos, devoluciones y disponibilidad de ejemplares.

## Actores

El enunciado distingue dos tipos de usuarios; el personal se divide en dos roles.

| Actor | Descripción | Estado |
|-------|-------------|--------|
| **Administrador** (personal de administración) | Gestiona la red: sedes, catálogo global, parámetros, usuarios del personal y reportes globales | Definido |
| **Bibliotecario** (personal operativo) | Opera en una sede: socios, préstamos, devoluciones, empaque y recepción de envíos | Definido |
| **Socio** | Consulta disponibilidad, pide préstamos para sí, reserva, ve sus préstamos y multas, paga sus multas en línea (simulado) y, si está dado de baja, pide su reactivación | Definido |
| **Visitante** (sin sesión) | Ve el inicio público: las cifras de la red y los libros más pedidos. No es un rol ni tiene cuenta; para operar, ingresa como alguno de los anteriores | Definido |

El bibliotecario siempre está asociado a **una sede activa**. El administrador no pertenece a ninguna y ve toda la red. El socio **no está vinculado a ninguna sede**: opera en toda la red.

### Permisos

Los roles son tres y fijos (los define el enunciado). Cada rol tiene un conjunto de **permisos** (consultar sedes básicas, administrar sedes, administrar usuarios, etc.) que se resuelve en el servidor; la matriz de abajo es su resumen. Un bibliotecario, además, solo opera sobre su propia sede.

La sesión dura 60 minutos (configurable por entorno). Si el usuario se da de baja o cambia de sede, el cambio rige desde su siguiente solicitud. El rol y el nombre de usuario no cambian después del alta.

## Matriz de permisos (resumen)

`A` = administra (alta/baja/modificación), `V` = consulta, `R` = registra la operación, `-` = sin acceso. «Su sede» = la sede del usuario.

| Recurso / acción | Administrador | Bibliotecario | Socio |
|------------------|:---:|:---:|:---:|
| Sedes | A | V (todas, datos básicos) | V (solo activas: dirección, contacto y horarios) |
| Usuarios del personal | A | - | - |
| Socios | A | A (alta/modificación), V | V (solo sus propios datos) |
| Libros (catálogo) | A | V | V |
| Ejemplares | A (en cualquier sede) | A (de su sede) | V (disponibilidad) |
| Préstamos | V (todos), R (en nombre del socio, en cualquier sede) | R (en nombre del socio, en su sede) | R (para sí, por libro), V (los propios) |
| Remitos | V (todos), R (desde cualquier sede: genera, despacha, recibe, anula), marca extraviado | R (su sede) | V (el estado del envío, dentro de sus préstamos) |
| Reservas | V (todas), R (en nombre del socio), cancela y entrega en cualquier sede | R (en nombre del socio), V (toda la red; por defecto su sede), cancela y entrega las de su sede | R (propias), cancela las propias |
| Devoluciones | V, R (en cualquier sede) | R (su sede) | - |
| Multas | V, cobra en el mostrador | V, cobra en el mostrador | V (propias), paga en línea las propias (simulado) |
| Reportes | todos | los operativos de su sede (R1, R4, R6) y R5 | R5 (disponibilidad) |
| Parámetros y tareas automáticas | A (modifica parámetros y ejecuta las tareas a mano) | - | - |
| Inicio público (cifras de la red y libros más pedidos) | V | V | V (también el visitante, sin sesión) |

El **administrador tiene los permisos completos**: administra la red y además opera en el mostrador de cualquier sede, indicando la sede en las operaciones nuevas (la de retiro de un préstamo, la de origen de un remito). Solo quedan fuera las acciones de autogestión del socio (pedir un préstamo para sí, pagar en línea), porque exigen una ficha de socio. Esta matriz se detalla en cada documento por proceso.

## Parámetros globales (configurables)

Valores iniciales **confirmados**. Se guardan como configuración (tabla `parametro`), no en el código, y los cambia el administrador desde la pantalla **Parámetros** del portal; rigen desde la siguiente operación. Cada cambio queda **auditado** (quién, cuándo, valor anterior y nuevo) en un historial que no se puede modificar, y la misma pantalla lo muestra.

Regla fija (no es un parámetro): el socio queda **inhabilitado** mientras tenga un préstamo vencido o una multa impaga, sin importar los días de atraso.

| Parámetro | Valor |
|-----------|-----------------|
| Plazo de préstamo local | 14 días corridos |
| Plazo de préstamo interbibliotecario | 21 días corridos, contados desde la entrega al socio en la sede destino |
| Renovaciones permitidas por préstamo | 1 (solo si no hay reservas pendientes sobre el libro) |
| Máximo de préstamos simultáneos por socio | 3 |
| Máximo de reservas activas por socio | 3 |
| Multa por día de atraso | $200 por día de atraso, monto fijo |
| Tope de multa por préstamo | 0 (sin tope); si se configura, la multa por atraso no lo supera |
| Multa por daño del ejemplar | 0 (no se cobra); si se configura, una devolución `Dañado` genera una multa por ese monto |
| Multa por extravío del ejemplar | 0 (no se cobra); si se configura, una devolución `Extraviado` genera una multa por ese monto |
| Vigencia de una reserva cumplida (retiro) | 3 días corridos |
| Plazo de despacho de un remito | 3 días corridos desde la generación; vencido, el remito figura atrasado |
| Plazo máximo de tránsito de un remito | 7 días corridos desde el despacho; vencido, se puede marcar como extraviado |
| Plazo para retirar un préstamo solicitado | 3 días corridos (el local, desde la solicitud; el interbibliotecario, desde la llegada a la sede destino) |

## Procesos automáticos

Tres tareas corren solas **todos los días a las 00:05** (hora de Córdoba) y una vez **al iniciar** el sistema, con las mismas reglas que si las hiciera una persona. El administrador también puede ejecutarlas a mano.

| Tarea | Qué hace |
|-------|----------|
| Detectar vencidos | Pasa a `Vencido` los préstamos activos cuyo plazo terminó e inhabilita a sus socios |
| Vencer retiros | Cancela los préstamos solicitados que el socio no retiró en el plazo de retiro (el ejemplar se libera o vuelve a su sede con un remito de retorno) |
| Vencer reservas | Vence las reservas disponibles para retiro que no se retiraron y ofrece el ejemplar a la siguiente de la cola |

En el historial, estos cambios figuran a nombre del **Sistema**.

## Principios transversales

1. **Libro ≠ ejemplar.** El libro es la obra (ISBN); el ejemplar es la copia física, con sede, código y estado propios.
2. **Origen y destino.** Origen = sede donde está el ejemplar. Destino = sede donde el socio lo retira y devuelve. En un préstamo local coinciden.
3. **Baja lógica.** Sedes, socios, usuarios y ejemplares no se borran: se dan de baja con estado, conservando el historial. Las únicas eliminaciones físicas son un libro cargado por error que no tiene ningún ejemplar y un cierre de sede (excepción de horario) de hoy o futuro.
4. **Trazabilidad.** Cada cambio de sede, socio, ejemplar, préstamo, remito y reserva queda en su historial con fecha, hora y responsable (una persona o el Sistema); los historiales no se pueden modificar.
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
| Multa | Sanción económica por devolución fuera de término, o por devolver el ejemplar dañado o extraviado |
| Incidencia | Extravío, daño o destrucción de un ejemplar o envío |
| Apartado | Estado del ejemplar retenido para un movimiento pendiente: un préstamo solicitado o su retorno a la sede propietaria |
| Traslado | Remito que cambia la sede propietaria de un ejemplar (sin préstamo) |
| Remito de retorno | Remito que el sistema genera para devolver un ejemplar a su sede propietaria |
| Plazo de retiro | Días que tiene el socio para retirar un préstamo solicitado o una reserva disponible |
| Pago | Registro del cobro de una multa (en el mostrador o en línea simulado), con su comprobante en PDF |
| Parámetro | Valor configurable del negocio (plazos, límites, montos) |
