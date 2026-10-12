from sqlalchemy.orm import Session

from biblioteca.infrastructure.db.mappers import configurar_mapeos
from biblioteca.infrastructure.repositories.libros import SqlLibroRepository
from biblioteca.infrastructure.repositories.sedes import SqlSedeRepository
from biblioteca.infrastructure.repositories.usuarios import SqlUsuarioRepository


class SqlUnidadDeTrabajo:
    """Todos los repositorios comparten la sesión: los cambios se confirman juntos.

    La sesión es la del request (o la que abra la CLI) y la cierra quien la creó: si el
    caso de uso falla antes de `confirmar()`, no se guarda nada.
    """

    def __init__(self, session: Session) -> None:
        configurar_mapeos()
        self._session = session
        self.libros = SqlLibroRepository(session)
        self.sedes = SqlSedeRepository(session)
        self.usuarios = SqlUsuarioRepository(session)

    def confirmar(self) -> None:
        self._session.commit()
