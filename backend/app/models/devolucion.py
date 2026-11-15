"""Devoluciones y multas.

La devolución cierra un préstamo ``Activo`` o ``Vencido`` y registra en qué estado llegó el
ejemplar. Si es fuera de término, nace una multa con la política de cálculo vigente (Strategy).
El día de vencimiento todavía está en término (CA-DEV-05).

Una devolución con fecha anterior al día en que se registra (el socio la entregó antes y se
carga ahora) exige un motivo, y el historial del préstamo deja las dos fechas: la fecha cambia
el atraso y, con él, la multa (RF-DEV-14).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from app.exceptions import TransicionInvalida
from app.models.pago import Pago
from app.models.policies.multa import PoliticaMulta
from app.models.prestamo import Prestamo
from app.models.usuario import UsuarioRef
from app.models.valores import MOTIVO_MAX, MOTIVO_MIN, error_de_campo

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
    # El pago que la saldó y el intento en línea en curso (los completa el repositorio).
    pago_aprobado: "Pago | None" = None
    pago_pendiente: "Pago | None" = None

    @property
    def pendiente(self) -> bool:
        return self.estado == EstadoMulta.PENDIENTE

    def saldar(self, actor: UsuarioRef | None, ahora: datetime) -> None:
        """Marca la multa como saldada con un pago aprobado (RF-DEV-06, 17, 19).

        ``actor`` es quien cobró en el mostrador, o ``None`` si la saldó un pago en línea.

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
    # Cuándo se cargó en el sistema; difiere de ``fecha_hora`` si es retroactiva.
    registrada_en: datetime | None = None
    motivo_fecha: str | None = None

    @property
    def es_retroactiva(self) -> bool:
        return self.motivo_fecha is not None

    def texto_del_historial(self, devuelto: date, registro: date) -> str:
        """Observación del movimiento ``Devuelto``: con las dos fechas si es retroactiva."""
        if not self.es_retroactiva:
            return "Devuelto"
        return (
            f"Devuelto el {devuelto.strftime('%d/%m/%Y')} "
            f"(registrado el {registro.strftime('%d/%m/%Y')}): {self.motivo_fecha}"
        )

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
        ahora: datetime | None = None,
        motivo_fecha: str | None = None,
    ) -> tuple["Devolucion", Multa | None]:
        """Valida la devolución y calcula la multa si corresponde.

        ``fecha`` es el día de la devolución en la zona de negocio (para contar el atraso).
        Si es anterior a ``hoy``, ``motivo_fecha`` es obligatorio (de 5 a 300 caracteres); si es
        de hoy, se ignora.

        Raises:
            TransicionInvalida: El préstamo no está activo ni vencido (CA-DEV-02).
            ErrorDeValidacion: Fecha futura o anterior al inicio (CA-DEV-04), un daño o
                extravío sin observaciones (CU-DEV-03, A2), o una fecha anterior a hoy sin
                motivo (CA-DEV-17).
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
        motivo = None
        if fecha < hoy:
            motivo = " ".join((motivo_fecha or "").split())
            if not MOTIVO_MIN <= len(motivo) <= MOTIVO_MAX:
                raise error_de_campo(
                    "motivo_fecha",
                    "Indique por qué la devolución tiene una fecha anterior a hoy "
                    "(de 5 a 300 caracteres): cambia el atraso y la multa.",
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
            registrada_en=ahora or fecha_hora,
            motivo_fecha=motivo,
        )
        multa = None
        monto_total = politica.calcular(dias)
        if dias > 0 and monto_total > 0:  # con monto por día en 0 no hay nada que cobrar
            multa = Multa(
                id=None,
                prestamo_id=prestamo.id,
                socio_id=prestamo.socio_id,
                dias_atraso=dias,
                monto_por_dia=politica.monto_por_dia,
                monto_total=monto_total,
                fecha_generacion=fecha_hora,
            )
        return devolucion, multa
