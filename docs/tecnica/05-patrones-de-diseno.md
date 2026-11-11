# 05. Patrones de diseño

El enunciado exige **al menos dos patrones**. Este documento analiza los que encajan en el dominio, qué problema resuelve cada uno, su ventaja y su costo, y cuáles se implementan.

## Resumen

| # | Patrón | Dónde | Prioridad | Implementar |
|---|--------|-------|-----------|-------------|
| 1 | State | Ciclo de vida de remito, préstamo, ejemplar y reserva | Alta | Sí |
| 2 | Strategy | Cálculo de multa y plazo de préstamo | Alta | Sí |
| 3 | Factory | Creación de préstamo local o interbibliotecario | Alta | Sí |
| 4 | Repository | Acceso a datos | Alta | Sí |
| 5 | Unit of Work | Transacción por caso de uso | Media | Sí |
| 6 | Observer (eventos de dominio) | Notificaciones | Media | Opcional |
| 7 | Chain of Responsibility / Specification | Validaciones de préstamo | Baja | Opcional |
| 8 | Dependency Injection | Servicios y repositorios | Alta | Sí (FastAPI lo trae) |
| 9 | Facade | Servicios de aplicación | Media | Sí, de forma natural |
| 10 | Strategy + Composite | Verificación de impedimentos de baja de sede | Alta | Sí |
| 11 | Value Object | Dirección, contacto, código de sede, franja horaria | Media | Sí |

**Propuesta:** los cuatro primeros más Unit of Work. Superan el mínimo de dos con holgura, y cada uno responde a un problema real del dominio y no se agrega por cumplir.

---

## 1. State (Estado)

**Problema.** El remito pasa por nueve estados con transiciones estrictas («sin saltos ni retrocesos»), y el préstamo, el ejemplar y la reserva también. Con `if estado == ...` repartidos por el código, cada regla nueva obliga a revisar todo, y es fácil permitir una transición inválida.

**Solución.** Cada estado es una clase que implementa solo las operaciones que admite; las demás lanzan `TransicionInvalida`. La entidad delega en su estado actual.

```python
class EstadoRemito(ABC):
    nombre: EstadoRemitoEnum

    def empaquetar(self, remito): raise TransicionInvalida(self.nombre, "empaquetar")
    def despachar(self, remito):  raise TransicionInvalida(self.nombre, "despachar")
    def recibir(self, remito):    raise TransicionInvalida(self.nombre, "recibir")
    # ...el resto por defecto también rechaza

class Generado(EstadoRemito):
    def empaquetar(self, remito):
        remito._cambiar_a(Empaquetado())

class Empaquetado(EstadoRemito):
    def despachar(self, remito):
        remito._cambiar_a(Despachado())
```

**Ventajas.**

- Las transiciones válidas quedan explícitas y verificables en un solo lugar por estado; las inválidas se rechazan por defecto.
- Agregar un estado no obliga a tocar los demás ni los clientes.
- Cada estado se prueba aislado, que se alinea con los criterios `CA-REM-04` a `CA-REM-06`.
- Responde directamente al requisito que la cátedra evalúa críticamente: el ciclo de vida del remito.

**Costos.** Más clases (una por estado) y hace falta convertir entre la clase y el valor guardado en la base (el repositorio mapea `EstadoRemitoEnum ↔ clase`).

**Alternativa.** Una tabla de transiciones permitidas (`dict`) con un enum. Es más corta, pero deja el comportamiento por estado repartido en condicionales; conviene solo si los estados no tienen lógica propia, que no es el caso del remito.

---

## 2. Strategy (Estrategia)

**Problema.** El monto de la multa y el plazo de préstamo son políticas que cambian (monto por día hoy, escalonado mañana; 14 o 21 días según el tipo). Si el cálculo está dentro de `Devolucion` o `Prestamo`, cada cambio de política obliga a modificar esas clases.

**Solución.** Una interfaz por política y una implementación por variante, elegidas por configuración.

```python
class PoliticaMulta(Protocol):
    def calcular(self, dias_atraso: int) -> Decimal: ...

class MultaFijaPorDia:
    def __init__(self, monto_por_dia: Decimal, tope: Decimal | None = None): ...
    def calcular(self, dias_atraso: int) -> Decimal:
        total = self.monto_por_dia * dias_atraso
        return min(total, self.tope) if self.tope else total

class PoliticaPlazo(Protocol):
    def vencimiento(self, inicio: date) -> date: ...
# PlazoLocal (14 días) y PlazoInterbibliotecario (21 días)
```

**Ventajas.**

- Cambiar o sumar una política (multa escalonada, plazo por categoría de libro) no toca el dominio existente (principio abierto/cerrado).
- Se prueba cada política sin base ni préstamo: `CA-DEV-06` y `CA-DEV-07`.
- Los valores salen de la tabla `parametro`, así el administrador los ajusta sin cambiar código.

