# 02. Modelo de clases

Diagramas UML en Mermaid (se visualizan en GitHub) de las clases reales de `backend/app/models/`, `services/` y `repositories/`. Muestran los atributos y operaciones públicos más relevantes; los nombres siguen la convención T2 (dominio en español sin tildes). Los patrones se detallan en [Patrones de diseño](05-patrones-de-diseno.md) y las tablas, en el [diccionario de datos](../../database/diccionario-de-datos.md).

## Sedes, usuarios y socios

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
        +DatosBaja baja
        +int version
        +crear(...)$ Sede
        +modificar(..., horarios, actor, ahora)
        +dar_de_baja(motivo, actor, ahora, impedimentos)
        +reactivar(actor, ahora)
        +agregar_excepciones(nuevas, actor, ahora, hoy)
        +quitar_excepcion(id, actor, ahora, hoy)
        +esta_abierta(momento_local) bool
        +excepciones_vigentes(hoy) list
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
        +int dia_semana
        +time apertura
        +time cierre
    }
    class ExcepcionHorario {
        <<value object>>
        +date fecha
        +TipoExcepcion tipo
        +time hora_desde
        +time hora_hasta
        +str motivo
    }
    class EventoSede {
        +TipoEventoSede tipo
        +datetime fecha_hora
        +list~Cambio~ cambios
        +str motivo
    }
    class Usuario {
        +int id
        +str username
        +str nombre
        +Rol rol
        +bool activo
        +SedeRef sede
        +int socio_id
        +crear_personal(...)$ Usuario
        +crear_cuenta_socio(...)$ Usuario
        +modificar(nombre, sede, actor, ahora)
        +dar_de_baja(actor, ahora)
        +reactivar(actor, ahora)
        +puede(permiso) bool
        +exigir(permiso)
        +opera_en(sede_id) bool
    }
    class Socio {
        +int id
        +str numero_socio
        +DatosPersonales datos
        +int sede_alta_id
        +EstadoSocio estado
        +set~MotivoInhabilitacion~ causas
        +TipoBaja tipo_baja
        +SolicitudReactivacion solicitud
        +registrar(...)$ Socio
        +modificar(datos, actor, ahora)
        +reevaluar(situacion, actor, ahora, origen)
        +inhabilitar(motivo, actor, ahora)
        +rehabilitar(situacion, actor, es_administrador, ahora)
        +dar_de_baja(situacion, tipo, motivo, actor, es_administrador, ahora)
        +solicitar_reactivacion(mensaje, actor, ahora)
        +rechazar_solicitud(motivo, actor, es_administrador, ahora)
        +reactivar(actor, es_administrador, ahora, origen)
        +validar_puede_operar()
    }
    class DatosPersonales {
        <<value object>>
        +Documento documento
        +str nombre
        +str apellido
        +date fecha_nacimiento
        +Email email
        +Telefono telefono
    }
    Sede "1" *-- "1..*" FranjaHoraria
    Sede "1" *-- "*" ExcepcionHorario
    Sede "1" *-- "1" Direccion
    Sede "1" *-- "1" Contacto
    Sede "1" --> "*" EventoSede : historial
    Usuario "*" --> "0..1" Sede : bibliotecario de
    Usuario "0..1" --> "0..1" Socio : cuenta de
    Socio "1" *-- "1" DatosPersonales
