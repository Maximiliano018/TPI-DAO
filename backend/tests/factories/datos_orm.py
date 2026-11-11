"""Ayudantes para crear filas ORM válidas en las pruebas de integración."""

from datetime import time
from itertools import count

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.security import hashear_clave
from app.db.models import HorarioSedeORM, LocalidadORM, SedeORM, UsuarioORM

_secuencia = count(1)


def crear_admin(sesion: Session, **over) -> UsuarioORM:
    n = next(_secuencia)
    datos = {
        "username": f"admin{n}",
        "password_hash": hashear_clave("x"),
        "nombre": f"Admin {n}",
        "rol": "ADMIN",
        "activo": True,
    }
    datos.update(over)
    usuario = UsuarioORM(**datos)
    sesion.add(usuario)
    sesion.flush()
    return usuario


def crear_sede(sesion: Session, admin: UsuarioORM, **over) -> SedeORM:
    n = next(_secuencia)
    localidad = sesion.scalar(select(LocalidadORM).where(LocalidadORM.nombre == "Córdoba"))
    datos = {
        "codigo": f"SEDE_{n}",
        "nombre": f"Sede {n}",
        "nombre_normalizado": f"sede {n}",
        "calle": "Av. Colón",
        "numero": str(1000 + n),
        "localidad_id": localidad.id,
        "direccion_normalizada": f"{localidad.id}|avenida colon|{1000 + n}",
        "telefono": "+543514221234",
        "email": "sede@red.example",
        "responsable": "Ana",
        "estado": "ACTIVA",
        "version": 1,
        "creado_por_id": admin.id,
        "actualizado_por_id": admin.id,
    }
    datos.update(over)
    sede = SedeORM(**datos)
    sesion.add(sede)
    sesion.flush()
    return sede


def franja(sede: SedeORM, dia: int, apertura: time, cierre: time) -> HorarioSedeORM:
    return HorarioSedeORM(
        sede_id=sede.id, dia_semana=dia, hora_apertura=apertura, hora_cierre=cierre
    )