**Costos.** Una abstracción más; se justifica porque el negocio ya declaró que estas reglas son configurables.

---

## 3. Factory (Fábrica)

**Problema.** Un préstamo local y uno interbibliotecario se crean con reglas distintas: el local exige origen igual a destino, no genera remito y usa el plazo local; el interbibliotecario exige sedes distintas, genera envío y usa otro plazo. Repetir esa decisión en cada servicio duplica las reglas.

**Solución.** `PrestamoFactory.crear(...)` decide el tipo según las sedes, construye el préstamo en estado `Solicitado` con la `PoliticaPlazo` correspondiente y garantiza sus invariantes.

**Ventajas.**

- Un único punto donde se decide «local o interbibliotecario», que respalda `CA-PRE-10`.
- El resto del código trata a todos los préstamos igual.
- Facilita sumar un tercer tipo (por ejemplo, préstamo a domicilio) sin tocar los llamadores.

**Costos.** Mínimos; es una clase o función con una responsabilidad.

---

## 4. Repository (Repositorio)

**Problema.** El dominio no debe conocer SQL ni SQLAlchemy, y los servicios deben poder probarse sin base de datos.

**Solución.** Interfaces de repositorio en el dominio (`PrestamoRepository`, `EjemplarRepository`…) y su implementación con SQLAlchemy en infraestructura. Existe también una implementación en memoria para los tests de servicios.

**Ventajas.**

- El dominio queda libre de la tecnología de persistencia y se prueba rápido.
- Las consultas complejas (vencidos, cola de reservas) quedan nombradas y reutilizables.
- Cambiar el motor de base de datos afecta solo a infraestructura.

**Costos.** Una capa más; es el costo de la arquitectura por capas que ya se decidió.

---

## 5. Unit of Work

**Problema.** Un caso de uso toca varias entidades (por ejemplo, devolver: préstamo, ejemplar, multa, socio, reserva) y debe confirmarse o deshacerse **en conjunto**.

**Solución.** La Unit of Work agrupa los repositorios de una sesión y expone `commit()` y `rollback()`. El servicio abre una por caso de uso.

**Ventajas.** Atomicidad real: si falla la asignación a la reserva, no queda una devolución a medias. Concentra el control de transacciones en la capa de aplicación.

---

## 6. Observer (eventos de dominio), opcional

**Problema.** Varios procesos reaccionan a un mismo hecho: al recibir un remito hay que avisar al socio, al liberar un ejemplar hay que revisar la cola de reservas, al generar una multa hay que reevaluar al socio.

**Solución.** El dominio emite eventos (`RemitoRecibido`, `EjemplarLiberado`, `MultaGenerada`, `PrestamoVencido`) y los observadores se suscriben. Las notificaciones al socio (proceso opcional del enunciado) son otro observador.

**Ventajas.**

- Desacopla: `Remito` no sabe de notificaciones ni de reservas.
- Agregar una reacción nueva (aviso por correo) es suscribir un observador, sin tocar el emisor.

**Costos.** El flujo es menos obvio de leer; se mitiga con eventos sincrónicos dentro de la misma transacción y un único despachador.

**Propuesta.** Incluirlo si se implementa el proceso opcional de notificaciones; las reacciones críticas (reasignar reservas, reevaluar socio) se mantienen explícitas en el servicio para que sean fáciles de seguir.

---

## 7. Specification / Chain of Responsibility, opcional

**Problema.** Registrar un préstamo aplica ocho validaciones (socio habilitado, ejemplar disponible, ejemplar de la sede origen, ambas sedes activas, tope de préstamos, libro repetido…), y no siempre el mismo conjunto.

**Solución.** Cada regla es un objeto con `verificar(contexto)`; una lista ordenada las aplica. Cada regla lanza su propia excepción de negocio.

**Ventajas.** Reglas pequeñas, probables una a una, que se pueden reordenar o reutilizar (por ejemplo, la misma regla «socio habilitado» sirve para reservas). Facilita trazar los criterios `CA-PRE-01` a `CA-PRE-06`.

**Costos.** Para ocho reglas simples, un método con guardas claras puede ser suficiente. Se recomienda solo si la lista crece o se reutiliza entre préstamos y reservas.

---

## 10. Strategy + Composite: verificación de baja de sede

**Problema.** La baja de una sede se bloquea por seis tipos de actividad pendiente que viven en procesos distintos y que se construyen en iteraciones distintas (usuarios hoy; ejemplares, préstamos, remitos y reservas después). Si `SedeService` consultara todo directamente, estaría acoplado a módulos que no existen y cada módulo nuevo obligaría a modificarlo (viola abierto/cerrado).

**Solución.** Un **puerto** definido por el dominio, una implementación por módulo y un compuesto que las agrupa.