```

## Catálogo

```mermaid
classDiagram
    class Libro {
        +int id
        +DatosLibro datos
        +int version
        +crear(datos, actor, ahora)$ Libro
        +modificar(datos, actor, ahora)
        +validar_version(version)
        +eliminable() bool
    }
    class DatosLibro {
        <<value object>>
        +Isbn isbn
        +str titulo
        +tuple~str~ autores
        +str editorial
        +int anio_edicion
        +CategoriaRef categoria
        +TipoMaterial tipo_material
        +clave_natural() str
    }
    class CategoriaRef {
        <<value object>>
        +int id
        +str nombre
    }
    class Ejemplar {
        +int id
        +str codigo_inventario
        +int libro_id
        +int sede_propietaria_id
        +int sede_actual_id
        +EstadoFisico estado_fisico
        +EstadoEjemplar estado
        +int version
        +registrar(...)$ Ejemplar
        +apartar(actor, ahora, obs)
        +reservar(actor, ahora, obs)
        +prestar(actor, ahora, obs)
        +poner_en_transito(actor, ahora, obs)
        +recibir_en(sede_id, estado_fisico, trasladar, actor, ahora, obs)
        +liberar(actor, ahora, obs)
        +enviar_a_revision(actor, ahora, obs)
        +reparar(actor, ahora)
        +dar_de_baja(motivo, actor, ahora)
        +registrar_baja(motivo, actor, ahora)
        +recuperar(estado_fisico, observacion, actor, ahora)
        +pertenece_a(sede_id) bool
    }
    class MovimientoEjemplar {
        +EstadoEjemplarEnum estado_anterior
        +EstadoEjemplarEnum estado_nuevo
        +datetime fecha_hora
        +tuple~Cambio~ cambios
    }
    Libro "1" *-- "1" DatosLibro
    DatosLibro --> CategoriaRef
    Libro "1" --> "*" Ejemplar
    Ejemplar "1" *-- "*" MovimientoEjemplar : historial
```

Los autores son una lista de nombres dentro de `DatosLibro`; en la base son las tablas `autor` y `libro_autor`, y la categoría sale del catálogo cerrado `categoria`.

## Préstamos, remitos y reservas

```mermaid
classDiagram
    class Prestamo {
        +int id
        +str numero
        +TipoPrestamo tipo
        +int socio_id
        +int ejemplar_id
        +int libro_id
        +int sede_origen_id
        +int sede_destino_id
        +EstadoPrestamo estado
        +datetime fecha_solicitud
        +date fecha_inicio
        +date fecha_vencimiento
        +datetime fecha_devolucion
        +date fecha_limite_retiro
        +int renovaciones
        +registrar_alta(actor, ahora)
        +habilitar_retiro(hasta, actor, ahora)
        +enviar(actor, ahora, remito)
        +entregar(hoy, politica, actor, ahora)
        +renovar(hoy, politica, maximo, hay_reservas, actor, ahora)
        +marcar_vencido(hoy, ahora) bool
        +devolver(fecha, actor, ahora, observacion)
        +cancelar(motivo, actor, ahora)
        +dias_de_atraso(fecha) int
        +retiro_vencido(hoy) bool
    }
    class Remito {
        +int id
        +str numero
        +int sede_origen_id
        +int sede_destino_id
        +MotivoRemito motivo
        +list~LineaRemito~ lineas
        +EstadoRemito estado
        +datetime fecha_despacho
        +datetime fecha_recepcion
        +int version
        +generar(...)$ Remito
        +empaquetar(actor, ahora)
        +despachar(actor, ahora)
        +pasar_a_transito(actor, ahora)
        +recibir(recepcion, actor, ahora)
        +anular(motivo, actor, ahora)
        +marcar_extraviado(plazo_dias, observacion, actor, ahora)
        +limite_de_despacho(plazo, zona) date
    }
    class LineaRemito {
        +int ejemplar_id
        +int prestamo_id
        +EstadoFisico estado_fisico_salida
        +EstadoFisico estado_fisico_llegada
        +ResultadoLinea resultado
        +str observacion
    }
    class MovimientoRemito {
        +EstadoRemitoEnum estado_anterior
        +EstadoRemitoEnum estado_nuevo
        +datetime fecha_hora
        +str observacion
    }
    class Incidencia {
        +TipoIncidencia tipo
        +OrigenIncidencia origen
        +int ejemplar_id
        +int socio_id
        +int remito_id
        +int sede_responsable_id
        +str descripcion
        +de_remito(...)$ Incidencia
        +resolver(resolucion, actor, ahora)
    }
    class Reserva {
        +int id
        +str numero
        +int socio_id
        +int libro_id
        +int sede_retiro_id
        +EstadoReserva estado
        +datetime fecha_reserva
        +int ejemplar_id
        +date vencimiento_retiro
        +int prestamo_id
        +registrar(...)$ Reserva
        +asignar(ejemplar_id, hoy, vigencia_dias, ahora, codigo)
        +convertir_en_prestamo(ejemplar_id, prestamo_id, ahora, numero)
        +cumplir(prestamo_id, actor, ahora, numero)
        +vencer(hoy, ahora) bool
        +cancelar(ahora, actor, motivo)
    }
    Prestamo "*" --> "1" Ejemplar
    Remito "1" *-- "1..*" LineaRemito
    Remito "1" *-- "*" MovimientoRemito : historial
    LineaRemito "*" --> "0..1" Prestamo
    Incidencia "*" --> "0..1" Remito
    Incidencia "*" --> "0..1" Prestamo
    Reserva "*" --> "0..1" Prestamo : se cumple con
