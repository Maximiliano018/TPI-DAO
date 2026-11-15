"""Pago de una multa: en el mostrador o en línea (simulado).

Una multa se salda con **un** pago aprobado. El de mostrador lo registra el bibliotecario ya
cobrado (efectivo, débito, crédito o transferencia). El pago en línea es una **simulación** para
la demo: el socio lo inicia (queda ``Pendiente``) y en el checkout simulado elige la forma de pago
(tarjeta de crédito, de débito o dinero en cuenta). No hay cobro real ni pasarela externa.

De la tarjeta solo se guardan los **últimos 4 dígitos** (el resto nunca sale del navegador). Para
probar un rechazo, la tarjeta de prueba terminada en ``0002`` se rechaza; cualquier otra se
aprueba. Todo pago aprobado tiene su comprobante (``numero_comprobante``).
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.exceptions import TransicionInvalida
from app.models.usuario import UsuarioRef
from app.models.valores import error_de_campo

COMPROBANTE_MAX = 100


class MedioPago(StrEnum):
    EFECTIVO = "EFECTIVO"
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    EN_LINEA = "EN_LINEA"  # pago en línea simulado del socio
    # Solo para las multas saldadas antes de registrar el medio (migración 0016).
    NO_REGISTRADO = "NO_REGISTRADO"


MEDIOS_DE_MOSTRADOR = frozenset(
    {MedioPago.EFECTIVO, MedioPago.DEBITO, MedioPago.CREDITO, MedioPago.TRANSFERENCIA}
)


class FormaEnLinea(StrEnum):
    """Forma de pago elegida en el checkout simulado."""

    TARJETA_CREDITO = "TARJETA_CREDITO"
    TARJETA_DEBITO = "TARJETA_DEBITO"
    DINERO_EN_CUENTA = "DINERO_EN_CUENTA"


CON_TARJETA = frozenset({FormaEnLinea.TARJETA_CREDITO, FormaEnLinea.TARJETA_DEBITO})
# Tarjeta de prueba que simula un rechazo (como las de prueba de las pasarelas reales).
TARJETA_RECHAZADA = "0002"
_ULTIMOS4 = re.compile(r"^[0-9]{4}$")


class EstadoPago(StrEnum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    CANCELADO = "CANCELADO"


@dataclass
class Pago:
    id: int | None
    multa_id: int
    medio: MedioPago
    monto: Decimal
    estado: EstadoPago
    fecha: datetime
    registrado_por: UsuarioRef | None
    comprobante: str | None = None
    acreditado_en: datetime | None = None
    motivo: str | None = None  # por qué se rechazó o se canceló
    forma_en_linea: FormaEnLinea | None = None
    tarjeta_ultimos4: str | None = None
    # Datos para mostrar y para el comprobante (los completa el repositorio).
    numero_prestamo: str | None = None
    libro_titulo: str | None = None
    dias_atraso: int | None = None
    socio_nombre: str | None = None
    numero_socio: str | None = None

    @property
    def numero_comprobante(self) -> str | None:
        """Número del comprobante de un pago aprobado: ``PG-<año>-<id>``."""
        if self.estado != EstadoPago.APROBADO or self.id is None:
            return None
        return f"PG-{self.fecha.year}-{self.id:06d}"

    @classmethod
    def manual(
        cls,
        *,
        multa_id: int,
        monto: Decimal,
        medio: MedioPago,
        comprobante: str | None,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Pago":
        """El bibliotecario ya cobró en el mostrador: el pago nace aprobado.

        Raises:
            ErrorDeValidacion: Medio que no es de mostrador o comprobante muy largo.
        """
        if medio not in MEDIOS_DE_MOSTRADOR:
            raise error_de_campo(
                "medio", "Elija efectivo, débito, crédito o transferencia para el mostrador."
            )
        texto = " ".join((comprobante or "").split()) or None
        if texto and len(texto) > COMPROBANTE_MAX:
            raise error_de_campo("comprobante", "El comprobante admite hasta 100 caracteres.")
        return cls(
            id=None,
            multa_id=multa_id,
            medio=medio,
            monto=monto,
            estado=EstadoPago.APROBADO,
            fecha=ahora,
            registrado_por=actor,
            comprobante=texto,
            acreditado_en=ahora,
        )

    @classmethod
    def en_linea(
        cls, *, multa_id: int, monto: Decimal, actor: UsuarioRef, ahora: datetime
    ) -> "Pago":
        """El socio inicia el pago en línea: queda pendiente hasta que elige el resultado."""
        return cls(
            id=None,
            multa_id=multa_id,
            medio=MedioPago.EN_LINEA,
            monto=monto,
            estado=EstadoPago.PENDIENTE,
            fecha=ahora,
            registrado_por=actor,
        )

    @property
    def pendiente(self) -> bool:
        return self.estado == EstadoPago.PENDIENTE

    def pagar_en_linea(
        self, forma: FormaEnLinea, tarjeta_ultimos4: str | None, ahora: datetime
    ) -> bool:
        """El socio confirma el pago en el checkout simulado. Devuelve si se aprobó.

        Raises:
            ErrorDeValidacion: Tarjeta sin sus últimos 4 dígitos, o dígitos con dinero en cuenta.
            TransicionInvalida: El pago ya no está pendiente.
        """
        self._exigir_pendiente()
        if forma in CON_TARJETA:
            if not tarjeta_ultimos4 or not _ULTIMOS4.match(tarjeta_ultimos4):
                raise error_de_campo(
                    "tarjeta_ultimos4", "Indique los últimos 4 dígitos de la tarjeta."
                )
        elif tarjeta_ultimos4:
            raise error_de_campo(
                "tarjeta_ultimos4", "El pago con dinero en cuenta no lleva tarjeta."
            )
        self.forma_en_linea = forma
        self.tarjeta_ultimos4 = tarjeta_ultimos4
        if tarjeta_ultimos4 == TARJETA_RECHAZADA:
            self.rechazar("Tarjeta rechazada por el emisor (tarjeta de prueba)")
            return False
        self.aprobar(ahora)
        return True

    def aprobar(self, ahora: datetime) -> None:
        self._exigir_pendiente()
        self.estado = EstadoPago.APROBADO
        self.acreditado_en = ahora

    def rechazar(self, motivo: str) -> None:
        self._exigir_pendiente()
        self.estado = EstadoPago.RECHAZADO
        self.motivo = motivo

    def cancelar(self, motivo: str) -> None:
        """Se abandona el intento: otro pago (el del mostrador) saldó la multa."""
        self._exigir_pendiente()
        self.estado = EstadoPago.CANCELADO
        self.motivo = motivo

    def _exigir_pendiente(self) -> None:
        if not self.pendiente:
            raise TransicionInvalida(
                f"El pago ya está {self.estado.value.lower()}.",
                [{"campo": "estado", "problema": self.estado.value}],
            )
