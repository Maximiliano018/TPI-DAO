"""Verificadores de impedimentos de baja de sede que aporta cada módulo.

Cada clase implementa el puerto ``VerificadorImpedimentoBaja`` del dominio y se registra en
``get_verificador_baja_sede``. ``SedeService`` no conoce ninguna de ellas.
"""

from app.models.ejemplar import Ejemplar
from app.models.policies.verificacion_baja_sede import (
    MAX_ELEMENTOS_POR_IMPEDIMENTO,
    ElementoImpedimento,
    Impedimento,
    TipoImpedimento,
)
from app.repositories.interfaces.catalogo_repository import EjemplarRepository
from app.repositories.interfaces.usuario_repository import UsuarioRepository


class VerificadorBibliotecariosAsignados:
    """Bloquea la baja de una sede que todavía tiene bibliotecarios activos asignados.

    Un bibliotecario dado de baja deja de contar (CA-ACC-10). Para destrabar la baja hay que
    reasignarlo a otra sede activa o darlo de baja.
    """

    tipo = TipoImpedimento.BIBLIOTECARIOS_ASIGNADOS

    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def verificar(self, sede_id: int) -> Impedimento | None:
        asignados, total = self._usuarios.bibliotecarios_activos_de_sede(
            sede_id, MAX_ELEMENTOS_POR_IMPEDIMENTO
        )
        if total == 0:
            return None
        elementos = [
            ElementoImpedimento(id=u.id, referencia=u.username, estado="ACTIVO")
            for u in asignados
            if u.id is not None
        ]
        return Impedimento(self.tipo, total, elementos)


class VerificadorEjemplaresEnSede:
    """Bloquea la baja de una sede donde todavía hay ejemplares (propios o de otra sede).

    Hay que trasladarlos a otra sede (remito de traslado) o darlos de baja (CA-SED-17).
    """

    tipo = TipoImpedimento.EJEMPLARES_EN_SEDE

    def __init__(self, ejemplares: EjemplarRepository) -> None:
        self._ejemplares = ejemplares

    def verificar(self, sede_id: int) -> Impedimento | None:
        alojados, total = self._ejemplares.alojados_en_sede(sede_id, MAX_ELEMENTOS_POR_IMPEDIMENTO)
        return _impedimento_de_ejemplares(self.tipo, alojados, total)


class VerificadorEjemplaresPropiosFuera:
    """Bloquea la baja si un ejemplar de la sede está prestado en otra o en tránsito (CA-SED-18).

    El ejemplar tiene que volver (o trasladarse) antes de cerrar la sede propietaria.
    """

    tipo = TipoImpedimento.EJEMPLARES_PROPIOS_FUERA

    def __init__(self, ejemplares: EjemplarRepository) -> None:
        self._ejemplares = ejemplares

    def verificar(self, sede_id: int) -> Impedimento | None:
        fuera, total = self._ejemplares.propios_fuera_de_sede(
            sede_id, MAX_ELEMENTOS_POR_IMPEDIMENTO
        )
        return _impedimento_de_ejemplares(self.tipo, fuera, total)


def _impedimento_de_ejemplares(
    tipo: TipoImpedimento, ejemplares: list[Ejemplar], total: int
) -> Impedimento | None:
    if total == 0:
        return None
    elementos = [
        ElementoImpedimento(id=e.id, referencia=e.codigo_inventario, estado=e.estado_nombre.value)
        for e in ejemplares
        if e.id is not None
    ]
    return Impedimento(tipo, total, elementos)
