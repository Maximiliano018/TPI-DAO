"""Puertos de acceso a sedes y al catálogo geográfico."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from app.models.sede import EventoSede, Sede, TipoEventoSede
from app.models.valores import Localidad


class FiltroEstado(StrEnum):
    ACTIVA = "ACTIVA"
    BAJA = "BAJA"
    TODAS = "TODAS"


class OrdenSedes(StrEnum):
    NOMBRE = "nombre"
    NOMBRE_DESC = "-nombre"
    CODIGO = "codigo"
    CODIGO_DESC = "-codigo"
    CREADO_EN = "creado_en"
    CREADO_EN_DESC = "-creado_en"


@dataclass(frozen=True)
class FiltroSedes:
    estado: FiltroEstado = FiltroEstado.TODAS
    texto: str | None = None
    localidad_id: int | None = None
    orden: OrdenSedes = OrdenSedes.NOMBRE


@dataclass(frozen=True)
class FiltroHistorial:
    tipo_evento: TipoEventoSede | None = None
    desde: datetime | None = None
    hasta: datetime | None = None


class SedeRepository(Protocol):
    """Acceso a sedes. Las operaciones que modifican bloquean la fila."""

    def agregar(self, sede: Sede) -> None:
        """Persiste una sede nueva (asigna ``id``) y sus eventos pendientes.

        Raises:
            SedeCodigoDuplicado: Código repetido (restricción única de la base).
            SedeNombreDuplicado: Nombre repetido (restricción única de la base).
        """
        ...

    def obtener(self, sede_id: int) -> Sede | None:
        """Sede por id, sin bloquear."""
        ...

    def obtener_para_modificar(self, sede_id: int) -> Sede | None:
        """Sede por id con la fila bloqueada para escritura (``FOR UPDATE``)."""
        ...

    def obtener_para_operar(self, sede_id: int) -> Sede:
        """Sede con la fila bloqueada en modo compartido (``FOR SHARE``) y ``validar_operativa``.

        Es el contrato que usan los demás módulos antes de tomar una sede como origen, destino,
        retiro o alta: serializa la operación con la baja de la sede.

        Raises:
            SedeNoEncontrada: Si no existe.
            SedeEnBaja: Si está dada de baja.
        """
        ...

    def guardar(self, sede: Sede) -> None:
        """Persiste los cambios de una sede cargada y sus eventos pendientes."""
        ...

    def buscar_por_codigo(self, codigo: str) -> Sede | None: ...

    def buscar_por_nombre_normalizado(
        self, nombre_normalizado: str, excluir_id: int | None = None
    ) -> Sede | None: ...

    def buscar_por_direccion(
        self, direccion_normalizada: str, excluir_id: int | None = None
    ) -> list[Sede]:
        """Sedes (activas o en baja) en la misma dirección normalizada."""
        ...

    def listar(self, filtro: FiltroSedes, page: int, size: int) -> tuple[list[Sede], int]:
        """Página de sedes y total."""
        ...

    def contar_por_estado(self) -> dict[str, int]:
        """Cantidad de sedes por estado (``ACTIVA`` y ``BAJA``)."""
        ...

    def historial(
        self, sede_id: int, filtro: FiltroHistorial, page: int, size: int
    ) -> tuple[list[EventoSede], int]:
        """Eventos de la sede, del más reciente al más antiguo."""
        ...


class LocalidadRepository(Protocol):
    """Catálogo cerrado de provincias y localidades."""

    def obtener(self, localidad_id: int) -> Localidad | None: ...

    def listar(
        self, provincia_id: int | None = None, texto: str | None = None
    ) -> list[Localidad]: ...

    def provincias(self) -> list[tuple[int, str]]:
        """Pares ``(id, nombre)`` de las provincias."""
        ...
