"""Entidad de dominio ``Socio``: datos, estados, causas de inhabilitación, bajas e historial.

Un socio pertenece a la red (no a una sede). Puede estar ``HABILITADO``, ``INHABILITADO`` o
dado de ``BAJA`` (baja lógica). La inhabilitación tiene causas:

* **Automáticas**: un préstamo vencido sin devolver o una multa impaga. No son una decisión: el
  servicio las calcula a partir de los préstamos y multas y llama a ``reevaluar``.
* **Administrativa**: la decide el administrador con un motivo y solo él la levanta. Sobrevive a
  una baja: si el socio se reactiva, vuelve inhabilitado.

Mientras haya al menos una causa vigente el socio queda ``INHABILITADO``; el motivo que se
muestra es el de mayor prioridad (administrativa, préstamo vencido, multa impaga).

La baja tiene un **tipo** (a pedido del socio, administrativa o por fallecimiento) que decide quién
puede reactivarlo. El socio dado de baja conserva su cuenta (salvo por fallecimiento) y puede
pedir la reactivación desde ella; el personal la aprueba o la rechaza, o lo reactiva en mostrador.
Cada cambio queda en el historial (``eventos_pendientes`` hasta que el repositorio lo guarda).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import ClassVar

from app.exceptions import (
    PermisoDenegado,
    SinSolicitudPendiente,
    SocioConActividadPendiente,
    SocioConCausasVigentes,
    SocioEnBaja,
    SocioInhabilitado,
    SocioNoReactivable,
    SocioYaActivo,
    SocioYaEnBaja,
    SocioYaHabilitado,
    SocioYaInhabilitado,
    SolicitudYaPendiente,
)
from app.models.sede import Cambio
from app.models.usuario import UsuarioRef
from app.models.valores import Email, Telefono, error_de_campo, validar_motivo
from app.utils.texto import normalizar

NOMBRE_MAX = 100
DOMICILIO_MAX = 200
FECHA_NACIMIENTO_MINIMA = date(1900, 1, 1)
MENSAJE_SOLICITUD_MAX = 300


class TipoDocumento(StrEnum):
    """Tipos de documento admitidos."""

    DNI = "DNI"
    LE = "LE"
    LC = "LC"
    PASAPORTE = "PASAPORTE"


class EstadoSocio(StrEnum):
    HABILITADO = "HABILITADO"
    INHABILITADO = "INHABILITADO"
    BAJA = "BAJA"


class MotivoInhabilitacion(StrEnum):
    """Causa de inhabilitación. El orden de la enumeración es la prioridad para mostrarla."""

    ADMINISTRATIVA = "ADMINISTRATIVA"
    PRESTAMO_VENCIDO = "PRESTAMO_VENCIDO"
    MULTA_IMPAGA = "MULTA_IMPAGA"


TEXTO_MOTIVO = {
    MotivoInhabilitacion.ADMINISTRATIVA: "decisión administrativa",
    MotivoInhabilitacion.PRESTAMO_VENCIDO: "préstamo vencido",
    MotivoInhabilitacion.MULTA_IMPAGA: "multa impaga",
}

CAUSAS_AUTOMATICAS = frozenset(
    {MotivoInhabilitacion.PRESTAMO_VENCIDO, MotivoInhabilitacion.MULTA_IMPAGA}
)


class TipoBaja(StrEnum):
    """Tipo de baja. El orden de la enumeración es la prioridad (la más grave primero)."""

    FALLECIMIENTO = "FALLECIMIENTO"
    ADMINISTRATIVA = "ADMINISTRATIVA"
    A_PEDIDO = "A_PEDIDO"

    @property
    def requiere_administrador(self) -> bool:
        """La baja a pedido la registra y la revierte el personal; las demás, el administrador."""
        return self != TipoBaja.A_PEDIDO


TEXTO_TIPO_BAJA = {
    TipoBaja.FALLECIMIENTO: "por fallecimiento",
    TipoBaja.ADMINISTRATIVA: "administrativa",
    TipoBaja.A_PEDIDO: "a pedido del socio",
}


class TipoEventoSocio(StrEnum):
    """Eventos del historial del socio."""

    ALTA = "ALTA"
    MODIFICACION = "MODIFICACION"
    INHABILITACION = "INHABILITACION"
    REHABILITACION = "REHABILITACION"
    CAMBIO_AUTOMATICO = "CAMBIO_AUTOMATICO"
    BAJA = "BAJA"
    SOLICITUD_REACTIVACION = "SOLICITUD_REACTIVACION"
    SOLICITUD_RECHAZADA = "SOLICITUD_RECHAZADA"
    REACTIVACION = "REACTIVACION"
    CUENTA_CREADA = "CUENTA_CREADA"


@dataclass(frozen=True)
class Documento:
    """Tipo y número de documento. El número se guarda sin puntos ni espacios.

    DNI, LE y LC: de 7 a 8 dígitos. Pasaporte: de 6 a 9 letras o dígitos, en mayúsculas.
    """

    tipo: TipoDocumento
    numero: str
    _NUMERICO: ClassVar[re.Pattern[str]] = re.compile(r"^\d{7,8}$")
    _PASAPORTE: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Z0-9]{6,9}$")

    @classmethod
    def crear(cls, tipo: TipoDocumento, numero: str) -> "Documento":
        """Normaliza el número (sin puntos, guiones ni espacios) y valida su formato."""
        valor = re.sub(r"[\s.\-]", "", numero or "").upper()
        if tipo == TipoDocumento.PASAPORTE:
            if not cls._PASAPORTE.match(valor):
                raise error_de_campo(
                    "nro_documento", "El pasaporte debe tener de 6 a 9 letras o números."
                )
        elif not cls._NUMERICO.match(valor):
            raise error_de_campo("nro_documento", "El documento debe tener 7 u 8 dígitos.")
        return cls(tipo, valor)

    def __str__(self) -> str:
        return f"{self.tipo.value} {self.numero}"


@dataclass(frozen=True)
class DatosPersonales:
    """Datos editables de un socio, ya validados (ver ``DatosPersonales.crear``)."""

    documento: Documento
    nombre: str
    apellido: str
    fecha_nacimiento: date | None
    email: Email | None
    telefono: Telefono | None
    domicilio: str | None

    @classmethod
    def crear(
        cls,
        *,
        documento: Documento,
        nombre: str,
        apellido: str,
        fecha_nacimiento: date | None,
        email: str | None,
        telefono: str | None,
        domicilio: str | None,
        hoy: date,
    ) -> "DatosPersonales":
        """Valida nombre, apellido, fecha de nacimiento y contacto.

        Se exige al menos un medio de contacto (correo o teléfono).

        Raises:
            ErrorDeValidacion: Algún dato falta o tiene un formato inválido.
        """
        nombre_ok = _texto_obligatorio("nombre", nombre, NOMBRE_MAX)
        apellido_ok = _texto_obligatorio("apellido", apellido, NOMBRE_MAX)
        if fecha_nacimiento is not None and not (
            FECHA_NACIMIENTO_MINIMA <= fecha_nacimiento <= hoy
        ):
            raise error_de_campo(
                "fecha_nacimiento", "La fecha de nacimiento no puede ser futura ni anterior a 1900."
            )
        email_ok = Email.crear(email) if email and email.strip() else None
        telefono_ok = Telefono.crear(telefono) if telefono and telefono.strip() else None
        if email_ok is None and telefono_ok is None:
            raise error_de_campo("email", "Indique al menos un correo o un teléfono de contacto.")
        domicilio_ok = " ".join((domicilio or "").split()) or None
        if domicilio_ok and len(domicilio_ok) > DOMICILIO_MAX:
            raise error_de_campo("domicilio", "El domicilio no puede superar los 200 caracteres.")
        return cls(
            documento, nombre_ok, apellido_ok, fecha_nacimiento, email_ok, telefono_ok, domicilio_ok
        )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"


@dataclass(frozen=True)
class SituacionSocio:
    """Actividad del socio en la red: lo que bloquea su baja y lo que muestra su ficha."""

    prestamos_activos: int = 0
    prestamos_vencidos: int = 0
    multas_pendientes: int = 0
    reservas_activas: int = 0

    @property
    def causas_automaticas(self) -> frozenset[MotivoInhabilitacion]:
        """Causas de inhabilitación que surgen de los préstamos y multas."""
        causas: set[MotivoInhabilitacion] = set()
        if self.prestamos_vencidos:
            causas.add(MotivoInhabilitacion.PRESTAMO_VENCIDO)
        if self.multas_pendientes:
            causas.add(MotivoInhabilitacion.MULTA_IMPAGA)
        return frozenset(causas)


@dataclass(frozen=True)
class CuentaSocio:
    """Cuenta de acceso del socio (usuario con rol ``SOCIO``)."""

    usuario_id: int
    username: str
    activo: bool


@dataclass(frozen=True)
class SolicitudReactivacion:
    """Pedido de reactivación que el socio dado de baja hace desde su cuenta."""

    fecha: datetime
    mensaje: str | None = None


@dataclass
class EventoSocio:
    """Registro del historial del socio (solo inserción).

    ``usuario`` es ``None`` cuando el cambio lo hizo el sistema (inhabilitación automática);
    ``origen`` dice qué lo provocó (``Préstamo P-2026-0012 vencido``).
    """

    tipo: TipoEventoSocio
    fecha_hora: datetime
    usuario: UsuarioRef | None
    estado_anterior: EstadoSocio | None = None
    estado_nuevo: EstadoSocio | None = None
    motivo: str | None = None
    origen: str | None = None
    cambios: list[Cambio] = field(default_factory=list)
    id: int | None = None


@dataclass
class Socio:
    """Socio de la red de bibliotecas.

    Los eventos que generan las operaciones quedan en ``eventos_pendientes`` hasta que el
    repositorio los guarda en el historial.
    """

    id: int | None
    numero_socio: str
    datos: DatosPersonales
    sede_alta_id: int
    estado: EstadoSocio = EstadoSocio.HABILITADO
    causas: set[MotivoInhabilitacion] = field(default_factory=set)
    motivo_administrativo: str | None = None
    fecha_alta: datetime | None = None
    tipo_baja: TipoBaja | None = None
    fecha_baja: datetime | None = None
    motivo_baja: str | None = None
    solicitud: SolicitudReactivacion | None = None
    creado_por: UsuarioRef | None = None
    actualizado_en: datetime | None = None
    actualizado_por: UsuarioRef | None = None
    sede_alta_nombre: str | None = None
    cuenta: CuentaSocio | None = None
    eventos_pendientes: list[EventoSocio] = field(default_factory=list)

    # --- alta y datos ---------------------------------------------------------------------

    @classmethod
    def registrar(
        cls,
        *,
        numero_socio: str,
        datos: DatosPersonales,
        sede_alta_id: int,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Socio":
        """Alta de un socio: queda ``HABILITADO``, sin causas de inhabilitación."""
        socio = cls(
            id=None,
            numero_socio=numero_socio,
            datos=datos,
            sede_alta_id=sede_alta_id,
            fecha_alta=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )
        socio._registrar_evento(
            TipoEventoSocio.ALTA,
            actor,
            ahora,
            con_estado=True,
            cambios=[Cambio(c, None, v) for c, v in _valores(datos).items() if v is not None],
        )
        return socio

    def modificar(self, datos: DatosPersonales, *, actor: UsuarioRef, ahora: datetime) -> bool:
        """Reemplaza los datos personales. Un socio dado de baja no se modifica.

        Returns:
            ``True`` si algo cambió.

        Raises:
            SocioEnBaja: Si el socio está dado de baja (hay que reactivarlo antes).
        """
        self.validar_editable()
        if datos == self.datos:
            return False
        antes, despues = _valores(self.datos), _valores(datos)
        self.datos = datos
        self._registrar_cambio(actor, ahora)
        self._registrar_evento(
            TipoEventoSocio.MODIFICACION,
            actor,
            ahora,
            cambios=[Cambio(c, antes[c], despues[c]) for c in despues if antes[c] != despues[c]],
        )
        return True

    def validar_editable(self) -> None:
        """Guarda de la modificación; el servicio la usa antes de controlar duplicados.

        Raises:
            SocioEnBaja: Si el socio está dado de baja (hay que reactivarlo antes).
        """
        self._exigir_no_baja()

    def registrar_cuenta(self, cuenta: CuentaSocio, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Asocia la cuenta de acceso recién creada y lo deja en el historial."""
        self.cuenta = cuenta
        self._registrar_evento(
            TipoEventoSocio.CUENTA_CREADA,
            actor,
            ahora,
            cambios=[Cambio("cuenta", None, cuenta.username)],
        )

    # --- inhabilitación -------------------------------------------------------------------

    @property
    def motivo_inhabilitacion(self) -> MotivoInhabilitacion | None:
        """Causa vigente de mayor prioridad, o ``None`` si no hay ninguna."""
        return next((m for m in MotivoInhabilitacion if m in self.causas), None)

    @property
    def inhabilitado_administrativamente(self) -> bool:
        return MotivoInhabilitacion.ADMINISTRATIVA in self.causas

    def reevaluar(
        self,
        situacion: SituacionSocio,
        *,
        actor: UsuarioRef | None,
        ahora: datetime,
        origen: str | None = None,
    ) -> bool:
        """Recalcula el estado con las causas automáticas vigentes (RF-SOC-05).

        Se llama en cada evento relevante: préstamo que vence, devolución, multa generada o
        saldada. Conserva la causa administrativa, que solo levanta el administrador.

        Args:
            origen: Qué provocó la reevaluación, para el historial.

        Returns:
            ``True`` si el estado o las causas cambiaron.
        """
        if self.estado == EstadoSocio.BAJA:
            return False
        nuevas = set(situacion.causas_automaticas)
        if self.inhabilitado_administrativamente:
            nuevas.add(MotivoInhabilitacion.ADMINISTRATIVA)
        return self._aplicar_causas(
            nuevas, actor, ahora, evento=TipoEventoSocio.CAMBIO_AUTOMATICO, origen=origen
        )

    def inhabilitar(self, motivo: str, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Inhabilitación administrativa con motivo (solo el administrador, RF-SOC-06).

        Raises:
            ErrorDeValidacion: Motivo vacío, muy corto o muy largo.
            SocioEnBaja: El socio está dado de baja.
            SocioYaInhabilitado: Ya tenía una inhabilitación administrativa.
        """
        self._exigir_no_baja()
        texto = validar_motivo(motivo)
        if self.inhabilitado_administrativamente:
            raise SocioYaInhabilitado(
                f"El socio {self.numero_socio} ya está inhabilitado por decisión administrativa."
            )
        self.motivo_administrativo = texto
        self._aplicar_causas(
            self.causas | {MotivoInhabilitacion.ADMINISTRATIVA},
            actor,
            ahora,
            evento=TipoEventoSocio.INHABILITACION,
            motivo=texto,
        )

    def rehabilitar(
        self,
        situacion: SituacionSocio,
        *,
        actor: UsuarioRef,
        es_administrador: bool,
        ahora: datetime,
    ) -> None:
        """Rehabilita al socio si no quedan causas vigentes.

        El administrador además levanta la inhabilitación administrativa; si queda una causa
        automática, el socio sigue inhabilitado por esa causa. Un bibliotecario no puede
        levantar una inhabilitación administrativa (CA-SOC-10).

        Raises:
            SocioEnBaja: El socio está dado de baja.
            PermisoDenegado: Un bibliotecario intenta levantar una inhabilitación administrativa.
            SocioYaHabilitado: No había nada que levantar.
            SocioConCausasVigentes: Siguen vigentes causas automáticas (y no había una
                administrativa que levantar).
        """
        self._exigir_no_baja()
        automaticas = set(situacion.causas_automaticas)
        if self.inhabilitado_administrativamente:
            if not es_administrador:
                raise PermisoDenegado(
                    "Solo un administrador puede levantar una inhabilitación administrativa."
                )
            self.motivo_administrativo = None
            self._aplicar_causas(automaticas, actor, ahora, evento=TipoEventoSocio.REHABILITACION)
            return
        if automaticas:
            raise SocioConCausasVigentes(
                f"El socio {self.numero_socio} sigue inhabilitado: "
                + ", ".join(TEXTO_MOTIVO[c] for c in MotivoInhabilitacion if c in automaticas)
                + ".",
                [{"campo": "causas", "problema": c.value} for c in sorted(automaticas)],
            )
        if self.estado == EstadoSocio.HABILITADO:
            raise SocioYaHabilitado(f"El socio {self.numero_socio} ya está habilitado.")
        self._aplicar_causas(set(), actor, ahora, evento=TipoEventoSocio.REHABILITACION)

    # --- baja y reactivación --------------------------------------------------------------

    def dar_de_baja(
        self,
        situacion: SituacionSocio,
        tipo: TipoBaja,
        motivo: str,
        *,
        actor: UsuarioRef,
        es_administrador: bool,
        ahora: datetime,
    ) -> None:
        """Baja lógica: solo sin préstamos en curso ni multas pendientes (RF-SOC-09).

        La baja a pedido del socio la registra el personal; la administrativa y la de
        fallecimiento, solo el administrador. Una inhabilitación administrativa **se conserva**:
        si el socio se reactiva, vuelve inhabilitado. Las reservas activas no impiden la baja: el
        servicio las cancela.

        Raises:
            ErrorDeValidacion: Motivo inválido.
            SocioYaEnBaja: Ya estaba dado de baja.
            PermisoDenegado: Un bibliotecario intenta una baja administrativa o por fallecimiento.
            SocioConActividadPendiente: Tiene préstamos en curso o multas pendientes.
        """
        texto = validar_motivo(motivo)
        if self.estado == EstadoSocio.BAJA:
            raise SocioYaEnBaja(f"El socio {self.numero_socio} ya está dado de baja.")
        if tipo.requiere_administrador and not es_administrador:
            raise PermisoDenegado(
                f"Solo un administrador registra una baja {TEXTO_TIPO_BAJA[tipo]}."
            )
        pendientes = []
        if situacion.prestamos_activos or situacion.prestamos_vencidos:
            cantidad = situacion.prestamos_activos + situacion.prestamos_vencidos
            pendientes.append({"tipo": "PRESTAMOS_EN_CURSO", "cantidad": cantidad})
        if situacion.multas_pendientes:
            pendientes.append(
                {"tipo": "MULTAS_PENDIENTES", "cantidad": situacion.multas_pendientes}
            )
        if pendientes:
            raise SocioConActividadPendiente(
                f"El socio {self.numero_socio} tiene préstamos en curso o multas pendientes.",
                pendientes,
            )
        anterior = self.estado
        self.estado = EstadoSocio.BAJA
        self.causas = {c for c in self.causas if c == MotivoInhabilitacion.ADMINISTRATIVA}
        self.tipo_baja = tipo
        self.fecha_baja = ahora
        self.motivo_baja = texto
        self.solicitud = None
        self._registrar_cambio(actor, ahora)
        self._registrar_evento(
            TipoEventoSocio.BAJA,
            actor,
            ahora,
            con_estado=True,
            estado_anterior=anterior,
            motivo=texto,
            cambios=[Cambio("tipo_baja", None, tipo.value)],
        )

    def reactivar(
        self, *, actor: UsuarioRef, es_administrador: bool, ahora: datetime, origen: str
    ) -> None:
        """Vuelve a dar de alta a un socio dado de baja, en lugar de duplicarlo.

        Vuelve ``HABILITADO``, o ``INHABILITADO`` si tenía una inhabilitación administrativa
        (no se borra con la baja). Limpia la baja y una solicitud pendiente.

        Args:
            origen: Cómo se reactivó (en mostrador o por una solicitud aprobada).

        Raises:
            SocioYaActivo: No estaba dado de baja.
            SocioNoReactivable: La baja fue por fallecimiento.
            PermisoDenegado: Un bibliotecario intenta reactivar una baja administrativa.
        """
        self._exigir_reactivable(es_administrador)
        anterior = self.estado
        self.estado = EstadoSocio.INHABILITADO if self.causas else EstadoSocio.HABILITADO
        self.tipo_baja = None
        self.fecha_baja = None
        self.motivo_baja = None
        self.solicitud = None
        self._registrar_cambio(actor, ahora)
        self._registrar_evento(
            TipoEventoSocio.REACTIVACION,
            actor,
            ahora,
            con_estado=True,
            estado_anterior=anterior,
            origen=origen,
        )

    def solicitar_reactivacion(
        self, mensaje: str | None, *, actor: UsuarioRef, ahora: datetime
    ) -> None:
        """El socio dado de baja pide volver desde su cuenta; el personal decide.

        Raises:
            SocioYaActivo: No está dado de baja.
            SocioNoReactivable: La baja fue por fallecimiento.
            SolicitudYaPendiente: Ya hay una solicitud sin resolver.
            ErrorDeValidacion: Mensaje de más de 300 caracteres.
        """
        self._exigir_en_baja()
        if self.solicitud is not None:
            raise SolicitudYaPendiente(
                "Ya hay una solicitud de reactivación pendiente desde el "
                f"{self.solicitud.fecha.strftime('%d/%m/%Y')}."
            )
        texto = " ".join((mensaje or "").split()) or None
        if texto and len(texto) > MENSAJE_SOLICITUD_MAX:
            raise error_de_campo("mensaje", "El mensaje no puede superar los 300 caracteres.")
        self.solicitud = SolicitudReactivacion(ahora, texto)
        self._registrar_evento(TipoEventoSocio.SOLICITUD_REACTIVACION, actor, ahora, motivo=texto)

    def exigir_solicitud_pendiente(self) -> None:
        """Raises: SinSolicitudPendiente: Si no hay una solicitud que resolver."""
        if self.solicitud is None:
            raise SinSolicitudPendiente(
                f"El socio {self.numero_socio} no tiene una solicitud de reactivación pendiente."
            )

    def rechazar_solicitud(
        self, motivo: str, *, actor: UsuarioRef, es_administrador: bool, ahora: datetime
    ) -> None:
        """Rechaza la solicitud con un motivo; el socio sigue en baja y puede volver a pedir.

        Raises:
            SinSolicitudPendiente: No hay solicitud.
            PermisoDenegado: Un bibliotecario intenta resolver la de una baja administrativa.
            ErrorDeValidacion: Motivo inválido.
        """
        self.exigir_solicitud_pendiente()
        self._exigir_reactivable(es_administrador)
        texto = validar_motivo(motivo)
        self.solicitud = None
        self._registrar_cambio(actor, ahora)
        self._registrar_evento(TipoEventoSocio.SOLICITUD_RECHAZADA, actor, ahora, motivo=texto)

    @property
    def reactivable(self) -> bool:
        """En baja y no por fallecimiento."""
        return self.estado == EstadoSocio.BAJA and self.tipo_baja != TipoBaja.FALLECIMIENTO

    # --- guardas para otros módulos -------------------------------------------------------

    def validar_puede_operar(self) -> None:
        """Guarda de préstamos y reservas: el socio tiene que estar habilitado (RF-SOC-07).

        Raises:
            SocioEnBaja: Está dado de baja.
            SocioInhabilitado: Está inhabilitado (el mensaje indica la causa).
        """
        self._exigir_no_baja()
        motivo = self.motivo_inhabilitacion
        if motivo is not None:
            raise SocioInhabilitado(
                f"El socio {self.numero_socio} está inhabilitado por {TEXTO_MOTIVO[motivo]}.",
                [{"campo": "socio_id", "problema": "inhabilitado", "motivo": motivo.value}],
            )

    @property
    def puede_operar(self) -> bool:
        return self.estado == EstadoSocio.HABILITADO

    # --- internos -------------------------------------------------------------------------

    def _exigir_no_baja(self) -> None:
        if self.estado == EstadoSocio.BAJA:
            raise SocioEnBaja(
                f"El socio {self.numero_socio} está dado de baja.",
                [{"campo": "socio_id", "problema": "dado_de_baja"}],
            )

    def _exigir_en_baja(self) -> None:
        if self.estado != EstadoSocio.BAJA:
            raise SocioYaActivo(f"El socio {self.numero_socio} no está dado de baja.")
        if self.tipo_baja == TipoBaja.FALLECIMIENTO:
            raise SocioNoReactivable(
                f"El socio {self.numero_socio} fue dado de baja por fallecimiento."
            )

    def _exigir_reactivable(self, es_administrador: bool) -> None:
        self._exigir_en_baja()
        assert self.tipo_baja is not None
        if self.tipo_baja.requiere_administrador and not es_administrador:
            raise PermisoDenegado(
                f"Solo un administrador resuelve una baja {TEXTO_TIPO_BAJA[self.tipo_baja]}."
            )

    def _aplicar_causas(
        self,
        causas: set[MotivoInhabilitacion],
        actor: UsuarioRef | None,
        ahora: datetime,
        *,
        evento: TipoEventoSocio,
        motivo: str | None = None,
        origen: str | None = None,
    ) -> bool:
        estado = EstadoSocio.INHABILITADO if causas else EstadoSocio.HABILITADO
        if causas == self.causas and estado == self.estado:
            return False
        anterior, causas_anteriores = self.estado, self.causas
        self.causas = causas
        self.estado = estado
        self._registrar_cambio(actor, ahora)
        self._registrar_evento(
            evento,
            actor,
            ahora,
            con_estado=True,
            estado_anterior=anterior,
            motivo=motivo,
            origen=origen,
            cambios=[Cambio("causas", _ordenadas(causas_anteriores), _ordenadas(causas))],
        )
        return True

    def _registrar_cambio(self, actor: UsuarioRef | None, ahora: datetime) -> None:
        self.actualizado_en = ahora
        if actor is not None:
            self.actualizado_por = actor

    def _registrar_evento(
        self,
        tipo: TipoEventoSocio,
        actor: UsuarioRef | None,
        ahora: datetime,
        *,
        con_estado: bool = False,
        estado_anterior: EstadoSocio | None = None,
        motivo: str | None = None,
        origen: str | None = None,
        cambios: list[Cambio] | None = None,
    ) -> None:
        """Agrega un evento al historial; ``con_estado`` registra el estado anterior y el nuevo."""
        self.eventos_pendientes.append(
            EventoSocio(
                tipo=tipo,
                fecha_hora=ahora,
                usuario=actor,
                estado_anterior=estado_anterior if con_estado else None,
                estado_nuevo=self.estado if con_estado else None,
                motivo=motivo,
                origen=origen,
                cambios=cambios or [],
            )
        )


def _valores(datos: DatosPersonales) -> dict[str, str | None]:
    """Datos personales en una forma comparable y serializable (para el historial)."""
    return {
        "tipo_documento": datos.documento.tipo.value,
        "nro_documento": datos.documento.numero,
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "fecha_nacimiento": datos.fecha_nacimiento.isoformat() if datos.fecha_nacimiento else None,
        "email": datos.email.valor if datos.email else None,
        "telefono": datos.telefono.valor if datos.telefono else None,
        "domicilio": datos.domicilio,
    }


def _ordenadas(causas: set[MotivoInhabilitacion]) -> list[str]:
    return [c.value for c in MotivoInhabilitacion if c in causas]


def formatear_numero_socio(secuencia: int) -> str:
    """Número de socio legible: la secuencia con 5 dígitos (``00045``)."""
    return f"{secuencia:05d}"


def clave_persona(nombre: str, apellido: str) -> str:
    """Nombre y apellido normalizados para detectar posibles duplicados."""
    return normalizar(f"{nombre} {apellido}")


def _texto_obligatorio(campo: str, texto: str, maximo: int) -> str:
    valor = " ".join((texto or "").split())
    if not valor:
        raise error_de_campo(campo, f"El {campo} es obligatorio.")
    if len(valor) > maximo:
        raise error_de_campo(campo, f"El {campo} no puede superar los {maximo} caracteres.")
    return valor
