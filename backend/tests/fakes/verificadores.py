"""Verificadores de baja falsos: simulan actividad pendiente sin esperar a los demás módulos."""

from app.models.policies.verificacion_baja_sede import (
    ElementoImpedimento,
    Impedimento,
    TipoImpedimento,
    VerificadorBajaSede,
)


class VerificadorFalso:
    """Informa un impedimento fijo para un tipo (o ninguno si ``cantidad`` es 0)."""

    def __init__(self, tipo: TipoImpedimento, cantidad: int = 0, estado: str = "ACTIVO") -> None:
        self.tipo = tipo
        self._cantidad = cantidad
        self._estado = estado

    def verificar(self, sede_id: int) -> Impedimento | None:
        if self._cantidad == 0:
            return None
        elementos = [
            ElementoImpedimento(i, f"{self.tipo.value[:3]}-{i}", self._estado)
            for i in range(1, min(self._cantidad, 10) + 1)
        ]
        return Impedimento(self.tipo, self._cantidad, elementos)


def verificador_con(**cantidades: int) -> VerificadorBajaSede:
    """Compuesto con un verificador falso por tipo; ``cantidades`` por nombre de tipo."""
    return VerificadorBajaSede(
        [VerificadorFalso(tipo, cantidades.get(tipo.value, 0)) for tipo in TipoImpedimento]
    )
