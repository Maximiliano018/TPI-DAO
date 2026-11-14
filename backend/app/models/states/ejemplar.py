"""Estados de disponibilidad del ejemplar (patrón State).

Roles del patrón:

- **Contexto:** ``Ejemplar`` (``models/ejemplar.py``). Guarda su estado actual, le delega cada
  operación, lo reemplaza por el estado que este devuelve y registra el movimiento.
- **Estado abstracto:** ``EstadoEjemplar``. Declara todas las operaciones; por defecto las
  rechaza con ``TransicionInvalida``.
- **Estados concretos:** ``Disponible``, ``Apartado``, ``Reservado``, ``EnTransito``,
  ``Prestado``, ``EnRevision`` y ``Baja``. Cada uno sobrescribe solo las operaciones que admite
  y devuelve el estado siguiente.
- **Clientes:** los servicios (catálogo, préstamos, remitos, reservas y devoluciones), que piden
  la operación al ejemplar sin preguntar en qué estado está.

Así una transición nueva o un estado nuevo se agregan en una clase, sin tocar condicionales en
los servicios. Ver ``docs/tecnica/03-maquinas-de-estado.md`` y ``05-patrones-de-diseno.md``.

Además de las transiciones, ``validar_edicion`` decide si se pueden editar los datos del
ejemplar (estado físico y observaciones): todos los estados lo admiten salvo ``Baja``.

| Estado        | Operaciones admitidas                                                      |
|---------------|----------------------------------------------------------------------------|
| Disponible    | apartar, reservar, dar_de_baja                                             |
| Apartado      | prestar, poner_en_transito, liberar                                        |
| Reservado     | prestar, poner_en_transito, liberar                                        |
| EnTransito    | apartar (préstamo recibido en destino, espera el retiro del socio),        |
|               | liberar (retorno o traslado recibido), enviar_a_revision (recibido         |
|               | dañado), dar_de_baja (extraviado o destruido)                              |
| Prestado      | liberar (devuelto en su sede), apartar (devuelto en otra sede),            |
|               | enviar_a_revision (devuelto dañado), dar_de_baja (extraviado)              |
| EnRevision    | reparar, dar_de_baja (irreparable)                                         |
| Baja          | recuperar (solo un extraviado que apareció: vuelve a Disponible, o a       |
|               | En revisión si llegó dañado). Lo controla el servicio con la incidencia.   |
"""

from enum import StrEnum
from typing import ClassVar

from app.exceptions import TransicionInvalida


class EstadoEjemplarEnum(StrEnum):
    DISPONIBLE = "DISPONIBLE"
    APARTADO = "APARTADO"
    RESERVADO = "RESERVADO"
    PRESTADO = "PRESTADO"
    EN_TRANSITO = "EN_TRANSITO"
    EN_REVISION = "EN_REVISION"
    BAJA = "BAJA"


TEXTO_ESTADO = {
    EstadoEjemplarEnum.DISPONIBLE: "disponible",
    EstadoEjemplarEnum.APARTADO: "apartado",
    EstadoEjemplarEnum.RESERVADO: "reservado",
    EstadoEjemplarEnum.PRESTADO: "prestado",
    EstadoEjemplarEnum.EN_TRANSITO: "en tránsito",
    EstadoEjemplarEnum.EN_REVISION: "en revisión",
    EstadoEjemplarEnum.BAJA: "dado de baja",
}


class EstadoEjemplar:
    """Estado base: toda operación se rechaza salvo que el estado concreto la admita."""

    nombre: ClassVar[EstadoEjemplarEnum]

    def apartar(self) -> "EstadoEjemplar":
        raise self._invalida("apartar")

    def reservar(self) -> "EstadoEjemplar":
        raise self._invalida("reservar")

    def prestar(self) -> "EstadoEjemplar":
        raise self._invalida("prestar")

    def poner_en_transito(self) -> "EstadoEjemplar":
        raise self._invalida("enviar")

    def liberar(self) -> "EstadoEjemplar":
        raise self._invalida("liberar")

    def enviar_a_revision(self) -> "EstadoEjemplar":
        raise self._invalida("enviar a revisión")

    def reparar(self) -> "EstadoEjemplar":
        raise self._invalida("marcar como reparado")

    def dar_de_baja(self) -> "EstadoEjemplar":
        raise self._invalida("dar de baja")

    def recuperar(self, *, danado: bool) -> "EstadoEjemplar":
        raise self._invalida("recuperar")

    def validar_edicion(self) -> None:
        """Editar el estado físico o las observaciones no cambia la disponibilidad."""

    def _invalida(self, accion: str) -> TransicionInvalida:
        return TransicionInvalida(
            f"No se puede {accion} un ejemplar {TEXTO_ESTADO[self.nombre]}.",
            [{"campo": "estado", "problema": self.nombre.value}],
        )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, EstadoEjemplar) and otro.nombre == self.nombre

    def __hash__(self) -> int:
        return hash(self.nombre)

    def __repr__(self) -> str:
        return self.nombre.value


