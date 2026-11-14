"""Entidad de dominio ``Ejemplar``: la copia física de un libro, con sede y estados.

El estado de disponibilidad sigue el patrón State (``models/states/ejemplar.py``): ``Ejemplar``
es el **contexto**, que delega cada operación en su estado actual, reemplaza el estado por el
que este devuelve y registra un movimiento en su historial (RF-CAT-06). El estado no se edita
directamente: lo cambian los procesos de préstamo, envío, reserva y devolución (CU-CAT-03, A1).

El historial registra también los cambios que no son de disponibilidad: estado físico,
observaciones y sede (donde está y a cuál pertenece). Cada movimiento guarda esos cambios como
``Cambio(campo, antes, despues)``.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.exceptions import ConflictoDeVersion, EjemplarNoDisponible
from app.models.sede import Cambio
from app.models.states.ejemplar import (
    TEXTO_ESTADO,
    Disponible,
    EstadoEjemplar,
    EstadoEjemplarEnum,
)
from app.models.usuario import UsuarioRef
from app.models.valores import error_de_campo, validar_motivo

CODIGO_PATRON = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,29}$")
OBSERVACIONES_MAX = 300


class EstadoFisico(StrEnum):
    NUEVO = "NUEVO"
    BUENO = "BUENO"
    REGULAR = "REGULAR"
    DANADO = "DANADO"


def validar_codigo_inventario(texto: str) -> str:
    """Código de inventario en mayúsculas: 3 a 30 letras, números o guiones (``CEN-000123``)."""
    valor = (texto or "").strip().upper()
    if not CODIGO_PATRON.match(valor):
        raise error_de_campo(
            "codigo_inventario",
            "El código de inventario debe tener de 3 a 30 letras, números o guiones.",
        )
    return valor


def _observaciones(texto: str | None) -> str | None:
    valor = " ".join((texto or "").split()) or None
    if valor and len(valor) > OBSERVACIONES_MAX:
        raise error_de_campo("observaciones", "Las observaciones admiten hasta 300 caracteres.")
    return valor


CAMPO_ESTADO_FISICO = "estado_fisico"
CAMPO_OBSERVACIONES = "observaciones"
CAMPO_SEDE_ACTUAL = "sede_actual"
CAMPO_SEDE_PROPIETARIA = "sede_propietaria"


class TipoMovimiento(StrEnum):
    """Qué registra un movimiento (se deduce de su contenido, no se guarda)."""

    ALTA = "ALTA"
    CAMBIO_DE_ESTADO = "CAMBIO_DE_ESTADO"
    TRASLADO = "TRASLADO"
    CAMBIO_DE_UBICACION = "CAMBIO_DE_UBICACION"
    MODIFICACION = "MODIFICACION"


@dataclass(frozen=True)
class MovimientoEjemplar:
    """Un cambio del ejemplar (fuente de su trazabilidad).

    ``estado_anterior`` y ``estado_nuevo`` son iguales cuando el movimiento no cambia la
    disponibilidad (por ejemplo, un cambio de estado físico). En ``cambios`` las sedes van por
    id; el repositorio las devuelve con su nombre al leer el historial.
    """

    estado_anterior: EstadoEjemplarEnum | None
    estado_nuevo: EstadoEjemplarEnum
    fecha_hora: datetime
    usuario: UsuarioRef | None
    observacion: str | None = None
    cambios: tuple[Cambio, ...] = ()

    @property
    def tipo(self) -> TipoMovimiento:
        campos = {c.campo for c in self.cambios}
        if self.estado_anterior is None:
            return TipoMovimiento.ALTA
        if self.estado_anterior != self.estado_nuevo:
            return TipoMovimiento.CAMBIO_DE_ESTADO
        if CAMPO_SEDE_PROPIETARIA in campos:
            return TipoMovimiento.TRASLADO
        if CAMPO_SEDE_ACTUAL in campos:
            return TipoMovimiento.CAMBIO_DE_UBICACION
        return TipoMovimiento.MODIFICACION


@dataclass
class Ejemplar:
    """Copia física de un libro. Pertenece a una sede y puede estar físicamente en otra."""

    id: int | None
    codigo_inventario: str
    libro_id: int
    sede_propietaria_id: int
    sede_actual_id: int
    estado_fisico: EstadoFisico
    estado: EstadoEjemplar = field(default_factory=Disponible)
    observaciones: str | None = None
    fecha_baja: datetime | None = None
    motivo_baja: str | None = None
    version: int = 1
    movimientos_pendientes: list[MovimientoEjemplar] = field(default_factory=list)
    # Datos para mostrar (los completa el repositorio).
    libro_titulo: str | None = None
    sede_propietaria_nombre: str | None = None
    sede_actual_nombre: str | None = None

    @classmethod
    def registrar(
        cls,
        *,
        codigo_inventario: str,
        libro_id: int,
        sede_id: int,
        estado_fisico: EstadoFisico,
        observaciones: str | None,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Ejemplar":
        """Alta: queda ``Disponible`` en su sede, con el primer movimiento del historial."""
        ejemplar = cls(
            id=None,
            codigo_inventario=validar_codigo_inventario(codigo_inventario),
            libro_id=libro_id,
            sede_propietaria_id=sede_id,
            sede_actual_id=sede_id,
            estado_fisico=estado_fisico,
            observaciones=_observaciones(observaciones),
        )
        ejemplar.movimientos_pendientes.append(
            MovimientoEjemplar(None, EstadoEjemplarEnum.DISPONIBLE, ahora, actor, "Alta")
        )
        return ejemplar

    # --- consultas ------------------------------------------------------------------------

    @property
    def estado_nombre(self) -> EstadoEjemplarEnum:
        return self.estado.nombre

    @property
    def esta_disponible(self) -> bool:
        return self.estado_nombre == EstadoEjemplarEnum.DISPONIBLE

    def pertenece_a(self, sede_id: int) -> bool:
        """El ejemplar es de esa sede (sede propietaria)."""
        return self.sede_propietaria_id == sede_id

    def validar_version(self, version: int) -> None:
        """Concurrencia optimista: rechaza si otra persona lo modificó antes."""
        if version != self.version:
            raise ConflictoDeVersion(
                "Otra persona modificó el ejemplar. Recargue para ver los cambios.",
                [{"campo": "version", "problema": "desactualizada"}],
            )

    # --- datos ----------------------------------------------------------------------------

    def modificar(
        self,
        *,
        estado_fisico: EstadoFisico,
        observaciones: str | None,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> bool:
        """Cambia el estado físico y las observaciones (no la disponibilidad).

        El cambio queda en el historial. Un ejemplar dado de baja no se edita.

        Raises:
            TransicionInvalida: El ejemplar está dado de baja.
            ErrorDeValidacion: Observaciones demasiado largas.
        """
        self.estado.validar_edicion()
        obs = _observaciones(observaciones)
        cambios = [
            Cambio(CAMPO_ESTADO_FISICO, self.estado_fisico.value, estado_fisico.value)
            if estado_fisico != self.estado_fisico
            else None,
            Cambio(CAMPO_OBSERVACIONES, self.observaciones, obs)
            if obs != self.observaciones
            else None,
        ]
        if not any(cambios):
            return False
        self.estado_fisico, self.observaciones = estado_fisico, obs
        self._registrar(actor, ahora, "Datos modificados", [c for c in cambios if c])
        return True

    def registrar_estado_fisico(
        self, estado_fisico: EstadoFisico, actor: UsuarioRef | None, ahora: datetime, motivo: str
    ) -> None:
        """Estado físico verificado en una devolución o una recepción (queda en el historial)."""
        if estado_fisico == self.estado_fisico:
            return
        cambio = Cambio(CAMPO_ESTADO_FISICO, self.estado_fisico.value, estado_fisico.value)
        self.estado_fisico = estado_fisico
        self._registrar(actor, ahora, motivo, [cambio])

    def recibir_en(
        self,
        sede_id: int,
        estado_fisico: EstadoFisico,
        *,
        trasladar: bool,
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
    ) -> None:
        """Llega a una sede con un remito: cambia dónde está y su estado físico.

        Con ``trasladar`` (traslado definitivo) también cambia la sede propietaria. Todo queda
        en un único movimiento; el cambio de disponibilidad lo registra la transición que sigue.
        """
        cambios = []
        if sede_id != self.sede_actual_id:
            cambios.append(Cambio(CAMPO_SEDE_ACTUAL, self.sede_actual_id, sede_id))
            self.sede_actual_id = sede_id
        if trasladar and sede_id != self.sede_propietaria_id:
            cambios.append(Cambio(CAMPO_SEDE_PROPIETARIA, self.sede_propietaria_id, sede_id))
            self.sede_propietaria_id = sede_id
        if estado_fisico != self.estado_fisico:
            cambios.append(
                Cambio(CAMPO_ESTADO_FISICO, self.estado_fisico.value, estado_fisico.value)
            )
            self.estado_fisico = estado_fisico
        if cambios:
            self._registrar(actor, ahora, observacion, cambios)

    # --- transiciones (State) -------------------------------------------------------------

    def apartar(self, actor: UsuarioRef | None, ahora: datetime, observacion: str) -> None:
        self._transicion(self.estado.apartar, actor, ahora, observacion)

    def reservar(self, actor: UsuarioRef | None, ahora: datetime, observacion: str) -> None:
        self._transicion(self.estado.reservar, actor, ahora, observacion)

    def prestar(self, actor: UsuarioRef | None, ahora: datetime, observacion: str) -> None:
        self._transicion(self.estado.prestar, actor, ahora, observacion)

    def poner_en_transito(
        self, actor: UsuarioRef | None, ahora: datetime, observacion: str
    ) -> None:
        self._transicion(self.estado.poner_en_transito, actor, ahora, observacion)

    def liberar(self, actor: UsuarioRef | None, ahora: datetime, observacion: str) -> None:
        self._transicion(self.estado.liberar, actor, ahora, observacion)

    def enviar_a_revision(
        self, actor: UsuarioRef | None, ahora: datetime, observacion: str
    ) -> None:
        """Queda en revisión con estado físico ``Dañado``."""
        self._transicion(
            self.estado.enviar_a_revision, actor, ahora, observacion, EstadoFisico.DANADO
        )

    def reparar(self, actor: UsuarioRef, ahora: datetime) -> None:
        """Sale de revisión: vuelve a ``Disponible`` con estado físico ``Regular``."""
        self._transicion(self.estado.reparar, actor, ahora, "Reparado", EstadoFisico.REGULAR)

    def dar_de_baja(self, motivo: str, actor: UsuarioRef, ahora: datetime) -> None:
        """Baja manual: solo de un ejemplar ``Disponible`` o ``En revisión`` (RF-CAT-07).

        Un ejemplar prestado, reservado, apartado o en tránsito primero completa su flujo; si
        hay una incidencia, la baja la registra el cierre del envío o la devolución.

        Raises:
            ErrorDeValidacion: Motivo inválido.
            EjemplarNoDisponible: El ejemplar está en uso.
        """
        texto = validar_motivo(motivo)
        admitidos = (EstadoEjemplarEnum.DISPONIBLE, EstadoEjemplarEnum.EN_REVISION)
        if self.estado_nombre not in admitidos:
            raise EjemplarNoDisponible(
                f"El ejemplar {self.codigo_inventario} no se puede dar de baja: está "
                f"{TEXTO_ESTADO[self.estado_nombre]}.",
                [{"campo": "estado", "problema": self.estado_nombre.value}],
            )
        self.registrar_baja(texto, actor, ahora)

    def registrar_baja(self, motivo: str, actor: UsuarioRef | None, ahora: datetime) -> None:
        """Baja por una incidencia (extravío, destrucción) o por la decisión de baja manual."""
        self._transicion(self.estado.dar_de_baja, actor, ahora, motivo)
        self.fecha_baja = ahora
        self.motivo_baja = motivo

    def _transicion(
        self,
        operacion: Callable[[], EstadoEjemplar],
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
        estado_fisico: EstadoFisico | None = None,
    ) -> None:
        """Delega la operación en el estado actual (State) y registra el movimiento.

        Si el estado rechaza la operación (``TransicionInvalida``), el ejemplar no cambia.
        ``estado_fisico`` se aplica recién cuando la transición fue aceptada.
        """
        anterior = self.estado_nombre
        self.estado = operacion()
        cambios = []
        if estado_fisico is not None and estado_fisico != self.estado_fisico:
            cambios.append(
                Cambio(CAMPO_ESTADO_FISICO, self.estado_fisico.value, estado_fisico.value)
            )
            self.estado_fisico = estado_fisico
        self._registrar(actor, ahora, observacion, cambios, anterior)

    def _registrar(
        self,
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
        cambios: list[Cambio],
        estado_anterior: EstadoEjemplarEnum | None = None,
    ) -> None:
        self.version += 1
        self.movimientos_pendientes.append(
            MovimientoEjemplar(
                estado_anterior or self.estado_nombre,
                self.estado_nombre,
                ahora,
                actor,
                observacion,
                tuple(cambios),
            )
        )