```

## Devoluciones, multas y pagos

```mermaid
classDiagram
    class Devolucion {
        +int id
        +int prestamo_id
        +int sede_id
        +datetime fecha_hora
        +EstadoRecibido estado_recibido
        +int dias_atraso
        +str observaciones
        +datetime registrada_en
        +str motivo_fecha
        +registrar(prestamo, ..., politica, politica_incidencia)$ tuple
        +texto_del_historial(devuelto, registro) str
    }
    class Multa {
        +int id
        +int prestamo_id
        +int socio_id
        +TipoMulta tipo
        +int dias_atraso
        +Decimal monto_por_dia
        +Decimal monto_total
        +EstadoMulta estado
        +concepto() str
        +saldar(actor, ahora)
    }
    class Pago {
        +int id
        +int multa_id
        +MedioPago medio
        +EstadoPago estado
        +Decimal monto
        +FormaEnLinea forma_en_linea
        +str tarjeta_ultimos4
        +datetime acreditado_en
        +manual(multa_id, monto, medio, comprobante, actor, ahora)$ Pago
        +en_linea(multa_id, monto, actor, ahora)$ Pago
        +pagar_en_linea(forma, tarjeta_ultimos4, ahora) bool
        +aprobar(ahora)
        +rechazar(motivo)
        +cancelar(motivo)
        +numero_comprobante() str
    }
    class TipoMulta {
        <<enumeration>>
        ATRASO
        DANIO
        EXTRAVIO
    }
    class MedioPago {
        <<enumeration>>
        EFECTIVO
        DEBITO
        CREDITO
        TRANSFERENCIA
        EN_LINEA
        NO_REGISTRADO
    }
    class EstadoPago {
        <<enumeration>>
        PENDIENTE
        APROBADO
        RECHAZADO
        CANCELADO
    }
    class FormaEnLinea {
        <<enumeration>>
        TARJETA_CREDITO
        TARJETA_DEBITO
        DINERO_EN_CUENTA
    }
    Prestamo "1" --> "0..1" Devolucion
    Prestamo "1" --> "*" Multa : una por tipo
    Multa "1" --> "*" Pago : un solo aprobado
    Multa --> TipoMulta
    Pago --> MedioPago
    Pago --> EstadoPago
    Pago --> FormaEnLinea
