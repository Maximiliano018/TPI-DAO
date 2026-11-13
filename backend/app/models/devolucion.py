"""Devoluciones y multas.

La devolución cierra un préstamo ``Activo`` o ``Vencido`` y registra en qué estado llegó el
ejemplar. Si es fuera de término, nace una multa con la política de cálculo vigente (Strategy).
El día de vencimiento todavía está en término (CA-DEV-05).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.exceptions import TransicionInvalida
from app.models.policies.multa import PoliticaMulta
from app.models.prestamo import Prestamo
from app.models.usuario import UsuarioRef
from app.models.valores import error_de_campo

OBSERVACIONES_MAX = 300


class EstadoRecibido(StrEnum):
    BUENO = "BUENO"
    REGULAR = "REGULAR"
    DANADO = "DANADO"
    EXTRAVIADO = "EXTRAVIADO"


class EstadoMulta(StrEnum):
    PENDIENTE = "PENDIENTE"
    SALDADA = "SALDADA"


@dataclass
class Multa:
    id: int | None
    prestamo_id: int
    socio_id: int
    dias_atraso: int
    monto_por_dia: Decimal
    monto_total: Decimal
    fecha_generacion: datetime
    estado: EstadoMulta = EstadoMulta.PENDIENTE
    fecha_saldada: datetime | None = None
    saldada_por: UsuarioRef | None = None
    # Datos para mostrar.
    numero_prestamo: str | None = None
    socio_nombre: str | None = None
    libro_titulo: str | None = None

    def saldar(self, actor: UsuarioRef, ahora: datetime) -> None:
        """Marca la multa como saldada (el cobro real queda fuera del sistema, RF-DEV-06).

        Raises:
            TransicionInvalida: Ya estaba saldada.
        """
        if self.estado == EstadoMulta.SALDADA:
            raise TransicionInvalida(
                "La multa ya está saldada.", [{"campo": "estado", "problema": "SALDADA"}]
            )
        self.estado = EstadoMulta.SALDADA
        self.fecha_saldada = ahora
        self.saldada_por = actor


@dataclass
class Devolucion:
    id: int | None
    prestamo_id: int
    sede_id: int
    fecha_hora: datetime
    estado_recibido: EstadoRecibido
    dias_atraso: int
    observaciones: str | None
    registrada_por: UsuarioRef | None

    @classmethod
    def registrar(
        cls,
        *,
        prestamo: Prestamo,
        fecha_hora: datetime,
        fecha: date,
        hoy: date,
        estado_recibido: EstadoRecibido,
        observaciones: str | None,
        politica: PoliticaMulta,
        actor: UsuarioRef,
    ) -> tuple["Devolucion", Multa | None]:
        """Valida la devolución y calcula la multa si corresponde.

        ``fecha`` es el día de la devolución en la zona de negocio (para contar el atraso).

        Raises:
            TransicionInvalida: El préstamo no está activo ni vencido (CA-DEV-02).
            ErrorDeValidacion: Fecha futura o anterior al inicio (CA-DEV-04), o un daño o
                extravío sin observaciones (CU-DEV-03, A2).
        """
        prestamo.estado.devolver()  # valida el estado antes que los datos
        assert prestamo.id is not None and prestamo.fecha_inicio is not None
        if fecha > hoy:
            raise error_de_campo("fecha_hora", "La fecha de devolución no puede ser futura.")
        if fecha < prestamo.fecha_inicio:
            raise error_de_campo(
                "fecha_hora", "La fecha de devolución no puede ser anterior a la entrega."
            )
        texto = " ".join((observaciones or "").split()) or None
        if texto and len(texto) > OBSERVACIONES_MAX:
            raise error_de_campo("observaciones", "Las observaciones admiten hasta 300 caracteres.")
        if estado_recibido in (EstadoRecibido.DANADO, EstadoRecibido.EXTRAVIADO) and not texto:
            raise error_de_campo(
                "observaciones", "Describa el daño o el extravío en las observaciones."
            )
        dias = prestamo.dias_de_atraso(fecha)
        devolucion = cls(
            id=None,
            prestamo_id=prestamo.id,
            sede_id=prestamo.sede_destino_id,
            fecha_hora=fecha_hora,
            estado_recibido=estado_recibido,
            dias_atraso=dias,
            observaciones=texto,
            registrada_por=actor,
        )
        multa = None
        if dias > 0:
            multa = Multa(
                id=None,
                prestamo_id=prestamo.id,
                socio_id=prestamo.socio_id,
                dias_atraso=dias,
                monto_por_dia=politica.monto_por_dia,
                monto_total=politica.calcular(dias),
                fecha_generacion=fecha_hora,
            )
        return devolucion, multa
