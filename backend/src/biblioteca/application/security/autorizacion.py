"""Reglas de autorización (ARCHITECTURE.md §6.3).

La API exige el rol antes de llamar al servicio; el servicio verifica la sede, que
depende del recurso y solo se conoce después de cargarlo. Ambas funciones se pueden
usar en cualquier capa y se prueban sin HTTP.
"""

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import AccesoDenegado


def exigir_rol(actor: UsuarioActual, *roles: Rol) -> None:
    if actor.rol not in roles:
        permitidos = ", ".join(roles)
        raise AccesoDenegado(f"Esta acción requiere uno de estos roles: {permitidos}")


def exigir_sede(actor: UsuarioActual, *sedes_del_recurso: int) -> None:
    """El ADMIN opera en toda la red; el resto, solo si su sede está entre las del recurso.

    Se pasan varias sedes cuando la acción admite más de una (por ejemplo, un remito
    se puede marcar extraviado desde la sede origen o la destino).
    """
    if actor.es_admin:
        return
    if actor.sede_id not in sedes_del_recurso:
        raise AccesoDenegado("No puede operar sobre recursos de otra sede")
