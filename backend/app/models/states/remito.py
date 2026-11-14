"""Estados del remito (patrón State). Es el ciclo que la cátedra evalúa críticamente.

| Estado      | Operaciones admitidas                                               |
|-------------|---------------------------------------------------------------------|
| Generado    | empaquetar, anular                                                  |
| Empaquetado | despachar, anular                                                   |
| Despachado  | pasar_a_transito, marcar_extraviado                                 |
| EnTransito  | recibir (Recibido, Dañado, Destruido o Incompleto según la peor     |
|             | línea), marcar_extraviado                                           |
| Recibido, Extraviado, Danado, Destruido, Incompleto, Anulado | ninguna (finales)    |

``Incompleto`` es un remito recibido con al menos un ejemplar que no llegó (faltante): los que
llegaron se reciben normalmente y los faltantes se dan de baja por extravío.

Sin saltos ni retrocesos: cualquier operación que no figura se rechaza con ``TransicionInvalida``.
La recepción desde ``Despachado`` la resuelve la entidad pasando antes por ``EnTransito``, para
que el historial muestre los dos movimientos.
"""

from enum import StrEnum
from typing import ClassVar

from app.exceptions import TransicionInvalida


class EstadoRemitoEnum(StrEnum):
    GENERADO = "GENERADO"
    EMPAQUETADO = "EMPAQUETADO"
    DESPACHADO = "DESPACHADO"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDO = "RECIBIDO"
    EXTRAVIADO = "EXTRAVIADO"
    DANADO = "DANADO"
    DESTRUIDO = "DESTRUIDO"
    INCOMPLETO = "INCOMPLETO"
    ANULADO = "ANULADO"


ABIERTOS = frozenset(
    {
        EstadoRemitoEnum.GENERADO,
        EstadoRemitoEnum.EMPAQUETADO,
        EstadoRemitoEnum.DESPACHADO,
        EstadoRemitoEnum.EN_TRANSITO,
    }
)

TEXTO_ESTADO = {
    EstadoRemitoEnum.GENERADO: "generado",
    EstadoRemitoEnum.EMPAQUETADO: "empaquetado",
    EstadoRemitoEnum.DESPACHADO: "despachado",
    EstadoRemitoEnum.EN_TRANSITO: "en tránsito",
    EstadoRemitoEnum.RECIBIDO: "recibido",
    EstadoRemitoEnum.EXTRAVIADO: "extraviado",
    EstadoRemitoEnum.DANADO: "recibido con daño",
    EstadoRemitoEnum.DESTRUIDO: "recibido destruido",
    EstadoRemitoEnum.INCOMPLETO: "recibido con faltantes",
    EstadoRemitoEnum.ANULADO: "anulado",
}


class EstadoRemito:
    """Estado base: rechaza todo lo que el estado concreto no admite."""

    nombre: ClassVar[EstadoRemitoEnum]

    def empaquetar(self) -> "EstadoRemito":
        raise self._invalida("empaquetar")

    def despachar(self) -> "EstadoRemito":
        raise self._invalida("despachar")

    def pasar_a_transito(self) -> "EstadoRemito":
        raise self._invalida("pasar a en tránsito")

    def recibir(self) -> "EstadoRemito":
        raise self._invalida("recibir")

    def recibir_con_dano(self) -> "EstadoRemito":
        raise self._invalida("recibir")

    def recibir_destruido(self) -> "EstadoRemito":
        raise self._invalida("recibir")

    def recibir_con_faltantes(self) -> "EstadoRemito":
        raise self._invalida("recibir")

    def anular(self) -> "EstadoRemito":
        raise self._invalida("anular")

    def marcar_extraviado(self) -> "EstadoRemito":
        raise self._invalida("marcar como extraviado")

    def _invalida(self, accion: str) -> TransicionInvalida:
        return TransicionInvalida(
            f"No se puede {accion} un remito {TEXTO_ESTADO[self.nombre]}.",
            [{"campo": "estado", "problema": self.nombre.value}],
        )

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, EstadoRemito) and otro.nombre == self.nombre

    def __hash__(self) -> int:
        return hash(self.nombre)

    def __repr__(self) -> str:
        return self.nombre.value


class Generado(EstadoRemito):
    nombre = EstadoRemitoEnum.GENERADO

    def empaquetar(self) -> EstadoRemito:
        return Empaquetado()

    def anular(self) -> EstadoRemito:
        return Anulado()


class Empaquetado(EstadoRemito):
    nombre = EstadoRemitoEnum.EMPAQUETADO

    def despachar(self) -> EstadoRemito:
        return Despachado()

    def anular(self) -> EstadoRemito:
        return Anulado()


class Despachado(EstadoRemito):
    nombre = EstadoRemitoEnum.DESPACHADO

    def pasar_a_transito(self) -> EstadoRemito:
        return EnTransito()

    def marcar_extraviado(self) -> EstadoRemito:
        return Extraviado()


class EnTransito(EstadoRemito):
    nombre = EstadoRemitoEnum.EN_TRANSITO

    def recibir(self) -> EstadoRemito:
        return Recibido()

    def recibir_con_dano(self) -> EstadoRemito:
        return Danado()

    def recibir_destruido(self) -> EstadoRemito:
        return Destruido()

    def recibir_con_faltantes(self) -> EstadoRemito:
        return Incompleto()

    def marcar_extraviado(self) -> EstadoRemito:
        return Extraviado()


class Recibido(EstadoRemito):
    nombre = EstadoRemitoEnum.RECIBIDO


class Extraviado(EstadoRemito):
    nombre = EstadoRemitoEnum.EXTRAVIADO


class Danado(EstadoRemito):
    nombre = EstadoRemitoEnum.DANADO


class Destruido(EstadoRemito):
    nombre = EstadoRemitoEnum.DESTRUIDO


class Incompleto(EstadoRemito):
    """Recibido con ejemplares que no llegaron."""

    nombre = EstadoRemitoEnum.INCOMPLETO


class Anulado(EstadoRemito):
    nombre = EstadoRemitoEnum.ANULADO


_POR_NOMBRE: dict[EstadoRemitoEnum, type[EstadoRemito]] = {
    clase.nombre: clase
    for clase in (
        Generado,
        Empaquetado,
        Despachado,
        EnTransito,
        Recibido,
        Extraviado,
        Danado,
        Destruido,
        Incompleto,
        Anulado,
    )
}


def estado_remito(nombre: EstadoRemitoEnum | str) -> EstadoRemito:
    """Instancia del estado a partir del valor guardado en la base."""
    return _POR_NOMBRE[EstadoRemitoEnum(nombre)]()
