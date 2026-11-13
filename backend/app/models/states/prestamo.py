"""Estados del préstamo (patrón State).

| Estado      | Operaciones admitidas                                         |
|-------------|---------------------------------------------------------------|
| Solicitado  | enviar (remito generado), entregar (local), cancelar          |
| EnEnvio     | entregar (recibido en destino), cancelar (remito anulado,     |
|             | extraviado, dañado o el socio no lo retira)                   |
| Activo      | renovar, marcar_vencido, devolver                             |
| Vencido     | devolver (con multa)                                          |
| Devuelto    | ninguna (final)                                               |
| Cancelado   | ninguna (final)                                               |

Las guardas que dependen de otros datos (fecha de vencimiento, reservas, sede) las controla la
entidad ``Prestamo``; el estado solo decide qué operaciones existen en cada momento.
"""

from enum import StrEnum
from typing import ClassVar

from app.exceptions import TransicionInvalida


class EstadoPrestamoEnum(StrEnum):
    SOLICITADO = "SOLICITADO"
    EN_ENVIO = "EN_ENVIO"
    ACTIVO = "ACTIVO"
    VENCIDO = "VENCIDO"
    DEVUELTO = "DEVUELTO"
    CANCELADO = "CANCELADO"


ABIERTOS = frozenset(
    {
        EstadoPrestamoEnum.SOLICITADO,
        EstadoPrestamoEnum.EN_ENVIO,
        EstadoPrestamoEnum.ACTIVO,
        EstadoPrestamoEnum.VENCIDO,
    }
)

TEXTO_ESTADO = {
    EstadoPrestamoEnum.SOLICITADO: "solicitado",
    EstadoPrestamoEnum.EN_ENVIO: "en envío",
    EstadoPrestamoEnum.ACTIVO: "activo",
    EstadoPrestamoEnum.VENCIDO: "vencido",
    EstadoPrestamoEnum.DEVUELTO: "devuelto",
    EstadoPrestamoEnum.CANCELADO: "cancelado",
}


class EstadoPrestamo:
    """Estado base: toda operación se rechaza salvo que el estado concreto la admita."""

    nombre: ClassVar[EstadoPrestamoEnum]

    def enviar(self) -> "EstadoPrestamo":
        raise self._invalida("enviar")

    def entregar(self) -> "EstadoPrestamo":
        raise self._invalida("entregar")

    def renovar(self) -> "EstadoPrestamo":
        raise self._invalida("renovar")

    def marcar_vencido(self) -> "EstadoPrestamo":
        raise self._invalida("marcar como vencido")

    def devolver(self) -> "EstadoPrestamo":
        raise self._invalida("registrar la devolución de")

    def cancelar(self) -> "EstadoPrestamo":
        raise self._invalida("cancelar")

    def _invalida(self, accion: str) -> TransicionInvalida:
        return TransicionInvalida(
            f"No se puede {accion} un préstamo {TEXTO_ESTADO[self.nombre]}.",
            [{"campo": "estado", "problema": self.nombre.value}],
        )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, EstadoPrestamo) and otro.nombre == self.nombre

    def __hash__(self) -> int:
        return hash(self.nombre)

    def __repr__(self) -> str:
        return self.nombre.value


class Solicitado(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.SOLICITADO

    def enviar(self) -> EstadoPrestamo:
        return EnEnvio()

    def entregar(self) -> EstadoPrestamo:
        return Activo()

    def cancelar(self) -> EstadoPrestamo:
        return Cancelado()


class EnEnvio(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.EN_ENVIO

    def entregar(self) -> EstadoPrestamo:
        return Activo()

    def cancelar(self) -> EstadoPrestamo:
        return Cancelado()


class Activo(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.ACTIVO

    def renovar(self) -> EstadoPrestamo:
        return self

    def marcar_vencido(self) -> EstadoPrestamo:
        return Vencido()

    def devolver(self) -> EstadoPrestamo:
        return Devuelto()


class Vencido(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.VENCIDO

    def devolver(self) -> EstadoPrestamo:
        return Devuelto()


class Devuelto(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.DEVUELTO


class Cancelado(EstadoPrestamo):
    nombre = EstadoPrestamoEnum.CANCELADO


_POR_NOMBRE: dict[EstadoPrestamoEnum, type[EstadoPrestamo]] = {
    clase.nombre: clase for clase in (Solicitado, EnEnvio, Activo, Vencido, Devuelto, Cancelado)
}


def estado_prestamo(nombre: EstadoPrestamoEnum | str) -> EstadoPrestamo:
    """Instancia del estado a partir del valor guardado en la base."""
    return _POR_NOMBRE[EstadoPrestamoEnum(nombre)]()
