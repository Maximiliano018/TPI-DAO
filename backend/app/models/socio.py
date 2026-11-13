"""Entidad de dominio ``Socio``: datos, estados y causas de inhabilitación.

Un socio pertenece a la red (no a una sede). Puede estar ``HABILITADO``, ``INHABILITADO`` o
dado de ``BAJA`` (baja lógica). La inhabilitación tiene causas:

* **Automáticas**: un préstamo vencido sin devolver o una multa impaga. No se guardan como
  decisión: el servicio las calcula a partir de los préstamos y multas y llama a ``reevaluar``.
* **Administrativa**: la decide el administrador con un motivo y solo él la levanta.

Mientras haya al menos una causa vigente el socio queda ``INHABILITADO``; el motivo que se
muestra es el de mayor prioridad (administrativa, préstamo vencido, multa impaga).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import ClassVar

from app.exceptions import (
    PermisoDenegado,
    SocioConActividadPendiente,
    SocioConCausasVigentes,
    SocioEnBaja,
    SocioInhabilitado,
    SocioYaActivo,
    SocioYaEnBaja,
    SocioYaHabilitado,
    SocioYaInhabilitado,
)
from app.models.usuario import UsuarioRef
from app.models.valores import Email, Telefono, error_de_campo, validar_motivo
from app.utils.texto import normalizar

NOMBRE_MAX = 100
DOMICILIO_MAX = 200
FECHA_NACIMIENTO_MINIMA = date(1900, 1, 1)


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


@dataclass
class Socio:
    """Socio de la red de bibliotecas."""

    id: int | None
    numero_socio: str
    datos: DatosPersonales
    sede_alta_id: int
    estado: EstadoSocio = EstadoSocio.HABILITADO
    causas: set[MotivoInhabilitacion] = field(default_factory=set)
    motivo_administrativo: str | None = None
    fecha_alta: datetime | None = None
    fecha_baja: datetime | None = None
    motivo_baja: str | None = None
    creado_por: UsuarioRef | None = None
    actualizado_en: datetime | None = None
    actualizado_por: UsuarioRef | None = None
    sede_alta_nombre: str | None = None
    cuenta: CuentaSocio | None = None

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
        return cls(
            id=None,
            numero_socio=numero_socio,
            datos=datos,
            sede_alta_id=sede_alta_id,
            fecha_alta=ahora,
            creado_por=actor,
            actualizado_en=ahora,
            actualizado_por=actor,
        )

    def modificar(self, datos: DatosPersonales, *, actor: UsuarioRef, ahora: datetime) -> bool:
        """Reemplaza los datos personales. Un socio dado de baja no se modifica.

        Returns:
            ``True`` si algo cambió.

        Raises:
            SocioEnBaja: Si el socio está dado de baja (hay que reactivarlo antes).
        """
        self._exigir_no_baja()
        if datos == self.datos:
            return False
        self.datos = datos
        self._registrar_cambio(actor, ahora)
        return True

    # --- inhabilitación -------------------------------------------------------------------

    @property
    def motivo_inhabilitacion(self) -> MotivoInhabilitacion | None:
        """Causa vigente de mayor prioridad, o ``None`` si no hay ninguna."""
        return next((m for m in MotivoInhabilitacion if m in self.causas), None)

    @property
    def inhabilitado_administrativamente(self) -> bool:
        return MotivoInhabilitacion.ADMINISTRATIVA in self.causas

    def reevaluar(
        self, situacion: SituacionSocio, *, actor: UsuarioRef | None, ahora: datetime
    ) -> bool:
        """Recalcula el estado con las causas automáticas vigentes (RF-SOC-05).

        Se llama en cada evento relevante: préstamo que vence, devolución, multa generada o
        saldada. Conserva la causa administrativa, que solo levanta el administrador.

        Returns:
            ``True`` si el estado o las causas cambiaron.
        """
        if self.estado == EstadoSocio.BAJA:
            return False
        nuevas = set(situacion.causas_automaticas)
        if self.inhabilitado_administrativamente:
            nuevas.add(MotivoInhabilitacion.ADMINISTRATIVA)
        return self._aplicar_causas(nuevas, actor, ahora)

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
        self._aplicar_causas(self.causas | {MotivoInhabilitacion.ADMINISTRATIVA}, actor, ahora)

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
            self._aplicar_causas(automaticas, actor, ahora)
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
        self._aplicar_causas(set(), actor, ahora)

    # --- baja y reactivación --------------------------------------------------------------

    def dar_de_baja(
        self, situacion: SituacionSocio, motivo: str, *, actor: UsuarioRef, ahora: datetime
    ) -> None:
        """Baja lógica: solo sin préstamos activos ni multas pendientes (RF-SOC-09).

        Las reservas activas no la impiden: el servicio las cancela al dar la baja.

        Raises:
            ErrorDeValidacion: Motivo inválido.
            SocioYaEnBaja: Ya estaba dado de baja.
            SocioConActividadPendiente: Tiene préstamos en curso o multas pendientes.
        """
        texto = validar_motivo(motivo)
        if self.estado == EstadoSocio.BAJA:
            raise SocioYaEnBaja(f"El socio {self.numero_socio} ya está dado de baja.")
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
        self.estado = EstadoSocio.BAJA
        self.causas = set()
        self.motivo_administrativo = None
        self.fecha_baja = ahora
        self.motivo_baja = texto
        self._registrar_cambio(actor, ahora)

    def reactivar(self, *, actor: UsuarioRef, ahora: datetime) -> None:
        """Vuelve a dar de alta a un socio dado de baja, en lugar de duplicarlo.

        Raises:
            SocioYaActivo: No estaba dado de baja.
        """
        if self.estado != EstadoSocio.BAJA:
            raise SocioYaActivo(f"El socio {self.numero_socio} no está dado de baja.")
        self.estado = EstadoSocio.HABILITADO
        self.fecha_baja = None
        self.motivo_baja = None
        self._registrar_cambio(actor, ahora)

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

    def _aplicar_causas(
        self, causas: set[MotivoInhabilitacion], actor: UsuarioRef | None, ahora: datetime
    ) -> bool:
        estado = EstadoSocio.INHABILITADO if causas else EstadoSocio.HABILITADO
        if causas == self.causas and estado == self.estado:
            return False
        self.causas = causas
        self.estado = estado
        self._registrar_cambio(actor, ahora)
        return True

    def _registrar_cambio(self, actor: UsuarioRef | None, ahora: datetime) -> None:
        self.actualizado_en = ahora
        if actor is not None:
            self.actualizado_por = actor


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
