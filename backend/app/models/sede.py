"""Entidad de dominio ``Sede``: reglas de ciclo de vida, horarios y excepciones."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from app.exceptions import (
    ExcepcionHorarioInvalida,
    ExcepcionHorarioNoEncontrada,
    ExcepcionHorarioSuperpuesta,
    SedeConActividadPendiente,
    SedeEnBaja,
    SedeYaActiva,
    SedeYaEnBaja,
)
from app.models.horario import ExcepcionHorario, validar_horarios
from app.models.policies.verificacion_baja_sede import Impedimento
from app.models.valores import (
    CodigoSede,
    Contacto,
    Direccion,
    FranjaHoraria,
    error_de_campo,
)
from app.utils.texto import normalizar

MOTIVO_MIN = 5
MOTIVO_MAX = 300
NOMBRE_MIN = 3
NOMBRE_MAX = 100
MENSAJE_NO_DISPONIBLE = "La sede solicitada no existe o no está disponible."


class EstadoSede(StrEnum):
    ACTIVA = "ACTIVA"
    BAJA = "BAJA"


class TipoEventoSede(StrEnum):
    ALTA = "ALTA"
    MODIFICACION = "MODIFICACION"
    BAJA = "BAJA"
    REACTIVACION = "REACTIVACION"
    EXCEPCION_AGREGADA = "EXCEPCION_AGREGADA"
    EXCEPCION_ELIMINADA = "EXCEPCION_ELIMINADA"


@dataclass(frozen=True)
class UsuarioRef:
    """Quién realizó una operación (id y nombre para mostrar)."""

    id: int
    nombre: str


@dataclass(frozen=True)
class Cambio:
    """Un campo que cambió, con su valor anterior y el nuevo."""

    campo: str
    antes: Any
    despues: Any

    def como_dict(self) -> dict[str, Any]:
        return {"campo": self.campo, "antes": self.antes, "despues": self.despues}


@dataclass
class EventoSede:
    """Registro de auditoría de una sede (solo inserción)."""

    tipo: TipoEventoSede
    usuario: UsuarioRef
    fecha_hora: datetime
    version_resultante: int
    cambios: list[Cambio] = field(default_factory=list)
    estado_anterior: EstadoSede | None = None
    estado_nuevo: EstadoSede | None = None
    motivo: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class DatosBaja:
    """Cuándo, por qué y quién dio de baja la sede."""

    fecha: datetime
    motivo: str
    usuario: UsuarioRef


def validar_nombre(nombre: str) -> str:
    """Nombre de 3 a 100 caracteres, sin espacios de más."""
    limpio = " ".join((nombre or "").split())
    if not NOMBRE_MIN <= len(limpio) <= NOMBRE_MAX:
        raise error_de_campo("nombre", "El nombre debe tener entre 3 y 100 caracteres.")
    return limpio


def validar_motivo_baja(motivo: str) -> str:
    """Motivo de baja de 5 a 300 caracteres."""
    limpio = " ".join((motivo or "").split())
    if not MOTIVO_MIN <= len(limpio) <= MOTIVO_MAX:
        raise error_de_campo("motivo", "El motivo debe tener entre 5 y 300 caracteres.")
    return limpio


@dataclass
class Sede:
    """Sede de la red. Toda modificación de datos incrementa ``version``.

    Los eventos de auditoría que generan las operaciones quedan en ``eventos_pendientes`` hasta
    que el repositorio los persiste.
    """

    id: int | None
    codigo: CodigoSede
    nombre: str
    direccion: Direccion
    contacto: Contacto
    horarios: list[FranjaHoraria]
    estado: EstadoSede
    version: int
    creado_en: datetime
    creado_por: UsuarioRef
    actualizado_en: datetime
    actualizado_por: UsuarioRef
    excepciones: list[ExcepcionHorario] = field(default_factory=list)
    baja: DatosBaja | None = None
    eventos_pendientes: list[EventoSede] = field(default_factory=list)

    # --- creación -------------------------------------------------------------------------

    @classmethod
    def crear(
        cls,
        *,
        codigo: CodigoSede,
        nombre: str,
        direccion: Direccion,
        contacto: Contacto,
        horarios: list[FranjaHoraria],
        actor: UsuarioRef,
        ahora: datetime,
        direccion_duplicada_confirmada: list[dict[str, Any]] | None = None,
    ) -> "Sede":
        """Crea una sede ``Activa`` (versión 1) y registra el evento ``ALTA``."""
        sede = cls(
            id=None,
            codigo=codigo,
            nombre=validar_nombre(nombre),
            direccion=direccion,
            contacto=contacto,
            horarios=validar_horarios(horarios),
            estado=EstadoSede.ACTIVA,
            version=1,
            creado_en=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )
        cambios = [Cambio(c, None, v) for c, v in sede._valores().items()]
        if direccion_duplicada_confirmada:
            cambios.append(
                Cambio("direccion_duplicada_confirmada", None, direccion_duplicada_confirmada)
            )
        sede._registrar(
            TipoEventoSede.ALTA, actor, ahora, cambios=cambios, estado_nuevo=EstadoSede.ACTIVA
        )
        return sede

    # --- consultas ------------------------------------------------------------------------

    @property
    def nombre_normalizado(self) -> str:
        """Nombre sin mayúsculas ni tildes, para detectar duplicados."""
        return normalizar(self.nombre)

    def esta_activa(self) -> bool:
        return self.estado == EstadoSede.ACTIVA

    def validar_operativa(self) -> None:
        """Guarda que usan los demás módulos antes de operar con la sede.

        Raises:
            SedeEnBaja: Si la sede está dada de baja.
        """
        if not self.esta_activa():
            raise SedeEnBaja(f"La sede {self.nombre} está dada de baja. Reactívela para continuar.")

    def esta_abierta(self, momento_local: datetime) -> bool:
        """Indica si la sede atiende en ese momento (hora de la zona de negocio).

        Combina el horario semanal y las excepciones: un cierre total o parcial que alcance a
        ese momento gana sobre el horario semanal. Una sede en baja nunca está abierta.
        """
        if not self.esta_activa():
            return False
        hora = momento_local.time().replace(second=0, microsecond=0)
        fecha = momento_local.date()
        if any(e.fecha == fecha and e.cierra_en(hora) for e in self.excepciones):
            return False
        dia = momento_local.isoweekday()
        return any(f.dia == dia and f.contiene(hora) for f in self.horarios)

    def excepciones_vigentes(self, hoy: date) -> list[ExcepcionHorario]:
        """Excepciones de hoy y futuras, ordenadas."""
        vigentes = [e for e in self.excepciones if e.fecha >= hoy]
        return sorted(vigentes, key=lambda e: (e.fecha, e.desde or time.min))

    # --- modificación ---------------------------------------------------------------------

    def modificar(
        self,
        *,
        nombre: str,
        direccion: Direccion,
        contacto: Contacto,
        horarios: list[FranjaHoraria],
        actor: UsuarioRef,
        ahora: datetime,
        direccion_duplicada_confirmada: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Reemplaza los datos y el horario semanal. El código no cambia nunca.

        Returns:
            ``True`` si algo cambió; si no cambió nada no se incrementa la versión ni se
            registra un evento.

        Raises:
            SedeEnBaja: Si la sede está dada de baja.
        """
        self.validar_operativa()
        antes = self._valores()
        nuevo_nombre = validar_nombre(nombre)
        nuevos_horarios = validar_horarios(horarios)
        anterior = (self.nombre, self.direccion, self.contacto, self.horarios)
        self.nombre, self.direccion = nuevo_nombre, direccion
        self.contacto, self.horarios = contacto, nuevos_horarios
        despues = self._valores()
        cambios = [Cambio(c, antes[c], despues[c]) for c in despues if antes[c] != despues[c]]
        if not cambios:
            self.nombre, self.direccion, self.contacto, self.horarios = anterior
            return False
        if direccion_duplicada_confirmada:
            cambios.append(
                Cambio("direccion_duplicada_confirmada", None, direccion_duplicada_confirmada)
            )
        self._tocar(actor, ahora)
        self._registrar(TipoEventoSede.MODIFICACION, actor, ahora, cambios=cambios)
        return True

    def cambio_el_domicilio(self, direccion: Direccion) -> bool:
        """Indica si cambió la calle, el número o la localidad respecto del domicilio actual."""
        actual = self.direccion
        return (direccion.calle, direccion.numero, direccion.localidad.id) != (
            actual.calle,
            actual.numero,
            actual.localidad.id,
        )

    # --- baja y reactivación --------------------------------------------------------------

    def dar_de_baja(
        self,
        *,
        motivo: str,
        actor: UsuarioRef,
        ahora: datetime,
        impedimentos: list[Impedimento],
    ) -> None:
        """Pasa la sede a ``Baja`` si no hay actividad pendiente.

        Args:
            motivo: De 5 a 300 caracteres.
            impedimentos: Resultado de la verificación; si no está vacío, la baja se rechaza.

        Raises:
            SedeYaEnBaja: Si ya estaba en baja.
            ErrorDeValidacion: Motivo fuera de rango.
            SedeConActividadPendiente: Si hay impedimentos. No cambia nada.
        """
        if not self.esta_activa():
            raise SedeYaEnBaja(f"La sede {self.nombre} ya está dada de baja.")
        motivo = validar_motivo_baja(motivo)
        if impedimentos:
            resumen = ", ".join(i.etiqueta() for i in impedimentos)
            raise SedeConActividadPendiente(
                f"No se puede dar de baja la sede {self.nombre}: tiene actividad pendiente "
                f"({resumen}). Finalice o transfiera esa actividad y vuelva a intentar.",
                [i.como_dict() for i in impedimentos],
            )
        self.estado = EstadoSede.BAJA
        self.baja = DatosBaja(fecha=ahora, motivo=motivo, usuario=actor)
        self._tocar(actor, ahora)
        self._registrar(
            TipoEventoSede.BAJA,
            actor,
            ahora,
            motivo=motivo,
            estado_anterior=EstadoSede.ACTIVA,
            estado_nuevo=EstadoSede.BAJA,
        )

    def reactivar(self, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Vuelve a ``Activa`` sin condiciones; limpia los datos de la baja.

        Raises:
            SedeYaActiva: Si ya estaba activa.
        """
        if self.esta_activa():
            raise SedeYaActiva(f"La sede {self.nombre} ya está activa.")
        self.estado = EstadoSede.ACTIVA
        self.baja = None
        self._tocar(actor, ahora)
        self._registrar(
            TipoEventoSede.REACTIVACION,
            actor,
            ahora,
            estado_anterior=EstadoSede.BAJA,
            estado_nuevo=EstadoSede.ACTIVA,
        )

    # --- excepciones de horario -----------------------------------------------------------

    def agregar_excepciones(
        self,
        nuevas: list[ExcepcionHorario],
        *,
        actor: UsuarioRef,
        ahora: datetime,
        hoy: date,
    ) -> None:
        """Agrega cierres por fecha (todo o nada).

        No cambia la ``version`` de la sede: las excepciones son un conjunto aparte.

        Raises:
            SedeEnBaja: Si la sede está dada de baja.
            ExcepcionHorarioInvalida: Si alguna fecha es pasada.
            ExcepcionHorarioSuperpuesta: Si se superpone con una existente o entre las nuevas.
        """
        self.validar_operativa()
        for nueva in nuevas:
            if nueva.fecha < hoy:
                raise ExcepcionHorarioInvalida(
                    "No se pueden cargar excepciones en fechas pasadas.",
                    [{"campo": "fecha_desde", "problema": "fecha_pasada"}],
                )
        existentes = list(self.excepciones)
        for nueva in nuevas:
            for otra in existentes:
                if nueva.se_solapa_con(otra):
                    raise ExcepcionHorarioSuperpuesta(
                        f"Ya hay un cierre cargado el {otra.fecha.strftime('%d/%m/%Y')} "
                        "que se superpone.",
                        [{"campo": "fecha_desde", "problema": "superpuesta", **otra.como_dict()}],
                    )
            existentes.append(nueva)
        self.excepciones.extend(nuevas)
        self._tocar_sin_version(actor, ahora)
        self._registrar(
            TipoEventoSede.EXCEPCION_AGREGADA,
            actor,
            ahora,
            cambios=[Cambio("excepcion", None, e.como_dict()) for e in nuevas],
        )

    def quitar_excepcion(
        self, excepcion_id: int, *, actor: UsuarioRef, ahora: datetime, hoy: date
    ) -> None:
        """Elimina una excepción de hoy o futura (las pasadas se conservan).

        Raises:
            SedeEnBaja: Si la sede está dada de baja.
            ExcepcionHorarioNoEncontrada: Si no existe en esta sede.
            ExcepcionHorarioInvalida: Si es de una fecha pasada.
        """
        self.validar_operativa()
        excepcion = next((e for e in self.excepciones if e.id == excepcion_id), None)
        if excepcion is None:
            raise ExcepcionHorarioNoEncontrada("La excepción de horario no existe en esta sede.")
        if excepcion.fecha < hoy:
            raise ExcepcionHorarioInvalida(
                "Las excepciones pasadas se conservan como historial y no se eliminan.",
                [{"campo": "excepcion_id", "problema": "fecha_pasada"}],
            )
        self.excepciones.remove(excepcion)
        self._tocar_sin_version(actor, ahora)
        self._registrar(
            TipoEventoSede.EXCEPCION_ELIMINADA,
            actor,
            ahora,
            cambios=[Cambio("excepcion", excepcion.como_dict(), None)],
        )

    # --- internos -------------------------------------------------------------------------

    def _valores(self) -> dict[str, Any]:
        """Campos auditables, en una forma comparable y serializable."""
        return {
            "nombre": self.nombre,
            "calle": self.direccion.calle,
            "numero": self.direccion.numero,
            "localidad_id": self.direccion.localidad.id,
            "telefono": self.contacto.telefono.valor,
            "email": self.contacto.email.valor,
            "responsable": self.contacto.responsable,
            "codigo": self.codigo.valor,
            "horarios": [
                f.como_dict() for f in sorted(self.horarios, key=lambda f: (f.dia, f.apertura))
            ],
        }

    def _tocar(self, actor: UsuarioRef, ahora: datetime) -> None:
        self.version += 1
        self._tocar_sin_version(actor, ahora)

    def _tocar_sin_version(self, actor: UsuarioRef, ahora: datetime) -> None:
        self.actualizado_en = ahora
        self.actualizado_por = actor

    def _registrar(
        self,
        tipo: TipoEventoSede,
        actor: UsuarioRef,
        ahora: datetime,
        *,
        cambios: list[Cambio] | None = None,
        motivo: str | None = None,
        estado_anterior: EstadoSede | None = None,
        estado_nuevo: EstadoSede | None = None,
    ) -> None:
        self.eventos_pendientes.append(
            EventoSede(
                tipo=tipo,
                usuario=actor,
                fecha_hora=ahora,
                version_resultante=self.version,
                cambios=cambios or [],
                motivo=motivo,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
            )
        )
