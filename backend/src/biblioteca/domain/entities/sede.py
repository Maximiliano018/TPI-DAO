import re
from collections.abc import Iterable
from datetime import datetime, time
from itertools import pairwise

from biblioteca.domain.errors import (
    DatoInvalido,
    SedeConActividadAbierta,
    SedeDadaDeBaja,
    TransicionInvalida,
)
from biblioteca.domain.valores import texto_opcional, texto_requerido

DIAS_SEMANA = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo",
}


class HorarioSede:
    """Franja de atención de un día. Un día puede tener varias (horario cortado)."""

    id: int | None

    def __init__(self, dia_semana: int, hora_apertura: time, hora_cierre: time) -> None:
        if dia_semana not in DIAS_SEMANA:
            raise DatoInvalido("El día de la semana va de 1 (lunes) a 7 (domingo)")
        if hora_apertura >= hora_cierre:
            raise DatoInvalido(
                f"La apertura ({hora_apertura:%H:%M}) debe ser anterior al cierre "
                f"({hora_cierre:%H:%M}) del {DIAS_SEMANA[dia_semana]}"
            )
        self.id = None
        self.dia_semana = dia_semana
        self.hora_apertura = hora_apertura
        self.hora_cierre = hora_cierre


class Sede:
    """Sede de la red de bibliotecas.

    Invariantes: el código (2 a 5 letras mayúsculas) no cambia una vez creada, porque
    forma parte de los códigos de inventario; una sede dada de baja tiene fecha de baja.
    """

    id: int | None

    def __init__(
        self,
        codigo: str,
        nombre: str,
        direccion: str,
        localidad: str,
        telefono: str | None = None,
        email: str | None = None,
    ) -> None:
        codigo = codigo.strip().upper()
        if not re.fullmatch(r"[A-Z]{2,5}", codigo):
            raise DatoInvalido("El código de sede debe tener entre 2 y 5 letras (por ejemplo, CEN)")
        self.id = None
        self.codigo = codigo
        self.activa = True
        self.fecha_baja: datetime | None = None
        self.horarios: list[HorarioSede] = []
        self.actualizar_datos(nombre, direccion, localidad, telefono, email)

    def actualizar_datos(
        self,
        nombre: str,
        direccion: str,
        localidad: str,
        telefono: str | None,
        email: str | None,
    ) -> None:
        self.nombre = texto_requerido(nombre, "nombre", 100)
        self.direccion = texto_requerido(direccion, "dirección", 200)
        self.localidad = texto_requerido(localidad, "localidad", 100)
        self.telefono = texto_opcional(telefono, "teléfono", 30)
        self.email = texto_opcional(email, "email", 120)
        if self.email is not None and "@" not in self.email:
            raise DatoInvalido("El email no es válido")

    def definir_horarios(self, franjas: Iterable[HorarioSede]) -> None:
        """Reemplaza todos los horarios. Rechaza franjas superpuestas en un mismo día."""
        nuevas = sorted(franjas, key=lambda f: (f.dia_semana, f.hora_apertura))
        for anterior, siguiente in pairwise(nuevas):
            if anterior.dia_semana == siguiente.dia_semana and (
                siguiente.hora_apertura < anterior.hora_cierre
            ):
                raise DatoInvalido(
                    f"Las franjas del {DIAS_SEMANA[anterior.dia_semana]} se superponen"
                )
        # Se modifica la lista en el lugar: el ORM detecta las franjas quitadas y agregadas.
        self.horarios.clear()
        self.horarios.extend(nuevas)

    def verificar_activa(self) -> None:
        """Las operaciones nuevas (préstamos, reservas, envíos) exigen una sede activa."""
        if not self.activa:
            raise SedeDadaDeBaja(f"La sede {self.codigo} está dada de baja")

    def dar_de_baja(self, ahora: datetime, tiene_actividad_abierta: bool) -> None:
        if not self.activa:
            raise TransicionInvalida(f"La sede {self.codigo} ya está dada de baja")
        if tiene_actividad_abierta:
            raise SedeConActividadAbierta(
                f"La sede {self.codigo} tiene préstamos, envíos o reservas en curso; "
                "deben cerrarse antes de darla de baja"
            )
        self.activa = False
        self.fecha_baja = ahora

    def reactivar(self) -> None:
        if self.activa:
            raise TransicionInvalida(f"La sede {self.codigo} ya está activa")
        self.activa = True
        self.fecha_baja = None
