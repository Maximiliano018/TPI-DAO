"""Estados de disponibilidad del ejemplar (patrón State).

Cada estado es una clase que implementa solo las operaciones que admite; las demás heredan el
comportamiento por defecto, que rechaza con ``TransicionInvalida``. La entidad ``Ejemplar``
delega en su estado actual y registra el movimiento (ver ``docs/tecnica/03-maquinas-de-estado.md``).

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
| Baja          | ninguna                                                                    |
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
    nombre = EstadoEjemplarEnum.BAJA


_POR_NOMBRE: dict[EstadoEjemplarEnum, type[EstadoEjemplar]] = {
    clase.nombre: clase
    for clase in (Disponible, Apartado, Reservado, EnTransito, Prestado, EnRevision, Baja)
}


def estado_ejemplar(nombre: EstadoEjemplarEnum | str) -> EstadoEjemplar:
    """Instancia del estado a partir del valor guardado en la base."""
    return _POR_NOMBRE[EstadoEjemplarEnum(nombre)]()
