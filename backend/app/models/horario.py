"""Horario semanal y excepciones de horario de una sede."""

from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum

from app.exceptions import ExcepcionHorarioInvalida, HorarioInvalido
from app.models.valores import FranjaHoraria

MAX_FRANJAS_POR_DIA = 4
MAX_DIAS_POR_RANGO = 31
MAX_LARGO_MOTIVO = 150


def validar_horarios(franjas: list[FranjaHoraria]) -> list[FranjaHoraria]:
    """Valida el horario semanal completo y lo devuelve ordenado.

    Reglas: al menos una franja, hasta 4 por día y sin solapamientos en un mismo día.

    Raises:
        HorarioInvalido: Si alguna regla se incumple (indica el día en conflicto).
    """
    if not franjas:
        raise HorarioInvalido(
            "La sede debe tener al menos una franja horaria.",
            [{"campo": "horarios", "problema": "sin_franjas"}],
        )
    ordenadas = sorted(franjas, key=lambda f: (f.dia, f.apertura))
    for i, franja in enumerate(ordenadas):
        if sum(1 for f in ordenadas if f.dia == franja.dia) > MAX_FRANJAS_POR_DIA:
            raise HorarioInvalido(
                f"Un día admite hasta {MAX_FRANJAS_POR_DIA} franjas.",
                [{"campo": "horarios", "problema": "demasiadas_franjas", "dia": franja.dia}],
            )
        for otra in ordenadas[i + 1 :]:
            if franja.se_solapa_con(otra):
                raise HorarioInvalido(
                    "Hay franjas solapadas el mismo día.",
                    [{"campo": "horarios", "problema": "solapadas", "dia": franja.dia}],
                )
    return ordenadas


class TipoExcepcion(StrEnum):
    CIERRE_TOTAL = "CIERRE_TOTAL"
    CIERRE_PARCIAL = "CIERRE_PARCIAL"


@dataclass(frozen=True)
class ExcepcionHorario:
    """Cierre de la sede en una fecha: total o parcial (entre dos horas)."""

    fecha: date
    tipo: TipoExcepcion
    desde: time | None = None
    hasta: time | None = None
    motivo: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.motivo is not None and len(self.motivo) > MAX_LARGO_MOTIVO:
            raise ExcepcionHorarioInvalida(
                f"El motivo admite hasta {MAX_LARGO_MOTIVO} caracteres.",
                [{"campo": "motivo", "problema": "demasiado_largo"}],
            )
        if self.tipo == TipoExcepcion.CIERRE_TOTAL:
            if self.desde is not None or self.hasta is not None:
                raise ExcepcionHorarioInvalida(
                    "El cierre total no lleva horas.",
                    [{"campo": "hora_desde", "problema": "no_corresponde"}],
                )
            return
        if self.desde is None or self.hasta is None or self.hasta <= self.desde:
            raise ExcepcionHorarioInvalida(
                "El cierre parcial necesita una hora de inicio anterior a la de fin.",
                [{"campo": "hora_desde", "problema": "horas_invalidas"}],
            )
        if self.desde.second or self.hasta.second:
            raise ExcepcionHorarioInvalida(
                "Las horas se indican en horas y minutos.",
                [{"campo": "hora_desde", "problema": "segundos"}],
            )

    def se_solapa_con(self, otra: "ExcepcionHorario") -> bool:
        """Misma fecha y rangos que se cruzan; el cierre total ocupa todo el día."""
        if self.fecha != otra.fecha:
            return False
        if self.tipo == TipoExcepcion.CIERRE_TOTAL or otra.tipo == TipoExcepcion.CIERRE_TOTAL:
            return True
        assert self.desde and self.hasta and otra.desde and otra.hasta
        return self.desde < otra.hasta and otra.desde < self.hasta

    def cierra_en(self, hora: time) -> bool:
        """Indica si la sede está cerrada a esa hora por esta excepción."""
        if self.tipo == TipoExcepcion.CIERRE_TOTAL:
            return True
        assert self.desde and self.hasta
        return self.desde <= hora < self.hasta

    def como_dict(self) -> dict[str, object]:
        """Forma serializable para el historial."""
        return {
            "fecha": self.fecha.isoformat(),
            "tipo": self.tipo.value,
            "hora_desde": self.desde.strftime("%H:%M") if self.desde else None,
            "hora_hasta": self.hasta.strftime("%H:%M") if self.hasta else None,
            "motivo": self.motivo,
        }
