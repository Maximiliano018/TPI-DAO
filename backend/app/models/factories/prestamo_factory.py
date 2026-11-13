"""Creación de préstamos (patrón Factory).

Un único lugar decide si un préstamo es local o interbibliotecario, con qué política de plazo y
qué reglas valida antes de crearlo (CA-PRE-10). El resto del código trata a todos los préstamos
igual.
"""

from collections.abc import Sequence
from datetime import datetime

from app.exceptions import (
    EjemplarNoDisponible,
    EjemplarNoPerteneceASede,
    LibroYaPrestado,
    LimitePrestamosExcedido,
)
from app.models.ejemplar import Ejemplar
from app.models.parametros import Parametros
from app.models.policies.plazo import PlazoInterbibliotecario, PlazoLocal, PoliticaPlazo
from app.models.prestamo import Prestamo, TipoPrestamo
from app.models.sede import Sede
from app.models.socio import Socio
from app.models.states.ejemplar import TEXTO_ESTADO, EstadoEjemplarEnum
from app.models.usuario import UsuarioRef


class PrestamoFactory:
    """Construye préstamos ``Solicitado`` válidos y elige su política de plazo."""

    def __init__(self, parametros: Parametros) -> None:
        self._parametros = parametros

    def politica(self, tipo: TipoPrestamo) -> PoliticaPlazo:
        """Strategy de plazo según el tipo de préstamo."""
        if tipo == TipoPrestamo.LOCAL:
            return PlazoLocal(self._parametros.plazo_prestamo_local_dias)
        return PlazoInterbibliotecario(self._parametros.plazo_prestamo_inter_dias)

    def crear(
        self,
        *,
        numero: str,
        socio: Socio,
        ejemplar: Ejemplar,
        sede_origen: Sede,
        sede_destino: Sede,
        abiertos_del_socio: Sequence[Prestamo],
        actor: UsuarioRef | None,
        ahora: datetime,
        reservado: bool = False,
    ) -> Prestamo:
        """Valida las reglas del enunciado, aparta el ejemplar y devuelve el préstamo.

        Con ``reservado`` el ejemplar ya está ``Reservado`` para el socio (retiro de una reserva):
        se exige ese estado en lugar de ``Disponible`` y no se aparta. ``actor`` es ``None``
        cuando el préstamo lo genera el sistema al asignar una reserva.

        Raises:
            SedeEnBaja: Origen o destino dados de baja (CA-PRE-04, 05).
            SocioInhabilitado, SocioEnBaja: El socio no puede operar (CA-PRE-02).
            EjemplarNoDisponible: El ejemplar no está disponible (CA-PRE-01, 07).
            EjemplarNoPerteneceASede: El ejemplar no es de la sede origen (CA-PRE-03).
            LimitePrestamosExcedido: El socio ya tiene el máximo de préstamos (CA-PRE-06).
            LibroYaPrestado: El socio ya tiene un préstamo abierto del mismo libro.
        """
        sede_origen.validar_operativa()
        sede_destino.validar_operativa()
        socio.validar_puede_operar()
        assert sede_origen.id is not None and sede_destino.id is not None
        if not ejemplar.pertenece_a(sede_origen.id) or ejemplar.sede_actual_id != sede_origen.id:
            raise EjemplarNoPerteneceASede(
                f"El ejemplar {ejemplar.codigo_inventario} no pertenece a la sede origen "
                f"{sede_origen.nombre}.",
                [{"campo": "ejemplar_id", "problema": "fuera_de_sede_origen"}],
            )
        esperado = EstadoEjemplarEnum.RESERVADO if reservado else EstadoEjemplarEnum.DISPONIBLE
        if ejemplar.estado_nombre != esperado:
            raise EjemplarNoDisponible(
                f"El ejemplar {ejemplar.codigo_inventario} no está disponible: está "
                f"{TEXTO_ESTADO[ejemplar.estado_nombre]}.",
                [{"campo": "ejemplar_id", "problema": ejemplar.estado_nombre.value}],
            )
        maximo = self._parametros.prestamos_maximos_por_socio
        if len(abiertos_del_socio) >= maximo:
            raise LimitePrestamosExcedido(
                f"El socio {socio.numero_socio} ya tiene {maximo} préstamos en curso.",
                [{"campo": "socio_id", "problema": "limite", "maximo": maximo}],
            )
        if any(p.libro_id == ejemplar.libro_id for p in abiertos_del_socio):
            raise LibroYaPrestado(
                f"El socio {socio.numero_socio} ya tiene un préstamo en curso de este libro.",
                [{"campo": "ejemplar_id", "problema": "libro_repetido"}],
            )
        assert socio.id is not None and ejemplar.id is not None
        tipo = (
            TipoPrestamo.LOCAL
            if sede_origen.id == sede_destino.id
            else TipoPrestamo.INTERBIBLIOTECARIO
        )
        prestamo = Prestamo(
            id=None,
            numero=numero,
            tipo=tipo,
            socio_id=socio.id,
            ejemplar_id=ejemplar.id,
            libro_id=ejemplar.libro_id,
            sede_origen_id=sede_origen.id,
            sede_destino_id=sede_destino.id,
            fecha_solicitud=ahora,
            registrado_por=actor,
        )
        prestamo.registrar_alta(actor, ahora)
        if not reservado:
            ejemplar.apartar(actor, ahora, f"Apartado para el préstamo {numero}")
        return prestamo
