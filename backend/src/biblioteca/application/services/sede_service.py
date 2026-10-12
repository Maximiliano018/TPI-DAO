"""Casos de uso de sedes. Es el ejemplo de referencia para el resto de los servicios:

1. Verificar permisos del actor (`exigir_rol` / `exigir_sede`).
2. Abrir la Unidad de Trabajo, cargar entidades con los repositorios.
3. Delegar la regla de negocio en la entidad (no decidir acá).
4. Confirmar con `commit()` y devolver la entidad.
"""

from dataclasses import dataclass
from datetime import time

from biblioteca.application.paginacion import Pagina
from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.autorizacion import exigir_rol
from biblioteca.application.unit_of_work import UnitOfWork
from biblioteca.domain.clock import Reloj
from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import DuplicadoError, NoEncontrado


@dataclass(frozen=True, slots=True)
class DatosSede:
    nombre: str
    direccion: str
    localidad: str
    telefono: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class FranjaHoraria:
    dia_semana: int
    hora_apertura: time
    hora_cierre: time


class SedeService:
    def __init__(self, uow: UnitOfWork, reloj: Reloj) -> None:
        self.uow = uow
        self.reloj = reloj

    # ------------------------------------------------------------------ Consultas

    def obtener(self, sede_id: int) -> Sede:
        with self.uow:
            return self._cargar(sede_id)

    def listar(self, *, solo_activas: bool, limite: int, desde: int) -> Pagina[Sede]:
        with self.uow:
            return Pagina(
                items=self.uow.sedes.listar(solo_activas=solo_activas, limite=limite, desde=desde),
                total=self.uow.sedes.contar(solo_activas=solo_activas),
                limite=limite,
                desde=desde,
            )

    # ------------------------------------------------------------------ Comandos (ADMIN)

    def crear(self, actor: UsuarioActual, codigo: str, datos: DatosSede) -> Sede:
        exigir_rol(actor, Rol.ADMIN)
        sede = Sede(
            codigo, datos.nombre, datos.direccion, datos.localidad, datos.telefono, datos.email
        )
        with self.uow:
            if self.uow.sedes.existe_codigo(sede.codigo):
                raise DuplicadoError(f"Ya existe una sede con el código {sede.codigo}")
            if self.uow.sedes.existe_nombre(sede.nombre):
                raise DuplicadoError(f"Ya existe una sede llamada {sede.nombre}")
            self.uow.sedes.agregar(sede)
            self.uow.commit()
            return sede

    def actualizar(self, actor: UsuarioActual, sede_id: int, datos: DatosSede) -> Sede:
        exigir_rol(actor, Rol.ADMIN)
        with self.uow:
            sede = self._cargar(sede_id)
            sede.actualizar_datos(
                datos.nombre, datos.direccion, datos.localidad, datos.telefono, datos.email
            )
            if self.uow.sedes.existe_nombre(sede.nombre, excepto_id=sede_id):
                raise DuplicadoError(f"Ya existe una sede llamada {sede.nombre}")
            self.uow.commit()
            return sede

    def definir_horarios(
        self, actor: UsuarioActual, sede_id: int, franjas: list[FranjaHoraria]
    ) -> Sede:
        exigir_rol(actor, Rol.ADMIN)
        with self.uow:
            sede = self._cargar(sede_id)
            sede.definir_horarios(
                HorarioSede(f.dia_semana, f.hora_apertura, f.hora_cierre) for f in franjas
            )
            self.uow.commit()
            return sede

    def dar_de_baja(self, actor: UsuarioActual, sede_id: int) -> Sede:
        exigir_rol(actor, Rol.ADMIN)
        with self.uow:
            sede = self._cargar(sede_id)
            sede.dar_de_baja(
                self.reloj.ahora(),
                tiene_actividad_abierta=self.uow.sedes.tiene_actividad_abierta(sede_id),
            )
            self.uow.commit()
            return sede

    def reactivar(self, actor: UsuarioActual, sede_id: int) -> Sede:
        exigir_rol(actor, Rol.ADMIN)
        with self.uow:
            sede = self._cargar(sede_id)
            sede.reactivar()
            self.uow.commit()
            return sede

    def _cargar(self, sede_id: int) -> Sede:
        sede = self.uow.sedes.obtener(sede_id)
        if sede is None:
            raise NoEncontrado(f"No existe la sede {sede_id}")
        return sede
