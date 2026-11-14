# 02. Modelo de clases

Diagramas UML en Mermaid (se visualizan en GitHub). Muestran el dominio; los nombres siguen la convención T2 (dominio en español sin tildes). Los patrones se detallan en [Patrones de diseño](05-patrones-de-diseno.md).

## Entidades del dominio

```mermaid
classDiagram
    class Sede {
        +int id
        +CodigoSede codigo
        +str nombre
        +Direccion direccion
        +Contacto contacto
        +list~FranjaHoraria~ horarios
        +list~ExcepcionHorario~ excepciones
        +EstadoSede estado
        +int version
        +dar_de_baja(motivo, usuario, impedimentos)
        +reactivar(usuario)
        +modificar(datos, usuario)
        +reemplazar_horarios(franjas)
        +agregar_excepcion(excepcion, hoy)
        +quitar_excepcion(id, hoy)
        +esta_abierta(momento) bool
        +esta_activa() bool
        +validar_operativa()
    }
    class Direccion {
        <<value object>>
        +str calle
        +str numero
        +Localidad localidad
        +normalizada() str
    }
    class Contacto {
        <<value object>>
        +Telefono telefono
        +Email email
        +str responsable
    }
    class FranjaHoraria {
        <<value object>>
        +DiaSemana dia
        +time apertura
        +time cierre
        +se_solapa_con(otra) bool
    }
    class ExcepcionHorario {
        <<value object>>
        +date fecha
        +TipoExcepcion tipo
        +time desde
        +time hasta
        +str motivo
    }
    class EventoSede {
        +TipoEventoSede tipo
        +datetime fecha_hora
        +list~Cambio~ cambios
        +str motivo
    }
    class Impedimento {
        <<value object>>
        +TipoImpedimento tipo
        +int cantidad
        +list elementos
    }
    class VerificadorImpedimentoBaja {
        <<interface>>
        +verificar(sede_id) Impedimento
    }
    class VerificadorBajaSede {
        +verificar(sede_id) list~Impedimento~
    }
    class Usuario {
        +int id
        +str username
        +Rol rol
        +bool activo
        +int sede_id
        +puede(permiso) bool
        +opera_en(sede_id) bool
    }
    class Socio {
        +int id
        +str numero_socio
        +Documento documento
        +str nombre
        +str apellido
        +EstadoSocio estado
        +inhabilitar(motivo)
        +rehabilitar()
        +puede_pedir_prestamo() bool
        +dar_de_baja()
    }
    class Libro {
        +int id
        +str isbn
        +str titulo
        +str editorial
        +int anio_edicion
        +TipoMaterial tipo
    }
    class Autor {
        +int id
        +str nombre
    }
    class Categoria {
        +int id
        +str nombre
    }
    class Ejemplar {
        +int id
        +str codigo_inventario
        +EstadoFisico estado_fisico
        +EstadoEjemplar estado
        +apartar()
        +reservar()
        +prestar()
        +poner_en_transito()
        +liberar()
        +enviar_a_revision()
        +dar_de_baja(motivo)
        +pertenece_a(sede) bool
    }
    class Prestamo {
        +int id
        +str numero
        +TipoPrestamo tipo
        +EstadoPrestamo estado
        +date fecha_solicitud
        +date fecha_inicio
        +date fecha_vencimiento
        +date fecha_devolucion
        +int renovaciones
        +enviar()
        +entregar(fecha, politica_plazo)
        +renovar(politica_plazo)
        +marcar_vencido(hoy)
        +devolver(fecha)
        +cancelar()
        +dias_de_atraso(fecha) int
    }
    class Remito {
        +int id
        +str numero
        +MotivoRemito motivo
        +EstadoRemito estado
        +empaquetar(usuario)
        +despachar(usuario)
        +pasar_a_transito(usuario)
        +recibir(usuario)
        +anular(usuario, motivo)
        +marcar_extraviado(usuario)
        +registrar_dano(usuario, linea)
        +agregar_ejemplar(ejemplar, prestamo)
    }
    class DetalleRemito {
        +EstadoFisico estado_salida
        +EstadoFisico estado_llegada
        +str observacion
    }
    class MovimientoRemito {
        +EstadoRemito estado_anterior
        +EstadoRemito estado_nuevo
        +datetime fecha_hora
        +str observacion
    }
    class Reserva {
        +int id
        +str numero
        +EstadoReserva estado
        +datetime fecha_reserva
        +date vencimiento_retiro
        +asignar(ejemplar, hoy, vigencia)
        +cumplir()
        +cancelar()
        +vencer(hoy)
    }
    class Devolucion {
        +datetime fecha_hora
        +EstadoFisico estado_recibido
        +int dias_atraso
        +str observaciones
    }
    class Multa {
        +int id
        +int dias_atraso
        +Decimal monto_por_dia
        +Decimal monto_total
        +EstadoMulta estado
        +saldar()
    }
    class Incidencia {
        +TipoIncidencia tipo
        +OrigenIncidencia origen
        +str descripcion
        +datetime fecha
    }

    Sede "1" *-- "1..*" FranjaHoraria
    Sede "1" *-- "*" ExcepcionHorario
    Sede "1" *-- "1" Direccion
    Sede "1" *-- "1" Contacto
    Sede "1" --> "*" EventoSede : historial
    VerificadorBajaSede o-- "*" VerificadorImpedimentoBaja
    VerificadorImpedimentoBaja ..> Impedimento : produce
    Sede ..> Impedimento : rechaza la baja si hay
    Sede "1" --> "*" Ejemplar : propietaria
    Sede "1" --> "*" Usuario : bibliotecarios
    Libro "1" --> "*" Ejemplar
    Libro "*" --> "*" Autor
    Libro "*" --> "1" Categoria
    Socio "1" --> "*" Prestamo
    Socio "1" --> "*" Reserva
    Ejemplar "1" --> "*" Prestamo
    Prestamo "*" --> "1" Sede : origen
    Prestamo "*" --> "1" Sede : destino
    Prestamo "1" --> "0..1" Devolucion
    Devolucion "1" --> "0..1" Multa
    Remito "*" --> "1" Sede : origen
    Remito "*" --> "1" Sede : destino
    Remito "1" *-- "1..*" DetalleRemito
    Remito "1" *-- "*" MovimientoRemito
    DetalleRemito "*" --> "1" Ejemplar
    DetalleRemito "*" --> "0..1" Prestamo
    Reserva "*" --> "1" Libro
    Reserva "*" --> "1" Sede : retiro
    Reserva "*" --> "0..1" Ejemplar : asignado
    Incidencia "*" --> "1" Ejemplar
    Incidencia "*" --> "0..1" Socio
```