```

### Notas del modelo

- **La sede decide.** `Sede.dar_de_baja(...)` recibe los impedimentos ya calculados y lanza `SedeConActividadPendiente` si hay alguno; `Sede.validar_operativa()` lanza `SedeEnBaja` y es la guarda que usan los demás módulos antes de operar con una sede. Los horarios se reemplazan con `Sede.modificar(..., horarios=...)`; `modificar`, `agregar_excepciones` y `quitar_excepcion` rechazan con `SedeEnBaja` si la sede está dada de baja.
- **Permisos.** `Permiso` es una enumeración y `ROL_PERMISOS` el mapa rol → permisos (`models/usuario.py`); `Usuario.puede(permiso)` consulta el mapa y `exigir` lanza `PermisoDenegado`. Los roles son tres y fijos; el rol y el usuario no cambian después del alta.
- **`esta_abierta(momento_local)`** combina horario semanal y excepciones en la zona de negocio; el reloj se inyecta.
- **El socio se reevalúa.** `Socio.reevaluar(situacion, ...)` recalcula las causas automáticas (préstamo vencido, multa impaga) a partir de una `SituacionSocio`; la inhabilitación administrativa solo la decide el administrador.
- **Libro y ejemplar son clases distintas.** El libro es la obra; el ejemplar es la copia física con sede propietaria, sede actual, estado físico y estado de disponibilidad.
- **Un préstamo tiene un solo ejemplar** y dos sedes: origen (donde está el ejemplar) y destino (donde lo retira el socio). En el préstamo local coinciden.
- **El remito agrupa ejemplares** con `LineaRemito`; todos comparten origen y destino. Cada línea referencia su préstamo, salvo los traslados. La recepción llega como una lista de `RecepcionLinea` (estado físico, destruido o faltante).
- **Historiales.** Remito, préstamo, ejemplar y reserva acumulan `movimientos_pendientes` (`MovimientoRemito`, `MovimientoPrestamo`, `MovimientoEjemplar`, `MovimientoReserva`) y sede y socio, `eventos_pendientes`; el repositorio los guarda en tablas de solo inserción.
- **`Multa`** cuelga del préstamo: nace al registrar la devolución, por atraso (con días y monto por día) o por daño o extravío (monto fijo); un préstamo tiene a lo sumo una de cada tipo. Se salda con un `Pago` aprobado, del mostrador (`Pago.manual`) o en línea simulado (`Pago.en_linea` y `pagar_en_linea`).
- Los **objetos de valor** (`CodigoSede`, `Direccion`, `Contacto`, `Telefono`, `Email`, `FranjaHoraria`, `ExcepcionHorario`, `Documento`, `DatosPersonales`, `Isbn`, `DatosLibro`) son inmutables y se validan al construirlos. Los montos son `Decimal`.

## Estados, políticas y fábrica (patrones)

```mermaid
classDiagram
    class EstadoRemito {
        <<abstract>>
        +nombre: EstadoRemitoEnum
        +empaquetar() EstadoRemito
        +despachar() EstadoRemito
        +pasar_a_transito() EstadoRemito
        +recibir() EstadoRemito
        +recibir_con_dano() EstadoRemito
        +recibir_destruido() EstadoRemito
        +recibir_con_faltantes() EstadoRemito
        +anular() EstadoRemito
        +marcar_extraviado() EstadoRemito
    }
    EstadoRemito <|-- Generado
    EstadoRemito <|-- Empaquetado
    EstadoRemito <|-- Despachado
    EstadoRemito <|-- EnTransito
    EstadoRemito <|-- Recibido
    EstadoRemito <|-- Danado
    EstadoRemito <|-- Destruido
    EstadoRemito <|-- Incompleto
    EstadoRemito <|-- Extraviado
    EstadoRemito <|-- Anulado
    Remito --> EstadoRemito : estado actual

    class PoliticaMulta {
        <<interface>>
        +monto_por_dia: Decimal
        +calcular(dias_atraso) Decimal
    }
    class MultaFijaPorDia {
        +Decimal monto_por_dia
        +Decimal tope
    }
    PoliticaMulta <|.. MultaFijaPorDia

    class PoliticaMultaPorIncidencia {
        <<interface>>
        +calcular(tipo) Decimal
    }
    class MontoFijoPorIncidencia {
        +Decimal danio
        +Decimal extravio
    }
    PoliticaMultaPorIncidencia <|.. MontoFijoPorIncidencia

    class PoliticaPlazo {
        <<interface>>
        +dias: int
        +vencimiento(inicio) date
    }
    PoliticaPlazo <|.. PlazoEnDias
    PlazoEnDias <|-- PlazoLocal
    PlazoEnDias <|-- PlazoInterbibliotecario

    class PrestamoFactory {
        +PrestamoFactory(parametros)
        +politica(tipo) PoliticaPlazo
        +validar_socio(socio, abiertos_del_socio, libro_id)
        +limite_de_retiro(desde) date
        +crear(numero, socio, ejemplar, sede_origen, sede_destino, abiertos_del_socio, actor, ahora, reservado, hoy) Prestamo
    }
    PrestamoFactory ..> Prestamo : crea
    PrestamoFactory ..> PoliticaPlazo : elige
    Prestamo ..> PoliticaPlazo
    Devolucion ..> PoliticaMulta
    Devolucion ..> PoliticaMultaPorIncidencia
