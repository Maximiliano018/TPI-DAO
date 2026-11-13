"""Entidad de dominio ``Remito``: el comprobante de un envío de ejemplares entre dos sedes.

Un remito agrupa ejemplares con el mismo origen y destino (una línea por ejemplar). Su ciclo de
vida sigue el patrón State (``models/states/remito.py``) y cada transición queda en
``MovimientoRemito``, que es la trazabilidad del envío y la fuente de los reportes de tránsito.

El remito decide **su** estado; los efectos sobre ejemplares y préstamos los orquesta el servicio.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from app.exceptions import PlazoDeTransitoVigente, RemitoInvalido
from app.models.ejemplar import EstadoFisico
from app.models.states.remito import (
    ABIERTOS,
    EstadoRemito,
    EstadoRemitoEnum,
    Generado,
)
from app.models.usuario import UsuarioRef
from app.models.valores import validar_motivo

OBSERVACION_MAX = 300


class MotivoRemito(StrEnum):
    ENVIO = "ENVIO"  # ida de un préstamo interbibliotecario
    RETORNO = "RETORNO"  # vuelta del ejemplar a su sede propietaria
    TRASLADO = "TRASLADO"  # cambio definitivo de sede propietaria


class ResultadoLinea(StrEnum):
    """Cómo llegó cada ejemplar (revisión de recepción)."""

    RECIBIDO = "RECIBIDO"
    DANADO = "DANADO"
    DESTRUIDO = "DESTRUIDO"


@dataclass
class LineaRemito:
    """Un ejemplar del remito, con su préstamo (salvo en los traslados)."""

    ejemplar_id: int
    prestamo_id: int | None
    estado_fisico_salida: EstadoFisico
    estado_fisico_llegada: EstadoFisico | None = None
    resultado: ResultadoLinea | None = None
    observacion: str | None = None
    codigo_ejemplar: str | None = None
    libro_titulo: str | None = None


@dataclass(frozen=True)
class RecepcionLinea:
    """Lo que verifica la sede destino en cada línea."""

    ejemplar_id: int
    estado_fisico: EstadoFisico
    destruido: bool = False
    observacion: str | None = None

    @property
    def resultado(self) -> ResultadoLinea:
        if self.destruido:
            return ResultadoLinea.DESTRUIDO
        if self.estado_fisico == EstadoFisico.DANADO:
            return ResultadoLinea.DANADO
        return ResultadoLinea.RECIBIDO


@dataclass(frozen=True)
class MovimientoRemito:
    estado_anterior: EstadoRemitoEnum | None
    estado_nuevo: EstadoRemitoEnum
    fecha_hora: datetime
    usuario: UsuarioRef | None
    observacion: str | None = None


@dataclass
class Remito:
    id: int | None
    numero: str
    sede_origen_id: int
    sede_destino_id: int
    motivo: MotivoRemito
    lineas: list[LineaRemito]
    estado: EstadoRemito = field(default_factory=Generado)
    fecha_generacion: datetime | None = None
    fecha_despacho: datetime | None = None
    fecha_recepcion: datetime | None = None
    observaciones: str | None = None
    version: int = 1
    movimientos_pendientes: list[MovimientoRemito] = field(default_factory=list)
    sede_origen_nombre: str | None = None
    sede_destino_nombre: str | None = None

    @classmethod
    def generar(
        cls,
        *,
        numero: str,
        sede_origen_id: int,
        sede_destino_id: int,
        motivo: MotivoRemito,
        lineas: list[LineaRemito],
        observaciones: str | None,
        actor: UsuarioRef,
        ahora: datetime,
    ) -> "Remito":
        """Crea el remito ``Generado`` con su detalle (RF-REM-01 a 03).

        Raises:
            RemitoInvalido: Mismo origen y destino, sin líneas, ejemplares repetidos o líneas
                sin préstamo en un envío o retorno (o con préstamo en un traslado).
        """
        if sede_origen_id == sede_destino_id:
            raise RemitoInvalido(
                "La sede destino debe ser distinta de la sede origen.",
                [{"campo": "sede_destino_id", "problema": "igual_al_origen"}],
            )
        if not lineas:
            raise RemitoInvalido(
                "El remito debe tener al menos un ejemplar.",
                [{"campo": "lineas", "problema": "vacio"}],
            )
        ids = [linea.ejemplar_id for linea in lineas]
        if len(set(ids)) != len(ids):
            raise RemitoInvalido(
                "Un ejemplar figura dos veces en el remito.",
                [{"campo": "lineas", "problema": "ejemplar_repetido"}],
            )
        con_prestamo = motivo != MotivoRemito.TRASLADO
        if any((linea.prestamo_id is not None) != con_prestamo for linea in lineas):
            problema = "falta_prestamo" if con_prestamo else "traslado_sin_prestamo"
            raise RemitoInvalido(
                "Cada línea de un envío o retorno lleva su préstamo; un traslado no lleva."
                if con_prestamo
                else "Un remito de traslado no lleva préstamos.",
                [{"campo": "lineas", "problema": problema}],
            )
        remito = cls(
            id=None,
            numero=numero,
            sede_origen_id=sede_origen_id,
            sede_destino_id=sede_destino_id,
            motivo=motivo,
            lineas=lineas,
            fecha_generacion=ahora,
            observaciones=_observacion(observaciones),
        )
        remito.movimientos_pendientes.append(
            MovimientoRemito(None, EstadoRemitoEnum.GENERADO, ahora, actor, "Remito generado")
        )
        return remito

    # --- consultas ------------------------------------------------------------------------

    @property
    def estado_nombre(self) -> EstadoRemitoEnum:
        return self.estado.nombre

    @property
    def esta_abierto(self) -> bool:
        return self.estado_nombre in ABIERTOS

    def linea_de(self, ejemplar_id: int) -> LineaRemito:
        return next(linea for linea in self.lineas if linea.ejemplar_id == ejemplar_id)

    # --- transiciones ---------------------------------------------------------------------

    def empaquetar(self, actor: UsuarioRef, ahora: datetime) -> None:
        self._transicion(self.estado.empaquetar, actor, ahora, "Empaquetado")

    def despachar(self, actor: UsuarioRef, ahora: datetime) -> None:
        """Sale de la sede origen; los ejemplares pasan a ``En tránsito`` (lo hace el servicio)."""
        self._transicion(self.estado.despachar, actor, ahora, "Despachado")
        self.fecha_despacho = ahora

    def pasar_a_transito(self, actor: UsuarioRef | None, ahora: datetime) -> None:
        self._transicion(self.estado.pasar_a_transito, actor, ahora, "En viaje")

    def recibir(
        self, recepcion: Sequence[RecepcionLinea], actor: UsuarioRef, ahora: datetime
    ) -> None:
        """La sede destino verifica cada línea (RF-REM-09, 13).

        El estado final sigue la peor condición: alguna línea destruida → ``Destruido``; alguna
        dañada → ``Dañado``; si no, ``Recibido``. Desde ``Despachado`` primero completa el paso
        por ``En tránsito`` (CU-REM-04, A3).

        Raises:
            TransicionInvalida: El remito no está despachado ni en tránsito.
            RemitoInvalido: Faltan o sobran líneas, o una incidencia no tiene observación.
        """
        if self.estado_nombre == EstadoRemitoEnum.DESPACHADO:
            self.pasar_a_transito(actor, ahora)
        else:
            self.estado.recibir()  # valida el estado antes de tocar las líneas
        por_ejemplar = {r.ejemplar_id: r for r in recepcion}
        if set(por_ejemplar) != {linea.ejemplar_id for linea in self.lineas}:
            raise RemitoInvalido(
                "Hay que verificar cada ejemplar del remito, sin agregar otros.",
                [{"campo": "lineas", "problema": "no_coinciden"}],
            )
        for linea in self.lineas:
            r = por_ejemplar[linea.ejemplar_id]
            observacion = _observacion(r.observacion)
            if r.resultado != ResultadoLinea.RECIBIDO and not observacion:
                raise RemitoInvalido(
                    "Describa el daño o la destrucción en la observación de la línea.",
                    [
                        {
                            "campo": "observacion",
                            "problema": "obligatoria",
                            "ejemplar_id": r.ejemplar_id,
                        }
                    ],
                )
            linea.estado_fisico_llegada = r.estado_fisico
            linea.resultado = r.resultado
            linea.observacion = observacion
        resultados = {linea.resultado for linea in self.lineas}
        if ResultadoLinea.DESTRUIDO in resultados:
            operacion, texto = self.estado.recibir_destruido, "Recibido con ejemplares destruidos"
        elif ResultadoLinea.DANADO in resultados:
            operacion, texto = self.estado.recibir_con_dano, "Recibido con ejemplares dañados"
        else:
            operacion, texto = self.estado.recibir, "Recibido"
        self._transicion(operacion, actor, ahora, texto)
        self.fecha_recepcion = ahora

    def anular(self, motivo: str, actor: UsuarioRef, ahora: datetime) -> None:
        """Solo antes del despacho (RF-REM-11)."""
        texto = validar_motivo(motivo)
        self._transicion(self.estado.anular, actor, ahora, texto)

    def marcar_extraviado(
        self, plazo_dias: int, observacion: str, actor: UsuarioRef, ahora: datetime
    ) -> None:
        """Da por perdido un envío que superó el plazo máximo de tránsito (RF-REM-12).

        Raises:
            TransicionInvalida: No está despachado ni en tránsito.
            PlazoDeTransitoVigente: Todavía no pasaron ``plazo_dias`` desde el despacho.
        """
        self.estado.marcar_extraviado()  # valida el estado antes que el plazo
        texto = validar_motivo(observacion)
        assert self.fecha_despacho is not None
        if ahora - self.fecha_despacho <= timedelta(days=plazo_dias):
            raise PlazoDeTransitoVigente(
                f"El remito {self.numero} se despachó hace menos de {plazo_dias} días: "
                "todavía no se puede dar por extraviado.",
                [{"campo": "estado", "problema": "plazo_vigente", "plazo_dias": plazo_dias}],
            )
        self._transicion(self.estado.marcar_extraviado, actor, ahora, texto)

    def _transicion(
        self,
        operacion: Callable[[], EstadoRemito],
        actor: UsuarioRef | None,
        ahora: datetime,
        observacion: str,
    ) -> None:
        anterior = self.estado_nombre
        self.estado = operacion()
        self.version += 1
        self.movimientos_pendientes.append(
            MovimientoRemito(anterior, self.estado_nombre, ahora, actor, observacion)
        )


def _observacion(texto: str | None) -> str | None:
    valor = " ".join((texto or "").split()) or None
    if valor and len(valor) > OBSERVACION_MAX:
        raise RemitoInvalido(
            "Las observaciones admiten hasta 300 caracteres.",
            [{"campo": "observacion", "problema": "largo"}],
        )
    return valor
