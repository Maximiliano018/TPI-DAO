# 05. Patrones de diseño

El enunciado exige **al menos dos patrones**. Este documento analiza los que encajan en el dominio, qué problema resuelve cada uno, su ventaja y su costo, y cuáles se implementan.

## Resumen

| # | Patrón | Dónde | Prioridad | Implementar |
|---|--------|-------|-----------|-------------|
| 1 | State | Ciclo de vida de remito, préstamo, ejemplar y reserva | Alta | Sí |
| 2 | Strategy | Cálculo de multa, plazo de préstamo y criterio de sede origen | Alta | Sí |
| 3 | Factory | Creación de préstamo local o interbibliotecario según el ejemplar asignado | Alta | Sí |
| 4 | Repository | Acceso a datos | Alta | Sí |
| 5 | Unit of Work | Transacción por caso de uso | Media | Sí |
| 6 | Observer (eventos de dominio) | Notificaciones | Media | Opcional |
| 7 | Chain of Responsibility / Specification | Validaciones de préstamo | Baja | Opcional |
| 8 | Dependency Injection | Servicios y repositorios | Alta | Sí (FastAPI lo trae) |
| 9 | Facade | Servicios de aplicación | Media | Sí, de forma natural |

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

class CriterioSedeOrigen(Protocol):
    def elegir(self, disponibles_por_sede: dict[int, int]) -> int: ...

class MasDisponiblesMenorId:
    def elegir(self, disponibles_por_sede: dict[int, int]) -> int:
        # más disponibles primero; con empate, menor id de sede
        return min(disponibles_por_sede, key=lambda sede_id: (-disponibles_por_sede[sede_id], sede_id))
```

`CriterioSedeOrigen` lo usa `AsignadorDeEjemplar` cuando la sede destino no tiene ejemplares disponibles. Si mañana se elige por cercanía o por carga de envíos, se agrega otra estrategia sin tocar el asignador.

**Ventajas.**

- Cambiar o sumar una política (multa escalonada, plazo por categoría de libro) no toca el dominio existente (principio abierto/cerrado).
- Se prueba cada política sin base ni préstamo: `CA-DEV-06` y `CA-DEV-07`.
- Los valores salen de la tabla `parametro`, así el administrador los ajusta sin cambiar código.

**Costos.** Una abstracción más; se justifica porque el negocio ya declaró que estas reglas son configurables.

---

## 3. Factory (Fábrica)

**Problema.** Un préstamo local y uno interbibliotecario se crean con reglas distintas: el local exige origen igual a destino, no genera remito y usa el plazo local; el interbibliotecario exige sedes distintas, genera envío y usa otro plazo. Repetir esa decisión en cada servicio duplica las reglas.

**Solución.** La decisión se reparte en dos pasos. Primero, `AsignadorDeEjemplar` elige el ejemplar según la disponibilidad: uno de la sede destino si hay, o si no uno de la sede que indica `CriterioSedeOrigen`. Después, `PrestamoFactory.crear(socio, ejemplar, sede_destino, parametros)` deduce el tipo comparando la sede del ejemplar con la sede destino, construye el préstamo en estado `Solicitado` con la `PoliticaPlazo` correspondiente y garantiza sus invariantes. El usuario nunca indica el tipo ni el ejemplar (RF-PRE-01, RF-PRE-16).

**Ventajas.**

- Un único punto donde se decide «local o interbibliotecario», que respalda `CA-PRE-10` y `CA-PRE-19` a `CA-PRE-21`.
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

## Patrones que no se recomiendan

| Patrón | Motivo |
|--------|--------|
| Singleton | Las dependencias se inyectan; un singleton oculta el estado y complica los tests |
| Abstract Factory | No hay familias de objetos que crear |
| Decorator, Adapter | No hay un problema concreto que resuelvan en este dominio |

## Relación con los requisitos de la cátedra

- **Mínimo de dos patrones:** State y Strategy cumplen solos, con Factory, Repository y Unit of Work como refuerzo.
- **Ciclo de vida del remito evaluado críticamente:** State lo modela de forma explícita y verificable.
- **Lógica en el dominio:** los patrones viven en `domain/` (State, Strategy, Factory) y en `application/` (Unit of Work); la interfaz no decide reglas.