### Notas del modelo

- **La sede decide.** `Sede.dar_de_baja(...)` recibe los impedimentos ya calculados y lanza `SedeConActividadPendiente` si hay alguno; `Sede.validar_operativa()` lanza `SedeEnBaja` y es la guarda que usan los demás módulos antes de operar con una sede. `Sede.modificar`, `reemplazar_horarios`, `agregar_excepcion` y `quitar_excepcion` rechazan con `SedeEnBaja` si la sede está dada de baja.
- **Permisos.** `Permiso` es una enumeración y `ROL_PERMISOS` el mapa rol → permisos; `Usuario.puede(permiso)` consulta el mapa. Los roles son tres y fijos.
- **`esta_abierta(momento)`** combina horario semanal y excepciones en la zona de negocio; el reloj se inyecta.

- **Libro y ejemplar son clases distintas.** El libro es la obra; el ejemplar es la copia física con sede, estado físico y estado de disponibilidad.
- **Un préstamo tiene un solo ejemplar** y dos sedes: origen (donde está el ejemplar) y destino (donde lo retira el socio). En el préstamo local coinciden.
- **El remito agrupa ejemplares** mediante `DetalleRemito`; todos comparten origen y destino. Cada línea referencia su préstamo, salvo los traslados.
- **`MovimientoRemito`** es el historial que da la trazabilidad y alimenta los reportes de tránsito. Préstamo y ejemplar tienen historiales equivalentes (`MovimientoPrestamo`, `MovimientoEjemplar`).
- **`Multa`** nace al registrar una devolución fuera de término.
- Los **objetos de valor** (`Direccion`, `Contacto`, `Documento`, `Dinero`) son inmutables y se validan al construirlos.

## Estados, políticas y fábrica (patrones)