class Disponible(EstadoEjemplar):
    nombre = EstadoEjemplarEnum.DISPONIBLE

    def apartar(self) -> EstadoEjemplar:
        return Apartado()

    def reservar(self) -> EstadoEjemplar:
        return Reservado()

    def dar_de_baja(self) -> EstadoEjemplar:
        return Baja()


class Apartado(EstadoEjemplar):
    """Retenido para un movimiento pendiente: préstamo solicitado o retorno a su sede."""

    nombre = EstadoEjemplarEnum.APARTADO

    def prestar(self) -> EstadoEjemplar:
        return Prestado()

    def poner_en_transito(self) -> EstadoEjemplar:
        return EnTransito()

    def liberar(self) -> EstadoEjemplar:
        return Disponible()


class Reservado(EstadoEjemplar):
    """Asignado a la reserva de un socio, a la espera del retiro."""

    nombre = EstadoEjemplarEnum.RESERVADO

    def prestar(self) -> EstadoEjemplar:
        return Prestado()

    def poner_en_transito(self) -> EstadoEjemplar:
        return EnTransito()

    def liberar(self) -> EstadoEjemplar:
        return Disponible()


class EnTransito(EstadoEjemplar):
    nombre = EstadoEjemplarEnum.EN_TRANSITO

    def apartar(self) -> EstadoEjemplar:
        # Llegó a la sede destino de un préstamo: queda retenido hasta que el socio lo retira
        # (el plazo del préstamo empieza recién con esa entrega).
        return Apartado()

    def liberar(self) -> EstadoEjemplar:
        return Disponible()

    def enviar_a_revision(self) -> EstadoEjemplar:
        return EnRevision()

    def dar_de_baja(self) -> EstadoEjemplar:
        return Baja()


class Prestado(EstadoEjemplar):
    nombre = EstadoEjemplarEnum.PRESTADO

    def liberar(self) -> EstadoEjemplar:
        return Disponible()

    def apartar(self) -> EstadoEjemplar:
        return Apartado()

    def enviar_a_revision(self) -> EstadoEjemplar:
        return EnRevision()

    def dar_de_baja(self) -> EstadoEjemplar:
        return Baja()


class EnRevision(EstadoEjemplar):
    """Devuelto o recibido dañado, a la espera de decidir reparación o baja."""

    nombre = EstadoEjemplarEnum.EN_REVISION

    def reparar(self) -> EstadoEjemplar:
        return Disponible()

    def dar_de_baja(self) -> EstadoEjemplar:
        return Baja()


class Baja(EstadoEjemplar):
    """No admite edición y su única salida es recuperar un ejemplar extraviado que apareció.

    Que la baja fue por extravío (y que la incidencia sigue abierta) lo controla el servicio:
    una baja por destrucción o daño irreparable es definitiva.
    """

    nombre = EstadoEjemplarEnum.BAJA

    def recuperar(self, *, danado: bool) -> EstadoEjemplar:
        return EnRevision() if danado else Disponible()

    def validar_edicion(self) -> None:
        raise self._invalida("editar")


_POR_NOMBRE: dict[EstadoEjemplarEnum, type[EstadoEjemplar]] = {
    clase.nombre: clase
    for clase in (Disponible, Apartado, Reservado, EnTransito, Prestado, EnRevision, Baja)
}


def estado_ejemplar(nombre: EstadoEjemplarEnum | str) -> EstadoEjemplar:
    """Instancia del estado a partir del valor guardado en la base."""
    return _POR_NOMBRE[EstadoEjemplarEnum(nombre)]()
