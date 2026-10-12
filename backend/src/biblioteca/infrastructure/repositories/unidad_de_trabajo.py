from sqlalchemy.orm import Session

from biblioteca.infrastructure.repositories.libros import SqlLibroRepository


class SqlUnidadDeTrabajo:
    """Todos los repositorios comparten la sesión: los cambios se confirman juntos."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.libros = SqlLibroRepository(session)

    def confirmar(self) -> None:
        self._session.commit()
