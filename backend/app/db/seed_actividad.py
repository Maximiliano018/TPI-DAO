"""Actividad de demostración: préstamos, remitos, devoluciones, multas y reservas.

Se genera con los casos de uso reales (los mismos que usa la API) y un reloj que avanza desde
hace 45 días hasta hoy, para que los historiales, las fechas de despacho y recepción, los
vencimientos y las multas queden coherentes y los reportes tengan datos. Solo corre si todavía
no hay préstamos.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import EjemplarORM, PrestamoORM, SedeORM, SocioORM
from app.models.devolucion import EstadoRecibido
from app.models.ejemplar import EstadoFisico
from app.models.remito import MotivoRemito, RecepcionLinea
from app.models.usuario import Usuario
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.devolucion_service import DevolucionService
from app.services.prestamo_service import PrestamoService
from app.services.remito_service import LineaNueva, RemitoService
from app.services.reserva_service import ReservaService


class _RelojDeDemo:
    """Reloj que se ubica en un día del pasado (``hace(dias)``); nunca pasa de hoy."""

    def __init__(self, zona: str) -> None:
        self._zona = ZoneInfo(zona)
        self._hoy = datetime.now(self._zona).date()
        self._local = datetime.now(self._zona)

    def hace(self, dias: int, hora: int = 11) -> None:
        dia: date = self._hoy - timedelta(days=dias)
        self._local = min(datetime.combine(dia, time(hora), self._zona), datetime.now(self._zona))

    def ahora(self) -> datetime:
        return self._local.astimezone(ZoneInfo("UTC"))

    def ahora_local(self) -> datetime:
        return self._local

    def hoy(self) -> date:
        return self._local.date()


class _Demo:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion
        self.uow = SqlAlchemyUnitOfWork(sesion)
        self.reloj = _RelojDeDemo(get_settings().tz_negocio)
        self.prestamos = PrestamoService(self.uow, self.reloj)
        self.remitos = RemitoService(self.uow, self.reloj)
        self.devoluciones = DevolucionService(self.uow, self.reloj)
        self.reservas = ReservaService(self.uow, self.reloj)

    def usuario(self, username: str) -> Usuario:
        usuario = self.uow.usuarios.obtener_por_username(username)
        assert usuario is not None, username
        return usuario

    def socio(self, documento: str) -> int:
        socio_id = self.sesion.scalar(
            select(SocioORM.id).where(SocioORM.nro_documento == documento)
        )
        assert socio_id is not None, documento
        return socio_id

    def ejemplar(self, codigo: str) -> int:
        ejemplar_id = self.sesion.scalar(
            select(EjemplarORM.id).where(EjemplarORM.codigo_inventario == codigo)
        )
        assert ejemplar_id is not None, codigo
        return ejemplar_id

    def sede(self, codigo: str) -> int:
        sede_id = self.sesion.scalar(select(SedeORM.id).where(SedeORM.codigo == codigo))
        assert sede_id is not None, codigo
        return sede_id

    def libro_de(self, codigo: str) -> int:
        libro_id = self.sesion.scalar(
            select(EjemplarORM.libro_id).where(EjemplarORM.codigo_inventario == codigo)
        )
        assert libro_id is not None, codigo
        return libro_id

    # --- pasos ----------------------------------------------------------------------------

    def prestar(self, biblio: Usuario, socio: str, ejemplar: str) -> int:
        prestamo = self.prestamos.registrar(biblio, self.socio(socio), self.ejemplar(ejemplar))
        assert prestamo.id is not None
        return prestamo.id

    def enviar(self, biblio: Usuario, destino: str, motivo: MotivoRemito, lineas) -> int:
        remito = self.remitos.generar(
            biblio,
            self.sede(destino),
            motivo,
            [LineaNueva(self.ejemplar(e), p) for e, p in lineas],
        )
        assert remito.id is not None
        self.remitos.empaquetar(biblio, remito.id)
        self.remitos.despachar(biblio, remito.id)
        return remito.id

    def recibir(self, biblio: Usuario, remito_id: int, *lineas) -> None:
        self.remitos.recibir(
            biblio,
            remito_id,
            [
                RecepcionLinea(self.ejemplar(e), estado, observacion=obs)
                for e, estado, obs in lineas
            ],
        )


def cargar_actividad(sesion: Session) -> None:
    """Cuenta una historia de 45 días por la red (idempotente: si hay préstamos, no hace nada)."""
    if sesion.scalar(select(func.count(PrestamoORM.id))):
        return
    d = _Demo(sesion)
    admin = d.usuario("admin")
    cen, norte, rc = (
        d.usuario("bibliotecario.cen"),
        d.usuario("bibliotecario.norte"),
        d.usuario("bibliotecario.rc"),
    )
    carla, martin, julian, valentina, camila = (
        "30111222",
        "28555666",
        "31777888",
        "33666777",
        "36888999",
    )
    buen = EstadoFisico.BUENO

    # Martín (Norte) pide «Rayuela» de Central; Central traslada «Clean Code» a Río Cuarto.
    d.reloj.hace(45)
    p_rayuela = d.prestar(norte, martin, "CEN-705783-1")
    ida_rayuela = d.enviar(cen, "NORTE", MotivoRemito.ENVIO, [("CEN-705783-1", p_rayuela)])
    traslado = d.enviar(cen, "SUR_RC", MotivoRemito.TRASLADO, [("CEN-350884-1", None)])
    d.reloj.hace(43)
    d.recibir(norte, ida_rayuela, ("CEN-705783-1", buen, None))
    d.prestamos.entregar(norte, p_rayuela)
    d.reloj.hace(41)
    d.recibir(rc, traslado, ("CEN-350884-1", buen, None))

    # Camila (Central) pide «El túnel» de Norte.
    d.reloj.hace(40)
    p_tunel = d.prestar(cen, camila, "NORTE-912347-1")
    ida_tunel = d.enviar(norte, "CEN", MotivoRemito.ENVIO, [("NORTE-912347-1", p_tunel)])
    d.reloj.hace(37)
    d.recibir(cen, ida_tunel, ("NORTE-912347-1", buen, None))
    d.prestamos.entregar(cen, p_tunel)

    # Carla se lleva «Cien años de soledad» en Central (préstamo local).
    d.reloj.hace(35)
    p_cien = d.prestar(cen, carla, "CEN-384567-1")
    d.prestamos.entregar(cen, p_cien)

    # Julián (Río Cuarto) pide «Ficciones» de Central: llega mojado, el préstamo se cancela y
    # el ejemplar espera en Río Cuarto el remito de retorno a Central, que es quien lo revisa.
    d.reloj.hace(30)
    p_ficciones = d.prestar(rc, julian, "CEN-801233-1")
    ida_ficciones = d.enviar(cen, "SUR_RC", MotivoRemito.ENVIO, [("CEN-801233-1", p_ficciones)])
    d.reloj.hace(28)
    d.recibir(rc, ida_ficciones, ("CEN-801233-1", EstadoFisico.DANADO, "Llegó mojado"))

    # Martín devuelve «Rayuela» en término: vuelve a Central con un remito de retorno.
    d.reloj.hace(25)
    devuelto = d.devoluciones.registrar(norte, p_rayuela, EstadoRecibido.BUENO)
    assert devuelto.remito_retorno is not None and devuelto.remito_retorno.id is not None
    retorno = devuelto.remito_retorno.id
    d.remitos.empaquetar(norte, retorno)
    d.remitos.despachar(norte, retorno)
    d.reloj.hace(23)
    d.recibir(cen, retorno, ("CEN-705783-1", buen, None))

    # Julián retira «Facundo» en Río Cuarto: no lo devuelve y vence.
    d.reloj.hace(20)
    p_facundo = d.prestar(rc, julian, "SURRC-443214-1")
    d.prestamos.entregar(rc, p_facundo)
    # Valentina (Norte) vuelve a pedir «Rayuela».
    p_rayuela2 = d.prestar(norte, valentina, "CEN-705783-1")
    ida_rayuela2 = d.enviar(cen, "NORTE", MotivoRemito.ENVIO, [("CEN-705783-1", p_rayuela2)])

    # Carla devuelve dos días tarde: multa de $400 que salda al día siguiente.
    d.reloj.hace(19, hora=17)
    tarde = d.devoluciones.registrar(cen, p_cien, EstadoRecibido.REGULAR, "Tapa gastada")
    d.reloj.hace(18)
    d.recibir(norte, ida_rayuela2, ("CEN-705783-1", buen, None))
    d.prestamos.entregar(norte, p_rayuela2)
    d.reloj.hace(18, hora=12)
    assert tarde.multa is not None and tarde.multa.id is not None
    d.devoluciones.saldar_multa(cen, tarde.multa.id)

    # Norte manda «El túnel» (2) a Río Cuarto y el envío nunca llega.
    d.reloj.hace(15)
    perdido = d.enviar(norte, "SUR_RC", MotivoRemito.TRASLADO, [("NORTE-912347-2", None)])

    # Camila devuelve cuatro días tarde: multa pendiente y retorno a Norte sin despachar.
    d.reloj.hace(12)
    d.devoluciones.registrar(cen, p_tunel, EstadoRecibido.BUENO)

    # Préstamos en curso.
    d.reloj.hace(10)
    p_venas = d.prestar(norte, martin, "NORTE-728895-1")
    d.prestamos.entregar(norte, p_venas)
    d.reloj.hace(5)
    p_cien2 = d.prestar(cen, carla, "NORTE-384567-1")
    d.reloj.hace(3)
    d.enviar(norte, "CEN", MotivoRemito.ENVIO, [("NORTE-384567-1", p_cien2)])
    d.reloj.hace(2)
    p_fierro = d.prestar(cen, carla, "CEN-045676-1")
    d.prestamos.entregar(cen, p_fierro)
    # Martín reserva «Martín Fierro» (el único ejemplar está prestado) para retirarlo en Norte.
    d.reservas.reservar(norte, d.libro_de("CEN-045676-1"), d.sede("NORTE"), d.socio(martin))

    # Hoy: corre la detección de vencidos y el administrador da por perdido el envío.
    d.reloj.hace(0, hora=9)
    d.prestamos.detectar_vencidos()
    d.remitos.marcar_extraviado(admin, perdido, "Superó el plazo de tránsito sin llegar")
