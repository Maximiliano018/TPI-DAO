"""Herramientas del seed de demostración: un reloj que viaja al pasado y los casos de uso reales.

Todo lo que carga el seed pasa por los mismos servicios que usa la API, con un reloj que se ubica
en un día del pasado. Así cada dato nace con su historial, su auditoría (quién y cuándo) y sus
reglas de negocio aplicadas, igual que si lo hubiera cargado una persona desde el portal.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.controllers.dependencies import get_verificador_baja_sede
from app.db.models import EjemplarORM, LibroORM, SedeORM, SocioORM
from app.models.remito import RecepcionLinea
from app.models.usuario import Usuario
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.services.catalogo_service import CatalogoService
from app.services.devolucion_service import DevolucionService
from app.services.pago_service import PagoService
from app.services.parametro_service import ParametroService
from app.services.prestamo_service import PrestamoService
from app.services.remito_service import LineaNueva, RemitoService
from app.services.reserva_service import ReservaService
from app.services.sede_service import SedeService
from app.services.socio_service import SocioService
from app.services.usuario_service import UsuarioService


class RelojDeDemo:
    """Reloj que se ubica en un día del pasado (``hace(dias, hora)``); nunca pasa de ahora."""

    def __init__(self, zona: str) -> None:
        self._zona = ZoneInfo(zona)
        self._hoy = datetime.now(self._zona).date()
        self._local = datetime.now(self._zona)

    def hace(self, dias: int, hora: int = 11, minuto: int = 0) -> None:
        dia: date = self._hoy - timedelta(days=dias)
        momento = datetime.combine(dia, time(hora, minuto), self._zona)
        self._local = min(momento, datetime.now(self._zona))

    def ahora(self) -> datetime:
        return self._local.astimezone(ZoneInfo("UTC"))

    def ahora_local(self) -> datetime:
        return self._local

    def hoy(self) -> date:
        return self._local.date()


class Demo:
    """Los servicios de la aplicación sobre una sesión, con el reloj de demostración."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion
        self.uow = SqlAlchemyUnitOfWork(sesion)
        self.reloj = RelojDeDemo(get_settings().tz_negocio)
        uow, reloj = self.uow, self.reloj
        self.sedes = SedeService(uow, reloj, get_verificador_baja_sede(uow))
        self.usuarios = UsuarioService(uow, reloj)
        self.socios = SocioService(uow, reloj)
        self.catalogo = CatalogoService(uow, reloj)
        self.parametros = ParametroService(uow, reloj)
        self.prestamos = PrestamoService(uow, reloj)
        self.remitos = RemitoService(uow, reloj)
        self.reservas = ReservaService(uow, reloj)
        self.devoluciones = DevolucionService(uow, reloj)
        self.pagos = PagoService(uow, reloj)

    # --- búsquedas ------------------------------------------------------------------------

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

    def version_ejemplar(self, codigo: str) -> int:
        version = self.sesion.scalar(
            select(EjemplarORM.version).where(EjemplarORM.codigo_inventario == codigo)
        )
        assert version is not None, codigo
        return version

    def sede(self, codigo: str) -> int:
        sede_id = self.sesion.scalar(select(SedeORM.id).where(SedeORM.codigo == codigo))
        assert sede_id is not None, codigo
        return sede_id

    def libro(self, isbn: str) -> int:
        libro_id = self.sesion.scalar(select(LibroORM.id).where(LibroORM.isbn == isbn))
        assert libro_id is not None, isbn
        return libro_id

    def libro_de(self, codigo: str) -> int:
        libro_id = self.sesion.scalar(
            select(EjemplarORM.libro_id).where(EjemplarORM.codigo_inventario == codigo)
        )
        assert libro_id is not None, codigo
        return libro_id

    # --- pasos frecuentes -----------------------------------------------------------------

    def prestar(
        self, biblio: Usuario, socio: str, ejemplar: str, destino: str | None = None
    ) -> int:
        prestamo = self.prestamos.registrar(
            biblio,
            self.socio(socio),
            self.ejemplar(ejemplar),
            sede_destino_id=self.sede(destino) if destino else None,
        )
        assert prestamo.id is not None
        return prestamo.id

    def generar(self, biblio: Usuario, destino: str, motivo, lineas, obs: str | None = None) -> int:
        remito = self.remitos.generar(
            biblio,
            self.sede(destino),
            motivo,
            [LineaNueva(self.ejemplar(e), p) for e, p in lineas],
            obs,
        )
        assert remito.id is not None
        return remito.id

    def enviar(self, biblio: Usuario, destino: str, motivo, lineas, obs: str | None = None) -> int:
        """Genera, empaqueta y despacha un remito."""
        remito_id = self.generar(biblio, destino, motivo, lineas, obs)
        self.remitos.empaquetar(biblio, remito_id)
        self.remitos.despachar(biblio, remito_id)
        return remito_id

    def recibir(self, biblio: Usuario, remito_id: int, *lineas: RecepcionLinea) -> None:
        self.remitos.recibir(biblio, remito_id, list(lineas))

    def linea(self, codigo: str, estado, obs: str | None = None, **extra) -> RecepcionLinea:
        return RecepcionLinea(self.ejemplar(codigo), estado, observacion=obs, **extra)
