"""Casos de uso de sedes: alta, modificación, baja, reactivación, excepciones e historial."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Any

from app.exceptions import (
    CodigoInmutable,
    ConflictoDeVersion,
    DireccionDuplicada,
    ExcepcionHorarioInvalida,
    LocalidadInvalida,
    PermisoDenegado,
    SedeCodigoDuplicado,
    SedeNoEncontrada,
    SedeNombreDuplicado,
)
from app.models.horario import MAX_DIAS_POR_RANGO, ExcepcionHorario, TipoExcepcion
from app.models.paginacion import Pagina
from app.models.policies.verificacion_baja_sede import Impedimento, VerificadorBajaSede
from app.models.sede import MENSAJE_NO_DISPONIBLE, EventoSede, Sede, validar_nombre
from app.models.usuario import Permiso, Usuario, UsuarioRef
from app.models.valores import CodigoSede, Contacto, Direccion, FranjaHoraria, Localidad
from app.repositories.interfaces.sede_repository import (
    FiltroEstado,
    FiltroHistorial,
    FiltroSedes,
    OrdenSedes,
)
from app.repositories.unit_of_work import UnitOfWork
from app.utils.reloj import Reloj
from app.utils.texto import normalizar


@dataclass(frozen=True)
class DatosSede:
    """Datos editables de una sede (el código solo se informa en el alta)."""

    nombre: str
    calle: str
    numero: str
    localidad_id: int
    telefono: str
    email: str
    responsable: str
    horarios: list[FranjaHoraria]


@dataclass(frozen=True)
class DatosExcepcion:
    """Cierre por fecha (o rango de fechas) a cargar."""

    fecha_desde: date
    fecha_hasta: date | None
    tipo: TipoExcepcion
    hora_desde: time | None = None
    hora_hasta: time | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class VistaSede:
    """Una sede con los datos calculados que se muestran junto a ella."""

    sede: Sede
    abierta_ahora: bool
    hoy: date


class SedeService:
    """Orquesta los casos de uso de sedes; las reglas viven en la entidad ``Sede``."""

    def __init__(self, uow: UnitOfWork, reloj: Reloj, verificador: VerificadorBajaSede) -> None:
        self._uow = uow
        self._reloj = reloj
        self._verificador = verificador

    # --- escritura ------------------------------------------------------------------------

    def crear(
        self,
        actor: Usuario,
        codigo: str,
        datos: DatosSede,
        confirmar_direccion_duplicada: bool = False,
    ) -> VistaSede:
        """Da de alta una sede ``Activa``.

        Orden de validación: forma (422) → código y nombre duplicados (409) → dirección
        repetida (409, se puede confirmar).

        Raises:
            PermisoDenegado: Si el usuario no administra sedes.
            ErrorDeValidacion: Formato inválido de algún campo.
            LocalidadInvalida: Localidad fuera del catálogo.
            SedeCodigoDuplicado, SedeNombreDuplicado: Unicidad.
            DireccionDuplicada: Ya hay una sede en esa dirección y no se confirmó.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        with self._transaccion():
            codigo_vo = CodigoSede.crear(codigo)
            direccion, contacto = self._armar(datos)
            self._verificar_unicidad(codigo_vo.valor, datos.nombre, None)
            confirmadas = self._verificar_direccion(direccion, None, confirmar_direccion_duplicada)
            ahora = self._reloj.ahora()
            sede = Sede.crear(
                codigo=codigo_vo,
                nombre=datos.nombre,
                direccion=direccion,
                contacto=contacto,
                horarios=datos.horarios,
                actor=_ref(actor),
                ahora=ahora,
                direccion_duplicada_confirmada=confirmadas,
            )
            self._uow.sedes.agregar(sede)
        return self._vista(sede)

    def modificar(
        self,
        actor: Usuario,
        sede_id: int,
        version: int,
        datos: DatosSede,
        codigo: str | None = None,
        confirmar_direccion_duplicada: bool = False,
    ) -> VistaSede:
        """Reemplaza los datos y el horario de una sede activa.

        Raises:
            SedeNoEncontrada: No existe.
            CodigoInmutable: Se envió un código distinto del actual.
            SedeEnBaja: La sede está dada de baja.
            ConflictoDeVersion: La versión enviada está desactualizada.
            SedeNombreDuplicado, DireccionDuplicada, ErrorDeValidacion, LocalidadInvalida.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        with self._transaccion():
            sede = self._para_modificar(sede_id)
            if codigo is not None and CodigoSede.crear(codigo) != sede.codigo:
                raise CodigoInmutable(
                    "El código de una sede no se puede cambiar.",
                    [{"campo": "codigo", "problema": "inmutable"}],
                )
            sede.validar_operativa()
            self._verificar_version(sede, version)
            direccion, contacto = self._armar(datos)
            validar_nombre(datos.nombre)
            self._verificar_unicidad(None, datos.nombre, sede.id)
            confirmadas = None
            if sede.cambio_el_domicilio(direccion):
                confirmadas = self._verificar_direccion(
                    direccion, sede.id, confirmar_direccion_duplicada
                )
            cambio = sede.modificar(
                nombre=datos.nombre,
                direccion=direccion,
                contacto=contacto,
                horarios=datos.horarios,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
                direccion_duplicada_confirmada=confirmadas,
            )
            if cambio:
                self._uow.sedes.guardar(sede)
        return self._vista(sede)

    def dar_de_baja(self, actor: Usuario, sede_id: int, version: int, motivo: str) -> VistaSede:
        """Da de baja la sede si no tiene actividad pendiente (nunca cancela nada).

        Raises:
            SedeYaEnBaja, ConflictoDeVersion, ErrorDeValidacion (motivo),
            SedeConActividadPendiente: Con el detalle por tipo de impedimento.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        with self._transaccion():
            sede = self._para_modificar(sede_id)
            if sede.esta_activa():
                self._verificar_version(sede, version)
            sede.dar_de_baja(
                motivo=motivo,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
                impedimentos=self._impedimentos(sede),
            )
            self._uow.sedes.guardar(sede)
        return self._vista(sede)

    def reactivar(self, actor: Usuario, sede_id: int, version: int) -> VistaSede:
        """Reactiva una sede en baja, sin condiciones adicionales.

        Raises:
            SedeYaActiva, ConflictoDeVersion.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        with self._transaccion():
            sede = self._para_modificar(sede_id)
            if not sede.esta_activa():
                self._verificar_version(sede, version)
            sede.reactivar(actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.sedes.guardar(sede)
        return self._vista(sede)

    def agregar_excepciones(
        self, actor: Usuario, sede_id: int, datos: DatosExcepcion
    ) -> list[ExcepcionHorario]:
        """Carga un cierre por fecha o rango (una excepción por día). Todo o nada.

        Raises:
            SedeEnBaja, ExcepcionHorarioInvalida, ExcepcionHorarioSuperpuesta.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        hasta = datos.fecha_hasta or datos.fecha_desde
        if hasta < datos.fecha_desde or (hasta - datos.fecha_desde).days + 1 > MAX_DIAS_POR_RANGO:
            raise ExcepcionHorarioInvalida(
                f"El rango debe ser de 1 a {MAX_DIAS_POR_RANGO} días.",
                [{"campo": "fecha_hasta", "problema": "rango_invalido"}],
            )
        nuevas = [
            ExcepcionHorario(
                fecha=datos.fecha_desde + timedelta(days=i),
                tipo=datos.tipo,
                desde=datos.hora_desde,
                hasta=datos.hora_hasta,
                motivo=(datos.motivo or None),
            )
            for i in range((hasta - datos.fecha_desde).days + 1)
        ]
        with self._transaccion():
            sede = self._para_modificar(sede_id)
            sede.agregar_excepciones(
                nuevas, actor=_ref(actor), ahora=self._reloj.ahora(), hoy=self._reloj.hoy()
            )
            self._uow.sedes.guardar(sede)
        fechas = {n.fecha for n in nuevas}
        return [e for e in sede.excepciones if e.fecha in fechas and e.id is not None]

    def quitar_excepcion(self, actor: Usuario, sede_id: int, excepcion_id: int) -> None:
        """Elimina una excepción de hoy o futura.

        Raises:
            SedeEnBaja, ExcepcionHorarioNoEncontrada, ExcepcionHorarioInvalida.
        """
        actor.exigir(Permiso.SEDE_ADMINISTRAR)
        with self._transaccion():
            sede = self._para_modificar(sede_id)
            sede.quitar_excepcion(
                excepcion_id, actor=_ref(actor), ahora=self._reloj.ahora(), hoy=self._reloj.hoy()
            )
            self._uow.sedes.guardar(sede)

    # --- lectura --------------------------------------------------------------------------

    def obtener(self, usuario: Usuario, sede_id: int) -> VistaSede:
        """Detalle de una sede según el rol.

        Raises:
            SedeNoEncontrada: No existe, o está en baja y el usuario es un socio.
        """
        _exigir_lectura(usuario)
        sede = self._uow.sedes.obtener(sede_id)
        if sede is None or (not sede.esta_activa() and not _ve_sedes_en_baja(usuario)):
            raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
        return self._vista(sede)

    def listar(
        self,
        usuario: Usuario,
        estado: FiltroEstado | None,
        texto: str | None,
        localidad_id: int | None,
        orden: OrdenSedes,
        page: int,
        size: int,
    ) -> Pagina[VistaSede]:
        """Listado paginado.

        El estado por defecto es ``TODAS`` para el administrador y ``ACTIVA`` para los demás;
        el socio solo ve sedes activas (el parámetro se ignora).
        """
        _exigir_lectura(usuario)
        if not _ve_sedes_en_baja(usuario):
            estado = FiltroEstado.ACTIVA
        elif estado is None:
            estado = (
                FiltroEstado.TODAS
                if usuario.puede(Permiso.SEDE_LEER_COMPLETO)
                else FiltroEstado.ACTIVA
            )
        filtro = FiltroSedes(
            estado=estado,
            texto=normalizar(texto) if texto else None,
            localidad_id=localidad_id,
            orden=orden,
        )
        sedes, total = self._uow.sedes.listar(filtro, page, size)
        return Pagina([self._vista(s) for s in sedes], total, page, size)

    def resumen(self, actor: Usuario) -> dict[str, int]:
        """Cantidad de sedes por estado (solo administrador)."""
        actor.exigir(Permiso.SEDE_LEER_COMPLETO)
        conteo = self._uow.sedes.contar_por_estado()
        activas, baja = conteo.get("ACTIVA", 0), conteo.get("BAJA", 0)
        return {"total": activas + baja, "activas": activas, "en_baja": baja}

    def excepciones(
        self, usuario: Usuario, sede_id: int, incluir_pasadas: bool = False
    ) -> list[ExcepcionHorario]:
        """Excepciones de una sede: vigentes para todos; con pasadas solo el administrador."""
        vista = self.obtener(usuario, sede_id)
        if incluir_pasadas and usuario.puede(Permiso.SEDE_LEER_COMPLETO):
            return sorted(vista.sede.excepciones, key=lambda e: (e.fecha, e.desde or time.min))
        return vista.sede.excepciones_vigentes(vista.hoy)

    def historial(
        self, actor: Usuario, sede_id: int, filtro: FiltroHistorial, page: int, size: int
    ) -> Pagina[EventoSede]:
        """Historial de eventos de la sede (solo administrador)."""
        actor.exigir(Permiso.SEDE_VER_HISTORIAL)
        if self._uow.sedes.obtener(sede_id) is None:
            raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
        eventos, total = self._uow.sedes.historial(sede_id, filtro, page, size)
        return Pagina(eventos, total, page, size)

    def localidades(self, provincia_id: int | None, texto: str | None) -> list[Localidad]:
        """Catálogo cerrado de localidades."""
        return self._uow.localidades.listar(provincia_id, normalizar(texto) if texto else None)

    def provincias(self) -> list[tuple[int, str]]:
        return self._uow.localidades.provincias()

    # --- internos -------------------------------------------------------------------------

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        """Una transacción por caso de uso: confirma si todo sale bien, deshace si no."""
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()

    def _vista(self, sede: Sede) -> VistaSede:
        return VistaSede(sede, sede.esta_abierta(self._reloj.ahora_local()), self._reloj.hoy())

    def _para_modificar(self, sede_id: int) -> Sede:
        sede = self._uow.sedes.obtener_para_modificar(sede_id)
        if sede is None:
            raise SedeNoEncontrada(MENSAJE_NO_DISPONIBLE)
        return sede

    @staticmethod
    def _verificar_version(sede: Sede, version: int) -> None:
        if sede.version != version:
            raise ConflictoDeVersion(
                "Otra persona modificó la sede. Recargue para ver los cambios.",
                [
                    {
                        "campo": "version",
                        "problema": "desactualizada",
                        "version_actual": sede.version,
                    }
                ],
            )

    def _impedimentos(self, sede: Sede) -> list[Impedimento]:
        assert sede.id is not None
        return self._verificador.verificar(sede.id)

    def _armar(self, datos: DatosSede) -> tuple[Direccion, Contacto]:
        localidad = self._uow.localidades.obtener(datos.localidad_id)
        if localidad is None:
            raise LocalidadInvalida(
                "Elija una localidad de la lista.",
                [{"campo": "localidad_id", "problema": "fuera_del_catalogo"}],
            )
        direccion = Direccion.crear(datos.calle, datos.numero, localidad)
        contacto = Contacto.crear(datos.telefono, datos.email, datos.responsable)
        return direccion, contacto

    def _verificar_unicidad(self, codigo: str | None, nombre: str, excluir_id: int | None) -> None:
        if codigo is not None:
            existente = self._uow.sedes.buscar_por_codigo(codigo)
            if existente is not None:
                raise SedeCodigoDuplicado(
                    f"Ya existe la sede {existente.nombre} con el código {codigo}.",
                    [{"campo": "codigo", "problema": "duplicado", "sede": _resumen(existente)}],
                )
        existente = self._uow.sedes.buscar_por_nombre_normalizado(normalizar(nombre), excluir_id)
        if existente is not None:
            raise SedeNombreDuplicado(
                f"Ya existe una sede con el nombre {existente.nombre}.",
                [{"campo": "nombre", "problema": "duplicado", "sede": _resumen(existente)}],
            )

    def _verificar_direccion(
        self, direccion: Direccion, excluir_id: int | None, confirmar: bool
    ) -> list[dict[str, Any]] | None:
        """Advierte si hay otra sede en la misma dirección; con ``confirmar`` la acepta.

        Returns:
            Las sedes duplicadas confirmadas (para el historial), o ``None`` si no hay.
        """
        duplicadas = self._uow.sedes.buscar_por_direccion(direccion.normalizada(), excluir_id)
        if not duplicadas:
            return None
        resumen = [_resumen(s) for s in duplicadas]
        if not confirmar:
            nombres = ", ".join(f"{s.nombre} ({s.codigo.valor})" for s in duplicadas)
            raise DireccionDuplicada(
                f"Ya existe una sede en esa dirección: {nombres}. "
                "Corrija la dirección o confirme que es intencional.",
                [{"campo": "direccion", "problema": "duplicada", "sede": r} for r in resumen],
            )
        return resumen


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)


def _resumen(sede: Sede) -> dict[str, Any]:
    return {
        "id": sede.id,
        "codigo": sede.codigo.valor,
        "nombre": sede.nombre,
        "estado": sede.estado.value,
    }


def _exigir_lectura(usuario: Usuario) -> None:
    if not usuario.puede(Permiso.SEDE_LEER_PUBLICO):
        raise PermisoDenegado("No tiene permiso para consultar sedes.")


def _ve_sedes_en_baja(usuario: Usuario) -> bool:
    return usuario.puede(Permiso.SEDE_LEER_BASICO)
