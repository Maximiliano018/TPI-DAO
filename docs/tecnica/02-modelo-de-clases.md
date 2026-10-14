# 02. Modelo de clases

Diagramas UML en Mermaid (se visualizan en GitHub). Muestran el dominio; los nombres siguen la convención T2 (dominio en español sin tildes). Los patrones se detallan en [Patrones de diseño](05-patrones-de-diseno.md).

## Entidades del dominio

```mermaid
classDiagram
    class Sede {
        +int id
        +str codigo
        +str nombre
        +Direccion direccion
        +Contacto contacto
        +EstadoSede estado
        +dar_de_baja(motivo)
        +reactivar()
        +esta_activa() bool
    }
    class HorarioSede {
        +DiaSemana dia
        +time apertura
        +time cierre
    }
    class Usuario {
        +int id
        +str username
        +Rol rol
        +bool activo
        +puede(accion) bool
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

    Sede "1" o-- "*" HorarioSede
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

Los estados de préstamo, ejemplar y reserva siguen la misma estructura que `EstadoRemito` (una clase por estado que define qué operaciones admite). Ver [Máquinas de estado](03-maquinas-de-estado.md).

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

Los servicios dependen de interfaces (`UnitOfWork`, repositorios) definidas en el dominio. Las implementaciones con SQLAlchemy viven en `infrastructure` y se inyectan, lo que permite probar los servicios con repositorios en memoria.
