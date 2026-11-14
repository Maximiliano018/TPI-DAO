"""Incidencias: extravío, daño o destrucción de un ejemplar (en un envío o en una devolución).

**¿Quién es responsable?** Depende de dónde pasó:

- **Devolución:** el socio, que tenía el ejemplar (``socio_id``). Queda registrada por si más
  adelante se decide aplicar una sanción.
- **Remito:** la **sede origen** del envío (``sede_responsable_id``), que lo empaquetó, lo
  despachó y lo custodia hasta que la sede destino lo recibe. En un retorno, la sede origen es
  la que recibió la devolución y lo manda de vuelta. El socio nunca es responsable de lo que
  pasa en un envío: no tenía el ejemplar. Quién lo despachó (la persona) está en el historial
  del remito.

Un extravío se puede **resolver** si el ejemplar aparece después (ver ``Ejemplar.recuperar``).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models.usuario import UsuarioRef


class TipoIncidencia(StrEnum):
    EXTRAVIO = "EXTRAVIO"
    DANIO = "DANIO"
    DESTRUCCION = "DESTRUCCION"


class OrigenIncidencia(StrEnum):
    REMITO = "REMITO"
    DEVOLUCION = "DEVOLUCION"


@dataclass
class Incidencia:
    """Registro de un problema con un ejemplar. Alimenta el reporte de envíos e incidencias."""

    tipo: TipoIncidencia
    origen: OrigenIncidencia
    ejemplar_id: int
    descripcion: str
    fecha: datetime
    usuario: UsuarioRef | None
    socio_id: int | None = None
    prestamo_id: int | None = None
    remito_id: int | None = None
    sede_responsable_id: int | None = None
    id: int | None = None
    resuelta_en: datetime | None = None
    resuelta_por: UsuarioRef | None = None
    resolucion: str | None = None
    # Para mostrar (lo completa el repositorio).
    sede_responsable_nombre: str | None = None

    @classmethod
    def de_remito(
        cls,
        *,
        tipo: TipoIncidencia,
        remito_id: int | None,
        sede_origen_id: int,
        ejemplar_id: int,
        prestamo_id: int | None,
        descripcion: str,
        actor: UsuarioRef | None,
        ahora: datetime,
    ) -> "Incidencia":
        """Incidencia de un envío: responde la sede origen, nunca el socio."""
        return cls(
            tipo=tipo,
            origen=OrigenIncidencia.REMITO,
            ejemplar_id=ejemplar_id,
            descripcion=descripcion,
            fecha=ahora,
            usuario=actor,
            prestamo_id=prestamo_id,
            remito_id=remito_id,
            sede_responsable_id=sede_origen_id,
        )

    @property
    def resuelta(self) -> bool:
        return self.resuelta_en is not None

    def resolver(self, resolucion: str, actor: UsuarioRef, ahora: datetime) -> None:
        """El ejemplar extraviado apareció: la incidencia queda resuelta (no se borra)."""
        self.resuelta_en = ahora
        self.resuelta_por = actor
        self.resolucion = resolucion
