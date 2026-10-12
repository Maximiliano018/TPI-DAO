"""Interfaces (puertos) de los repositorios.

El dominio define QUÉ necesita guardar y buscar; infrastructure/repositories
implementa CÓMO hacerlo con SQLAlchemy. Ejemplo a futuro:

    class SedeRepository(Protocol):
        def obtener(self, id: int) -> Sede | None: ...
        def guardar(self, sede: Sede) -> None: ...
"""
