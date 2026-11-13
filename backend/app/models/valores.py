"""Objetos de valor de la sede: se validan al construirse y son inmutables."""

import re
from dataclasses import dataclass
from datetime import time
from typing import ClassVar

from email_validator import EmailNotValidError, validate_email

from app.exceptions import ErrorDeValidacion
from app.utils.texto import normalizar_calle, normalizar_numero


def error_de_campo(campo: str, problema: str) -> ErrorDeValidacion:
    """Error de validación de un campo con el formato de ``detalles`` de la API."""
    return ErrorDeValidacion(problema, [{"campo": campo, "problema": problema}])


MOTIVO_MIN, MOTIVO_MAX = 5, 300


def validar_motivo(texto: str) -> str:
    """Motivo de una baja o una inhabilitación: de 5 a 300 caracteres."""
    valor = " ".join((texto or "").split())
    if not MOTIVO_MIN <= len(valor) <= MOTIVO_MAX:
        raise error_de_campo("motivo", "El motivo debe tener entre 5 y 300 caracteres.")
    return valor


@dataclass(frozen=True)
class CodigoSede:
    """Código corto de sede: 3 a 15 caracteres ``A-Z``, ``0-9`` y ``_``, en mayúsculas."""

    valor: str
    _PATRON: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Z0-9_]{3,15}$")

    @classmethod
    def crear(cls, texto: str) -> "CodigoSede":
        """Normaliza a mayúsculas y valida el formato."""
        valor = (texto or "").strip().upper()
        if not cls._PATRON.match(valor):
            raise error_de_campo(
                "codigo", "El código debe tener de 3 a 15 caracteres: letras, números o guion bajo."
            )
        return cls(valor)


@dataclass(frozen=True)
class Telefono:
    """Teléfono en formato internacional E.164: ``+`` y de 8 a 15 dígitos."""

    valor: str
    _PATRON: ClassVar[re.Pattern[str]] = re.compile(r"^\+[1-9][0-9]{7,14}$")

    @classmethod
    def crear(cls, texto: str) -> "Telefono":
        """Quita espacios, guiones y paréntesis y valida el formato E.164."""
        valor = re.sub(r"[\s\-().]", "", texto or "")
        if not cls._PATRON.match(valor):
            raise error_de_campo(
                "telefono",
                "El teléfono debe estar en formato internacional, por ejemplo +543514221234.",
            )
        return cls(valor)


@dataclass(frozen=True)
class Email:
    """Correo electrónico válido, en minúsculas."""

    valor: str

    @classmethod
    def crear(cls, texto: str) -> "Email":
        """Valida el formato (sin consultar DNS) y pasa a minúsculas."""
        try:
            resultado = validate_email((texto or "").strip(), check_deliverability=False)
        except EmailNotValidError as error:
            raise error_de_campo(
                "email", "El correo electrónico no tiene un formato válido."
            ) from error
        valor = resultado.normalized.lower()
        if len(valor) > 120:
            raise error_de_campo("email", "El correo electrónico es demasiado largo (máximo 120).")
        return cls(valor)


@dataclass(frozen=True)
class Localidad:
    """Localidad del catálogo cerrado, con su provincia."""

    id: int
    nombre: str
    departamento: str
    provincia_id: int
    provincia: str


@dataclass(frozen=True)
class Direccion:
    """Domicilio: calle, número y localidad (la provincia se deduce de la localidad)."""

    calle: str
    numero: str
    localidad: Localidad
    _NUMERO: ClassVar[re.Pattern[str]] = re.compile(r"^(\d{1,6}[A-Za-z]?|[Ss]/[Nn])$")

    @classmethod
    def crear(cls, calle: str, numero: str, localidad: Localidad) -> "Direccion":
        """Valida calle (2 a 100 caracteres) y número (``1250``, ``1250B`` o ``S/N``)."""
        calle = " ".join((calle or "").split())
        numero = (numero or "").strip().upper()
        if not 2 <= len(calle) <= 100:
            raise error_de_campo("calle", "La calle debe tener entre 2 y 100 caracteres.")
        if not cls._NUMERO.match(numero):
            raise error_de_campo("numero", "El número debe ser de puerta (1250, 1250B) o S/N.")
        return cls(calle, numero, localidad)

    def normalizada(self) -> str:
        """Clave para detectar direcciones repetidas: localidad, calle y número normalizados."""
        return (
            f"{self.localidad.id}|{normalizar_calle(self.calle)}|{normalizar_numero(self.numero)}"
        )


@dataclass(frozen=True)
class Contacto:
    """Teléfono, correo y responsable de la sede."""

    telefono: Telefono
    email: Email
    responsable: str

    @classmethod
    def crear(cls, telefono: str, email: str, responsable: str) -> "Contacto":
        """Construye el contacto validando cada dato."""
        responsable = " ".join((responsable or "").split())
        if not 3 <= len(responsable) <= 100:
            raise error_de_campo(
                "responsable", "El responsable debe tener entre 3 y 100 caracteres."
            )
        return cls(Telefono.crear(telefono), Email.crear(email), responsable)


@dataclass(frozen=True)
class FranjaHoraria:
    """Franja de atención de un día de la semana (1 = lunes ... 7 = domingo)."""

    dia: int
    apertura: time
    cierre: time

    def __post_init__(self) -> None:
        from app.exceptions import HorarioInvalido

        if not 1 <= self.dia <= 7:
            raise HorarioInvalido(
                "El día de la semana debe estar entre 1 (lunes) y 7 (domingo).",
                [{"campo": "horarios", "problema": "dia_invalido", "dia": self.dia}],
            )
        if self.apertura.second or self.cierre.second:
            raise HorarioInvalido(
                "Las horas se indican en horas y minutos.",
                [{"campo": "horarios", "problema": "segundos", "dia": self.dia}],
            )
        if self.cierre <= self.apertura:
            raise HorarioInvalido(
                "La hora de cierre debe ser posterior a la de apertura.",
                [{"campo": "horarios", "problema": "cierre_no_posterior", "dia": self.dia}],
            )

    def se_solapa_con(self, otra: "FranjaHoraria") -> bool:
        """Dos franjas contiguas (cierra a las 13:00 y abre a las 13:00) no se solapan."""
        return self.dia == otra.dia and self.apertura < otra.cierre and otra.apertura < self.cierre

    def contiene(self, hora: time) -> bool:
        """Intervalo semiabierto ``[apertura, cierre)``."""
        return self.apertura <= hora < self.cierre

    def como_dict(self) -> dict[str, object]:
        """Forma serializable para el historial."""
        return {
            "dia_semana": self.dia,
            "apertura": self.apertura.strftime("%H:%M"),
            "cierre": self.cierre.strftime("%H:%M"),
        }
