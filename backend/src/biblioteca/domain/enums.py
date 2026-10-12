"""Enumeraciones del dominio.

Los valores se guardan tal cual (texto en MAYÚSCULA) en la base de datos, y las
tablas los restringen con CHECK. Ver ARCHITECTURE.md §5.1.
"""

from enum import StrEnum


class Rol(StrEnum):
    ADMIN = "ADMIN"
    BIBLIOTECARIO = "BIBLIOTECARIO"
    LOGISTICA = "LOGISTICA"


class EstadoEjemplar(StrEnum):
    DISPONIBLE = "DISPONIBLE"
    RESERVADO = "RESERVADO"
    PENDIENTE_DESPACHO = "PENDIENTE_DESPACHO"
    EN_TRANSITO = "EN_TRANSITO"
    PRESTADO = "PRESTADO"
    EN_REVISION = "EN_REVISION"
    BAJA = "BAJA"


class CondicionFisica(StrEnum):
    BUENA = "BUENA"
    REGULAR = "REGULAR"
    DANADA = "DANADA"


class MotivoBaja(StrEnum):
    EXTRAVIO = "EXTRAVIO"
    DESTRUCCION = "DESTRUCCION"
    DANO = "DANO"
    DESCARTE = "DESCARTE"


class EstadoPrestamo(StrEnum):
    EN_ENVIO = "EN_ENVIO"
    LISTO_PARA_RETIRO = "LISTO_PARA_RETIRO"
    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    CANCELADO = "CANCELADO"


class MotivoCancelacion(StrEnum):
    ENVIO_CANCELADO = "ENVIO_CANCELADO"
    ENVIO_EXTRAVIADO = "ENVIO_EXTRAVIADO"
    ENVIO_DANADO = "ENVIO_DANADO"
    ENVIO_DESTRUIDO = "ENVIO_DESTRUIDO"
    NO_RETIRADO = "NO_RETIRADO"
    DESISTIDO = "DESISTIDO"


class EstadoMulta(StrEnum):
    PENDIENTE = "PENDIENTE"
    SALDADA = "SALDADA"


class EstadoReserva(StrEnum):
    PENDIENTE = "PENDIENTE"
    ASIGNADA = "ASIGNADA"
    CUMPLIDA = "CUMPLIDA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"


class Sentido(StrEnum):
    IDA = "IDA"
    VUELTA = "VUELTA"


class EstadoRemito(StrEnum):
    GENERADO = "GENERADO"
    EMPAQUETADO = "EMPAQUETADO"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDO = "RECIBIDO"
    EXTRAVIADO = "EXTRAVIADO"
    CANCELADO = "CANCELADO"


class ResultadoRevision(StrEnum):
    CONFORME = "CONFORME"
    DANADO = "DANADO"
    DESTRUIDO = "DESTRUIDO"


class TipoNotificacion(StrEnum):
    LISTO_PARA_RETIRO = "LISTO_PARA_RETIRO"
    RESERVA_ASIGNADA = "RESERVA_ASIGNADA"
    VENCIMIENTO_PROXIMO = "VENCIMIENTO_PROXIMO"
    PRESTAMO_VENCIDO = "PRESTAMO_VENCIDO"
    MULTA_GENERADA = "MULTA_GENERADA"
    PRESTAMO_CANCELADO = "PRESTAMO_CANCELADO"


class CanalNotificacion(StrEnum):
    EMAIL_SIMULADO = "EMAIL_SIMULADO"


class TipoParametro(StrEnum):
    ENTERO = "ENTERO"


# Estados "abiertos": se usan en los índices únicos parciales y en las reglas de baja.
ESTADOS_PRESTAMO_ABIERTOS = (
    EstadoPrestamo.EN_ENVIO,
    EstadoPrestamo.LISTO_PARA_RETIRO,
    EstadoPrestamo.ACTIVO,
)
ESTADOS_REMITO_NO_FINALES = (
    EstadoRemito.GENERADO,
    EstadoRemito.EMPAQUETADO,
    EstadoRemito.EN_TRANSITO,
)
ESTADOS_RESERVA_ABIERTOS = (EstadoReserva.PENDIENTE, EstadoReserva.ASIGNADA)
