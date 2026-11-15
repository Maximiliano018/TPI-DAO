"""Devoluciones y multas.

La devolución cierra un préstamo ``Activo`` o ``Vencido`` y registra en qué estado llegó el
ejemplar. Puede generar hasta dos multas, cada una con su política de cálculo (Strategy):

* **Atraso**, si es fuera de término (el día de vencimiento todavía está en término, CA-DEV-05).
* **Daño** o **extravío**, si el ejemplar volvió ``Dañado`` o el socio lo informó
  ``Extraviado`` (RF-DEV-23). Con el monto en 0, no se cobra.

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
from app.models.policies.multa import PoliticaMulta, PoliticaMultaPorIncidencia, TipoMulta
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


# Tipo de multa que corresponde a cada estado recibido (los demás no generan multa).
MULTA_POR_ESTADO = {
    EstadoRecibido.DANADO: TipoMulta.DANIO,
    EstadoRecibido.EXTRAVIADO: TipoMulta.EXTRAVIO,
}


@dataclass
class Multa:
    """Multa de un préstamo: por atraso (con días y monto por día) o por daño o extravío.

    Un préstamo tiene a lo sumo una multa de cada tipo.
    """

    id: int | None
    prestamo_id: int
    socio_id: int
    dias_atraso: int | None  # solo en la de atraso
    monto_por_dia: Decimal | None  # solo en la de atraso
    monto_total: Decimal
    fecha_generacion: datetime
    estado: EstadoMulta = EstadoMulta.PENDIENTE
    tipo: TipoMulta = TipoMulta.ATRASO
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

    @property
    def concepto(self) -> str:
        """Por qué se cobra, en palabras: «Atraso de 3 días», «Daño del ejemplar»."""
        return concepto_de_multa(self.tipo, self.dias_atraso)

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
        politica_incidencia: PoliticaMultaPorIncidencia | None = None,
    ) -> tuple["Devolucion", list[Multa]]:
        """Valida la devolución y calcula las multas que correspondan.

        Por atraso, con ``politica``; por daño o extravío, con ``politica_incidencia`` (sin
        ella, o con monto 0, no se cobra). Si hay las dos, el tope por préstamo se aplica solo
        a la de atraso (RF-DEV-23).

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
        multas = []
        monto_total = politica.calcular(dias)
        if dias > 0 and monto_total > 0:  # con monto por día en 0 no hay nada que cobrar
            multas.append(
                Multa(
                    id=None,
                    prestamo_id=prestamo.id,
                    socio_id=prestamo.socio_id,
                    dias_atraso=dias,
                    monto_por_dia=politica.monto_por_dia,
                    monto_total=monto_total,
                    fecha_generacion=fecha_hora,
                )
            )
        tipo = MULTA_POR_ESTADO.get(estado_recibido)
        if tipo is not None and politica_incidencia is not None:
            monto = politica_incidencia.calcular(tipo)
            if monto > 0:
                multas.append(
                    Multa(
                        id=None,
                        prestamo_id=prestamo.id,
                        socio_id=prestamo.socio_id,
                        dias_atraso=None,
                        monto_por_dia=None,
                        monto_total=monto,
                        fecha_generacion=fecha_hora,
                        tipo=tipo,
                    )
                )
        return devolucion, multas


def concepto_de_multa(tipo: TipoMulta, dias_atraso: int | None) -> str:
    """Texto del concepto de una multa (fichas, reportes y comprobante)."""
    if tipo == TipoMulta.DANIO:
        return "Daño del ejemplar"
    if tipo == TipoMulta.EXTRAVIO:
        return "Extravío del ejemplar"
    dias = dias_atraso or 0
    return f"Atraso de {dias} día" + ("" if dias == 1 else "s")