```mermaid
classDiagram
    class EstadoRemito {
        <<abstract>>
        +empaquetar(remito)
        +despachar(remito)
        +pasar_a_transito(remito)
        +recibir(remito)
        +anular(remito)
        +marcar_extraviado(remito)
        +registrar_dano(remito)
    }
    class Generado
    class Empaquetado
    class Despachado
    class EnTransito
    class Recibido
    class Extraviado
    class Danado
    class Destruido
    class Anulado
    EstadoRemito <|-- Generado
    EstadoRemito <|-- Empaquetado
    EstadoRemito <|-- Despachado
    EstadoRemito <|-- EnTransito
    EstadoRemito <|-- Recibido
    EstadoRemito <|-- Extraviado
    EstadoRemito <|-- Danado
    EstadoRemito <|-- Destruido
    EstadoRemito <|-- Anulado
    Remito --> EstadoRemito : estado actual

    class PoliticaMulta {
        <<interface>>
        +calcular(dias_atraso) Dinero
    }
    class MultaFijaPorDia {
        +Dinero monto_por_dia
        +Dinero tope
    }
    PoliticaMulta <|.. MultaFijaPorDia

    class PoliticaPlazo {
        <<interface>>
        +vencimiento(inicio) date
    }
    class PlazoLocal
    class PlazoInterbibliotecario
    PoliticaPlazo <|.. PlazoLocal
    PoliticaPlazo <|.. PlazoInterbibliotecario

    class PrestamoFactory {
        +crear(socio, ejemplar, sede_destino, parametros) Prestamo
    }
    PrestamoFactory ..> Prestamo : crea
    PrestamoFactory ..> PoliticaPlazo : elige
    Prestamo ..> PoliticaPlazo
    Devolucion ..> PoliticaMulta
```

Los estados de préstamo, ejemplar y reserva siguen la misma estructura que `EstadoRemito` (una clase por estado que define qué operaciones admite). Ver [Máquinas de estado](03-maquinas-de-estado.md). La sede no usa State: su estado es el enum `EstadoSede` ([por qué](05-patrones-de-diseno.md#por-qué-la-sede-no-usa-state)).

La verificación de baja de sede (Strategy + Composite: `VerificadorImpedimentoBaja`, sus seis verificadores concretos y el compuesto `VerificadorBajaSede`) tiene su diagrama y la tabla de roles en [Patrones de diseño](05-patrones-de-diseno.md#10-strategy--composite-verificación-de-baja-de-sede).

## Capa de aplicación y persistencia

```mermaid
classDiagram
    class PrestamoService {
        +registrar(datos, usuario) Prestamo
        +entregar(id, usuario)
        +renovar(id, usuario)
        +cancelar(id, usuario)
        +detectar_vencidos(hoy)
    }
    class RemitoService {
        +generar(datos, usuario) Remito
        +empaquetar(id, usuario)
        +despachar(id, usuario)
        +recibir(id, lineas, usuario)
        +anular(id, motivo, usuario)
    }
    class DevolucionService {
        +registrar(prestamo_id, datos, usuario) Devolucion
        +saldar_multa(multa_id, usuario)
    }
    class ReservaService
    class UnitOfWork {
        <<interface>>
        +prestamos PrestamoRepository
        +remitos RemitoRepository
        +ejemplares EjemplarRepository
        +commit()
        +rollback()
    }
    class PrestamoRepository {
        <<interface>>
        +obtener(id) Prestamo
        +guardar(prestamo)
        +abiertos_de_socio(socio_id) list
        +vencidos(hoy) list
    }
    class SqlAlchemyUnitOfWork
    class SqlAlchemyPrestamoRepository
    PrestamoService --> UnitOfWork
    RemitoService --> UnitOfWork
    DevolucionService --> UnitOfWork
    ReservaService --> UnitOfWork
    UnitOfWork --> PrestamoRepository
    UnitOfWork <|.. SqlAlchemyUnitOfWork
    PrestamoRepository <|.. SqlAlchemyPrestamoRepository
```

Los servicios dependen de interfaces (`UnitOfWork`, repositorios) definidas en el dominio. Las implementaciones con SQLAlchemy viven en `repositories/impl` y se inyectan, lo que permite probar los servicios con repositorios en memoria.
