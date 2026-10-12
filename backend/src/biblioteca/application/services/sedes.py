"""Sedes: casos de uso (ABM, horarios, baja) y consultas.

- Casos de uso (modifican datos): verifican permisos, pasan por la entidad `Sede` y
  confirman con la unidad de trabajo. La regla de negocio la decide la entidad.
- Consultas (solo lectura): van directo a las tablas y devuelven diccionarios.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.autorizacion import exigir_rol
from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.enums import EstadoEjemplar, Rol
from biblioteca.domain.errors import DuplicadoError, NoEncontrado
from biblioteca.domain.repositories import UnidadDeTrabajo
from biblioteca.infrastructure.db.tables import ejemplar, horario_sede, sede

# ------------------------------------------------------------------------ Casos de uso


@dataclass(frozen=True)
class DatosSede:
    nombre: str
    direccion: str
    localidad: str
    telefono: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class FranjaHoraria:
    dia_semana: int
    hora_apertura: time
    hora_cierre: time


def registrar_sede(
    uow: UnidadDeTrabajo, actor: UsuarioActual, codigo: str, datos: DatosSede
) -> int:
    exigir_rol(actor, Rol.ADMIN)
    nueva = Sede(
        codigo, datos.nombre, datos.direccion, datos.localidad, datos.telefono, datos.email
    )
    if uow.sedes.existe_codigo(nueva.codigo):
        raise DuplicadoError(f"Ya existe una sede con el código {nueva.codigo}")
    if uow.sedes.existe_nombre(nueva.nombre):
        raise DuplicadoError(f"Ya existe una sede llamada {nueva.nombre}")
    uow.sedes.agregar(nueva)
    uow.confirmar()
    assert nueva.id is not None
    return nueva.id


def actualizar_sede(
    uow: UnidadDeTrabajo, actor: UsuarioActual, sede_id: int, datos: DatosSede
) -> None:
    exigir_rol(actor, Rol.ADMIN)
    existente = _cargar(uow, sede_id)
    existente.actualizar_datos(
        datos.nombre, datos.direccion, datos.localidad, datos.telefono, datos.email
    )
    if uow.sedes.existe_nombre(existente.nombre, excepto_id=sede_id):
        raise DuplicadoError(f"Ya existe una sede llamada {existente.nombre}")
    uow.confirmar()


def definir_horarios(
    uow: UnidadDeTrabajo, actor: UsuarioActual, sede_id: int, franjas: list[FranjaHoraria]
) -> None:
    """Reemplaza todos los horarios de la sede."""
    exigir_rol(actor, Rol.ADMIN)
    _cargar(uow, sede_id).definir_horarios(
        HorarioSede(f.dia_semana, f.hora_apertura, f.hora_cierre) for f in franjas
    )
    uow.confirmar()


def dar_de_baja_sede(
    uow: UnidadDeTrabajo, actor: UsuarioActual, sede_id: int, ahora: datetime
) -> None:
    exigir_rol(actor, Rol.ADMIN)
    _cargar(uow, sede_id).dar_de_baja(
        ahora, tiene_actividad_abierta=uow.sedes.tiene_actividad_abierta(sede_id)
    )
    uow.confirmar()


def reactivar_sede(uow: UnidadDeTrabajo, actor: UsuarioActual, sede_id: int) -> None:
    exigir_rol(actor, Rol.ADMIN)
    _cargar(uow, sede_id).reactivar()
    uow.confirmar()


def _cargar(uow: UnidadDeTrabajo, sede_id: int) -> Sede:
    encontrada = uow.sedes.obtener(sede_id)
    if encontrada is None:
        raise NoEncontrado(f"No existe la sede {sede_id}")
    return encontrada


# ------------------------------------------------------------------------- Consultas


def listar_sedes(db: Session) -> list[dict[str, Any]]:
    return _consultar_sedes(db, sede_id=None)


def obtener_sede(db: Session, sede_id: int) -> dict[str, Any]:
    resultado = _consultar_sedes(db, sede_id=sede_id)
    if not resultado:
        raise NoEncontrado(f"No existe la sede {sede_id}")
    return resultado[0]


def _consultar_sedes(db: Session, sede_id: int | None) -> list[dict[str, Any]]:
    ejemplares = (
        select(func.count())
        .where(ejemplar.c.sede_id == sede.c.id, ejemplar.c.estado != EstadoEjemplar.BAJA)
        .scalar_subquery()
    )
    consulta = select(sede, ejemplares.label("cantidad_ejemplares")).order_by(sede.c.nombre)
    if sede_id is not None:
        consulta = consulta.where(sede.c.id == sede_id)
    sedes = [dict(fila) for fila in db.execute(consulta).mappings()]

    horarios: dict[int, list[dict[str, Any]]] = {}
    consulta_horarios = select(horario_sede).order_by(
        horario_sede.c.dia_semana, horario_sede.c.hora_apertura
    )
    if sede_id is not None:
        consulta_horarios = consulta_horarios.where(horario_sede.c.sede_id == sede_id)
    for h in db.execute(consulta_horarios).mappings():
        horarios.setdefault(h["sede_id"], []).append(
            {
                "dia_semana": h["dia_semana"],
                "hora_apertura": h["hora_apertura"],
                "hora_cierre": h["hora_cierre"],
            }
        )

    for s in sedes:
        s["horarios"] = horarios.get(s["id"], [])
    return sedes
