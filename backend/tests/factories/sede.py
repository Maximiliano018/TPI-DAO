"""Fábricas de sedes de dominio con datos válidos por defecto."""

from datetime import time
from itertools import count

import factory

from app.models.sede import EstadoSede, Sede, UsuarioRef
from app.models.valores import (
    CodigoSede,
    Contacto,
    Direccion,
    FranjaHoraria,
    Localidad,
)
from app.services.sede_service import DatosSede
from tests.fakes.reloj import RelojFijo

CORDOBA = Localidad(
    id=1, nombre="Córdoba", departamento="Capital", provincia_id=1, provincia="Córdoba"
)
RIO_CUARTO = Localidad(
    id=2, nombre="Río Cuarto", departamento="Río Cuarto", provincia_id=1, provincia="Córdoba"
)
ADMIN_REF = UsuarioRef(1, "Admin")
_n = count(1)


def franjas_tipicas() -> list[FranjaHoraria]:
    """Lunes a viernes de 9 a 13 y de 15 a 19."""
    resultado = []
    for dia in range(1, 6):
        resultado += [
            FranjaHoraria(dia, time(9), time(13)),
            FranjaHoraria(dia, time(15), time(19)),
        ]
    return resultado


def datos_sede(**over) -> DatosSede:
    """Datos de alta válidos; ``over`` sobrescribe campos."""
    n = next(_n)
    datos = {
        "nombre": f"Sede {n}",
        "calle": "Av. Colón",
        "numero": str(1000 + n),
        "localidad_id": CORDOBA.id,
        "telefono": "+543514221234",
        "email": "sede@red.example",
        "responsable": "Laura Pérez",
        "horarios": franjas_tipicas(),
    }
    datos.update(over)
    return DatosSede(**datos)


class SedeFactory(factory.Factory):
    class Meta:
        model = Sede

    id = factory.Sequence(lambda n: n + 1)
    codigo = factory.Sequence(lambda n: CodigoSede.crear(f"SEDE_{n}"))
    nombre = factory.Sequence(lambda n: f"Sede {n}")
    direccion = factory.Sequence(lambda n: Direccion.crear("Av. Colón", str(100 + n), CORDOBA))
    contacto = factory.LazyFunction(
        lambda: Contacto.crear("+543514221234", "sede@red.example", "Laura Pérez")
    )
    horarios = factory.LazyFunction(franjas_tipicas)
    estado = EstadoSede.ACTIVA
    version = 1
    creado_en = factory.LazyFunction(lambda: RelojFijo().ahora())
    creado_por = ADMIN_REF
    actualizado_en = factory.LazyFunction(lambda: RelojFijo().ahora())
    actualizado_por = ADMIN_REF
