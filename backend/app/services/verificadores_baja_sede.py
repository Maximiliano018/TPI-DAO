"""Verificadores de impedimentos de baja de sede que aporta cada módulo.

Cada clase implementa el puerto ``VerificadorImpedimentoBaja`` del dominio y se registra en
``get_verificador_baja_sede``. ``SedeService`` no conoce ninguna de ellas.
"""

from app.models.policies.verificacion_baja_sede import (
    MAX_ELEMENTOS_POR_IMPEDIMENTO,
    ElementoImpedimento,
    Impedimento,
    TipoImpedimento,
)
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