```

Los estados de préstamo, ejemplar y reserva siguen la misma estructura que `EstadoRemito`: una clase por estado que define qué operaciones admite y devuelve el estado siguiente. Ver [Máquinas de estado](03-maquinas-de-estado.md). La sede no usa State: su estado es el enum `EstadoSede` ([por qué](05-patrones-de-diseno.md#por-qué-la-sede-no-usa-state)).

La verificación de baja de sede (Strategy + Composite: `VerificadorImpedimentoBaja`, sus seis verificadores concretos y el compuesto `VerificadorBajaSede`) tiene su diagrama y la tabla de roles en [Patrones de diseño](05-patrones-de-diseno.md#4-strategy--composite-verificación-de-baja-de-sede).

## Capa de aplicación y persistencia

```mermaid
classDiagram
    class PrestamoService {
        +registrar(actor, socio_id, ejemplar_id, sede_destino_id) Prestamo
        +proponer(actor, libro_id, sede_destino_id, socio_id)
        +solicitar(actor, libro_id, sede_destino_id, socio_id, sede_origen_esperada_id) Prestamo
        +entregar(actor, id)
        +renovar(actor, id)
        +cancelar(actor, id, motivo)
        +vencer_retiros(actor) int
        +detectar_vencidos(actor) int
        +detalle(actor, id)
        +listar(actor, ...)
    }
    class RemitoService {
        +generar(actor, sede_destino_id, motivo, lineas, observaciones) Remito
        +generar_retorno(prestamo, ejemplar, actor) Remito
        +empaquetar(actor, id)
        +despachar(actor, id)
        +pasar_a_transito(actor, id)
        +recibir(actor, id, recepcion)
        +anular(actor, id, motivo)
        +marcar_extraviado(actor, id, observacion)
    }
    class DevolucionService {
        +registrar(actor, prestamo_id, estado, observaciones, fecha_hora, motivo_fecha)
        +listar_multas(actor, socio_id, estado, page, size)
    }
    class PagoService {
        +saldar_en_mostrador(actor, multa_id, medio, comprobante) Multa
        +iniciar_en_linea(actor, multa_id) Pago
        +pagar_en_linea(actor, pago_id, forma, tarjeta_ultimos4) Pago
        +comprobante(actor, pago_id) tuple
        +detalle(actor, pago_id) Pago
    }
    class ReservaService {
        +reservar(actor, libro_id, sede_retiro_id, socio_id)
        +retirar(actor, id)
        +cancelar(actor, id, motivo)
        +vencer_reservas(actor) int
    }
    class UnitOfWork {
        <<interface>>
        +prestamos PrestamoRepository
        +remitos RemitoRepository
        +ejemplares EjemplarRepository
        +multas MultaRepository
        +pagos PagoRepository
        +commit()
        +rollback()
    }
    class PrestamoRepository {
        <<interface>>
        +obtener(id) Prestamo
        +obtener_para_modificar(id) Prestamo
        +agregar(prestamo)
        +guardar(prestamo)
        +abiertos_de_socio(socio_id) list
        +activos_vencidos(hoy) list
        +retiros_vencidos(hoy) list
        +en_curso_de_sede(sede_id)
    }
    class SqlAlchemyUnitOfWork
    class SqlAlchemyPrestamoRepository
    PrestamoService --> UnitOfWork
    RemitoService --> UnitOfWork
    DevolucionService --> UnitOfWork
    PagoService --> UnitOfWork
    ReservaService --> UnitOfWork
    UnitOfWork --> PrestamoRepository
    UnitOfWork <|.. SqlAlchemyUnitOfWork
    PrestamoRepository <|.. SqlAlchemyPrestamoRepository
```

Los servicios dependen de interfaces (`Protocol`): la `UnitOfWork` (`repositories/unit_of_work.py`) y los repositorios (`repositories/interfaces/`). Las implementaciones con SQLAlchemy viven en `repositories/impl/` y se inyectan, lo que permite probar los servicios con repositorios en memoria (`tests/fakes/`). El resto de los servicios (sedes, socios, usuarios, catálogo, parámetros, reportes) sigue la misma estructura.
