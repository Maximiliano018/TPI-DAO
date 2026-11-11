"""Repositorios y Unit of Work en memoria para las pruebas de dominio y de servicios."""

from app.models.usuario import Usuario


class UsuarioRepositorioEnMemoria:
    """Implementa ``UsuarioRepository`` sin base de datos."""

    def __init__(self, usuarios: list[Usuario] | None = None) -> None:
        self._usuarios: dict[int, Usuario] = {}
        for usuario in usuarios or []:
            self.agregar(usuario)

    def agregar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            usuario.id = max(self._usuarios, default=0) + 1
        self._usuarios[usuario.id] = usuario
        return usuario

    def obtener(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def obtener_por_username(self, username: str) -> Usuario | None:
        return next((u for u in self._usuarios.values() if u.username == username), None)


class UnitOfWorkEnMemoria:
    """Unit of Work con repositorios en memoria; registra si se confirmó."""

    def __init__(self, usuarios: UsuarioRepositorioEnMemoria | None = None) -> None:
        self.usuarios = usuarios or UsuarioRepositorioEnMemoria()
        self.confirmaciones = 0
        self.reversiones = 0

    def commit(self) -> None:
        self.confirmaciones += 1

    def rollback(self) -> None:
        self.reversiones += 1
