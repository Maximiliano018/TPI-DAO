"""Puerto de acceso a socios."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.models.socio import Documento, EstadoSocio, EventoSocio, SituacionSocio, Socio


@dataclass(frozen=True)
class FiltroSocios:
    """Filtros de la búsqueda de socios (el texto llega normalizado).

    ``texto`` busca en el número de socio, el número de documento y el nombre y apellido.
    """

    texto: str | None = None
    documento: str | None = None
    estado: EstadoSocio | None = None
    solicitud_pendiente: bool = False


class SocioRepository(Protocol):
    """Acceso a socios. Las operaciones que modifican bloquean la fila."""

    def siguiente_numero(self) -> str:
        """Próximo número de socio (secuencia de la base, con 5 dígitos)."""
        ...

    def agregar(self, socio: Socio) -> None:
        """Persiste un socio nuevo (asigna ``id``).

        Raises:
            DuplicadoError: Documento repetido (restricción única de la base).
        """
        ...

    def guardar(self, socio: Socio) -> None:
        """Persiste los datos, el estado y la auditoría de un socio cargado."""
        ...

    def obtener(self, socio_id: int) -> Socio | None:
        """Socio por id, con su sede de alta, auditoría y cuenta de acceso."""
        ...

    def obtener_para_modificar(self, socio_id: int) -> Socio | None:
        """Como ``obtener`` pero con la fila bloqueada (``FOR UPDATE``)."""
        ...

    def buscar_por_documento(
        self, documento: Documento, excluir_id: int | None = None
    ) -> Socio | None:
        """Socio (de cualquier estado) con ese tipo y número de documento."""
        ...

    def buscar_por_persona(
        self, nombre: str, apellido: str, fecha_nacimiento: date, excluir_id: int | None = None
    ) -> list[Socio]:
        """Socios con igual nombre, apellido (sin tildes ni mayúsculas) y fecha de nacimiento."""
        ...

    def listar(self, filtro: FiltroSocios, page: int, size: int) -> tuple[list[Socio], int]:
        """Página de socios ordenada por apellido y nombre, y total."""
        ...

    def situacion(self, socio_id: int) -> SituacionSocio:
        """Préstamos en curso y vencidos, multas pendientes y reservas activas del socio."""
        ...

    def historial(self, socio_id: int, page: int, size: int) -> tuple[list[EventoSocio], int]:
        """Eventos del socio, del más reciente al más antiguo."""
        ...
