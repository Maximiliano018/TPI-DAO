"""Estados de la reserva (patrón State).

| Estado               | Operaciones admitidas                           |
|----------------------|-------------------------------------------------|
| Pendiente            | asignar, convertir_en_prestamo, cancelar        |
| DisponibleParaRetiro | cumplir (retiro), vencer, cancelar              |
| Cumplida, Cancelada, Vencida | ninguna (finales)                       |

``convertir_en_prestamo`` es la asignación de un ejemplar de **otra** sede: la reserva se cumple
con un préstamo interbibliotecario hacia la sede de retiro (RF-RES-08).
"""

from enum import StrEnum
from typing import ClassVar

from app.exceptions import TransicionInvalida


class EstadoReservaEnum(StrEnum):
    PENDIENTE = "PENDIENTE"
    DISPONIBLE_PARA_RETIRO = "DISPONIBLE_PARA_RETIRO"
    CUMPLIDA = "CUMPLIDA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"


ACTIVAS = frozenset({EstadoReservaEnum.PENDIENTE, EstadoReservaEnum.DISPONIBLE_PARA_RETIRO})

TEXTO_ESTADO = {
    EstadoReservaEnum.PENDIENTE: "pendiente",
    EstadoReservaEnum.DISPONIBLE_PARA_RETIRO: "disponible para retiro",
    EstadoReservaEnum.CUMPLIDA: "cumplida",
    EstadoReservaEnum.CANCELADA: "cancelada",
    EstadoReservaEnum.VENCIDA: "vencida",
}


class EstadoReserva:
    nombre: ClassVar[EstadoReservaEnum]

    def asignar(self) -> "EstadoReserva":
        raise self._invalida("asignar un ejemplar a")

    def convertir_en_prestamo(self) -> "EstadoReserva":
        raise self._invalida("convertir en préstamo")

    def cumplir(self) -> "EstadoReserva":
        raise self._invalida("entregar")

    def vencer(self) -> "EstadoReserva":
        raise self._invalida("vencer")

    def cancelar(self) -> "EstadoReserva":
        raise self._invalida("cancelar")

    def _invalida(self, accion: str) -> TransicionInvalida:
        return TransicionInvalida(
            f"No se puede {accion} una reserva {TEXTO_ESTADO[self.nombre]}.",
            [{"campo": "estado", "problema": self.nombre.value}],
        )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, EstadoReserva) and otro.nombre == self.nombre

    def __hash__(self) -> int:
        return hash(self.nombre)

    def __repr__(self) -> str:
        return self.nombre.value


class Pendiente(EstadoReserva):
    nombre = EstadoReservaEnum.PENDIENTE

    def asignar(self) -> EstadoReserva:
        return DisponibleParaRetiro()

    def convertir_en_prestamo(self) -> EstadoReserva:
        return Cumplida()

    def cancelar(self) -> EstadoReserva:
        return Cancelada()


class DisponibleParaRetiro(EstadoReserva):
    nombre = EstadoReservaEnum.DISPONIBLE_PARA_RETIRO

    def cumplir(self) -> EstadoReserva:
        return Cumplida()

    def vencer(self) -> EstadoReserva:
        return Vencida()

    def cancelar(self) -> EstadoReserva:
        return Cancelada()


class Cumplida(EstadoReserva):
    nombre = EstadoReservaEnum.CUMPLIDA


class Cancelada(EstadoReserva):
    nombre = EstadoReservaEnum.CANCELADA


class Vencida(EstadoReserva):
    nombre = EstadoReservaEnum.VENCIDA


_POR_NOMBRE: dict[EstadoReservaEnum, type[EstadoReserva]] = {
    clase.nombre: clase for clase in (Pendiente, DisponibleParaRetiro, Cumplida, Cancelada, Vencida)
}


def estado_reserva(nombre: EstadoReservaEnum | str) -> EstadoReserva:
    return _POR_NOMBRE[EstadoReservaEnum(nombre)]()