```python
@dataclass(frozen=True)
class Impedimento:
    tipo: TipoImpedimento          # PRESTAMOS_EN_CURSO, REMITOS_ABIERTOS, ...
    cantidad: int
    elementos: list[ElementoImpedimento]   # muestra de hasta 10: id y referencia legible
    hay_mas: bool

class VerificadorImpedimentoBaja(Protocol):          # puerto (models/policies)
    tipo: TipoImpedimento
    def verificar(self, sede_id: int) -> Impedimento | None: ...
    # devuelve None si no hay nada que bloquee

class VerificadorBajaSede:                           # Composite (models/policies)
    def __init__(self, verificadores: Sequence[VerificadorImpedimentoBaja]): ...
    def verificar(self, sede_id: int) -> list[Impedimento]:
        return [i for v in self._verificadores if (i := v.verificar(sede_id))]
```

El servicio obtiene la lista y se la entrega al dominio, que es quien decide:

```python
sede.dar_de_baja(motivo, usuario, impedimentos=verificador.verificar(sede.id))
# lanza SedeConActividadPendiente(sede, impedimentos) si la lista no está vacía
```

**Dónde vive cada pieza.**

| Pieza | Capa y archivo |
|-------|----------------|
| `Impedimento`, `TipoImpedimento`, puerto y compuesto | `models/policies/verificacion_baja_sede.py` |
| Implementación de **usuarios** (bibliotecarios activos asignados) | `repositories/impl/usuario_verificador_baja_sede.py` (esta iteración) |
| Implementaciones de ejemplares, préstamos, remitos y reservas | `repositories/impl/<modulo>_verificador_baja_sede.py`, cada una en el PR del módulo que corresponda |
| Armado del compuesto con las implementaciones registradas | `controllers/dependencies.py` (raíz de composición) |

**Cómo se suma un módulo.** El PR del módulo agrega su verificador, lo registra en la lista de la raíz de composición y suma las pruebas de su criterio de aceptación. No toca `SedeService` ni el dominio de sede.

**Garantía de cobertura.** `TipoImpedimento` enumera los seis tipos. Una prueba de contrato (`tests/contract/test_verificadores_baja_sede.py`) falla si hay un tipo sin verificador registrado, salvo los de una lista explícita de pendientes (`TIPOS_PENDIENTES_DE_MODULO`) que **solo puede achicarse**. Así no se puede olvidar una verificación al agregar un módulo ni dar la baja por completa antes de tiempo.

**Contrato para los demás módulos (concurrencia).** Toda operación que tome una sede como origen, destino, retiro o alta debe obtenerla con `SedeRepository.obtener_para_operar(id)`, que la bloquea con `FOR SHARE` y llama a `sede.validar_operativa()` (lanza `SedeEnBaja` si no está activa). La baja bloquea con `FOR UPDATE`. Así las dos se serializan: si la baja llega primero, la operación se rechaza; si la operación llega primero, la baja espera y después la ve.

**Ventajas.**

- `SedeService` no cambia cuando aparece un módulo nuevo.
- Cada verificación se prueba sola, con datos propios.
- La regla de decisión (bloquear si hay impedimentos) queda en un único lugar del dominio.
- Para las pruebas de servicio se inyectan verificadores falsos que simulan cada tipo de actividad, sin esperar a los demás módulos.

**Costos.** Una abstracción más y una prueba de contrato que mantener. Se justifica porque el negocio ya declaró que son seis causas en cuatro módulos que se construyen por separado.

**Alternativas descartadas.** (a) Consultas SQL directas en `SedeService`: acoplamiento fuerte y tablas que aún no existen. (b) Eventos de dominio: la verificación debe ser síncrona y dentro de la misma transacción que la baja, y un evento la volvería asincrónica y opaca. (c) Una vista SQL «actividad por sede»: oculta reglas de negocio en la base y se desactualiza con cada módulo.

---

## 11. Value Object

Los datos que se validan juntos y no tienen identidad propia son objetos de valor inmutables que se validan al construirse: `CodigoSede` (formato y mayúsculas), `Telefono` (E.164), `Email`, `Direccion` (calle, número, localidad y su forma normalizada para comparar), `FranjaHoraria` (día, apertura y cierre, con la regla de cierre posterior) y `ExcepcionHorario`. Así la regla vive en un solo lugar, el dominio nunca maneja cadenas sin validar y se prueba sin base de datos.

---

## Patrones que no se recomiendan

| Patrón | Motivo |
|--------|--------|
| Singleton | Las dependencias se inyectan; un singleton oculta el estado y complica los tests |
| Abstract Factory | No hay familias de objetos que crear |
| Decorator, Adapter | No hay un problema concreto que resuelvan en este dominio |

## Relación con los requisitos de la cátedra

- **Mínimo de dos patrones:** State y Strategy cumplen solos, con Factory, Repository y Unit of Work como refuerzo.
- **Ciclo de vida del remito evaluado críticamente:** State lo modela de forma explícita y verificable.
- **Lógica en el dominio:** los patrones viven en `models/` (State, Strategy, Factory) y en `repositories/` (Unit of Work); la interfaz no decide reglas.
