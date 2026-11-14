"""Cómo se muestra quién hizo algo, según quién lo lee.

El personal ve el nombre del usuario. El socio no ve la identidad del personal: ve «Vos» si lo
hizo él, «Personal de la biblioteca» si lo hizo otro usuario y «Sistema» si fue automático. Lo
usan los historiales del socio y del préstamo.
"""

from app.models.usuario import Usuario, UsuarioRef

AUTOR_SISTEMA = "Sistema"
AUTOR_PERSONAL = "Personal de la biblioteca"
AUTOR_PROPIO = "Vos"


def autor_visible(usuario: UsuarioRef | None, lector: Usuario, *, personal: bool) -> str:
    """Nombre para mostrar del autor de un cambio."""
    if usuario is None:
        return AUTOR_SISTEMA
    if personal:
        return usuario.nombre
    return AUTOR_PROPIO if usuario.id == lector.id else AUTOR_PERSONAL
