from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from biblioteca.domain.entities.usuario import Usuario
from biblioteca.infrastructure.db import tables as t


class SqlAlchemyUsuarioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def agregar(self, usuario: Usuario) -> None:
        self.session.add(usuario)

    def obtener(self, usuario_id: int) -> Usuario | None:
        return self.session.get(Usuario, usuario_id)

    def obtener_por_username(self, username: str) -> Usuario | None:
        return self.session.scalars(
            select(Usuario).where(t.usuario.c.username == username)
        ).one_or_none()

    def existe_username(self, username: str) -> bool:
        return bool(self.session.scalar(select(exists().where(t.usuario.c.username == username))))
