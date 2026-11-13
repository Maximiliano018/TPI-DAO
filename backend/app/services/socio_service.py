"""Casos de uso de socios: alta, búsqueda, modificación, inhabilitación, baja y cuenta."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.config.security import hashear_clave
from app.exceptions import (
    DuplicadoError,
    ErrorDeValidacion,
    PosibleDuplicado,
    SocioConCuenta,
    SocioEnBaja,
    SocioNoEncontrado,
)
from app.models.paginacion import Pagina
from app.models.socio import (
    CuentaSocio,
    DatosPersonales,
    Documento,
    EstadoSocio,
    SituacionSocio,
    Socio,
    TipoDocumento,
)
from app.models.usuario import Permiso, Rol, Usuario, UsuarioRef, validar_clave
from app.repositories.interfaces.socio_repository import FiltroSocios
from app.repositories.unit_of_work import UnitOfWork
from app.services.reserva_service import ReservaService
from app.utils.reloj import Reloj
from app.utils.texto import normalizar, quitar_tildes

MENSAJE_NO_ENCONTRADO = "El socio solicitado no existe."


@dataclass(frozen=True)
class DatosSocio:
    """Datos personales de un socio tal como llegan de la API (sin validar)."""

    tipo_documento: TipoDocumento
    nro_documento: str
    nombre: str
    apellido: str
    fecha_nacimiento: date | None = None
    email: str | None = None
    telefono: str | None = None
    domicilio: str | None = None


@dataclass(frozen=True)
class FichaSocio:
    """Socio con su situación en la red (RF-SOC-10)."""

    socio: Socio
    situacion: SituacionSocio


class SocioService:
    """Casos de uso de socios; las reglas de estado viven en ``Socio``."""

    def __init__(
        self,
        uow: UnitOfWork,
        reloj: Reloj,
        hashear: Callable[[str], str] = hashear_clave,
    ) -> None:
        self._uow = uow
        self._reloj = reloj
        self._hashear = hashear

    # --- alta y modificación --------------------------------------------------------------

    def crear(
        self,
        actor: Usuario,
        datos: DatosSocio,
        sede_alta_id: int | None = None,
        confirmar_posible_duplicado: bool = False,
    ) -> Socio:
        """Registra un socio ``HABILITADO`` con un número de socio nuevo (RF-SOC-01, 02).

        La sede de alta es la del bibliotecario; el administrador la indica. Orden de
        validación: forma (422) → documento repetido (409) → posible duplicado por nombre y
        fecha de nacimiento (409, salvo que se confirme) → sede (404/409).

        Raises:
            PermisoDenegado: Si el usuario no registra socios.
            ErrorDeValidacion: Datos inválidos o sede de alta mal indicada.
            DuplicadoError: Ya existe un socio con ese documento (indica si puede reactivarse).
            PosibleDuplicado: Hay socios con el mismo nombre y fecha de nacimiento.
            SedeNoEncontrada, SedeEnBaja: La sede de alta no existe o está dada de baja.
        """
        actor.exigir(Permiso.SOCIO_REGISTRAR)
        personales = self._validar(datos)
        sede_id = self._sede_de_alta(actor, sede_alta_id)
        with self._transaccion():
            self._rechazar_documento_repetido(personales.documento)
            if not confirmar_posible_duplicado:
                self._rechazar_posible_duplicado(personales)
            sede = self._uow.sedes.obtener_para_operar(sede_id)
            assert sede.id is not None
            socio = Socio.registrar(
                numero_socio=self._uow.socios.siguiente_numero(),
                datos=personales,
                sede_alta_id=sede.id,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            socio.sede_alta_nombre = sede.nombre
            self._uow.socios.agregar(socio)
        return socio

    def modificar(self, actor: Usuario, socio_id: int, datos: DatosSocio) -> Socio:
        """Reemplaza los datos personales (RF-SOC-03). El socio no edita los suyos.

        Raises:
            SocioNoEncontrado, ErrorDeValidacion, SocioEnBaja.
            DuplicadoError: El documento nuevo ya pertenece a otro socio.
        """
        actor.exigir(Permiso.SOCIO_REGISTRAR)
        personales = self._validar(datos)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            if personales.documento != socio.datos.documento:
                self._rechazar_documento_repetido(personales.documento, excluir_id=socio_id)
            if socio.modificar(personales, actor=_ref(actor), ahora=self._reloj.ahora()):
                self._uow.socios.guardar(socio)
        return socio

    # --- estados --------------------------------------------------------------------------

    def inhabilitar(self, actor: Usuario, socio_id: int, motivo: str) -> Socio:
        """Inhabilitación administrativa con motivo (solo el administrador, RF-SOC-06)."""
        actor.exigir(Permiso.SOCIO_ADMINISTRAR)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            socio.inhabilitar(motivo, actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.socios.guardar(socio)
        return socio

    def rehabilitar(self, actor: Usuario, socio_id: int) -> Socio:
        """Rehabilita si no quedan causas vigentes; solo el administrador levanta la causa
        administrativa (RF-SOC-05, 06)."""
        actor.exigir(Permiso.SOCIO_REGISTRAR)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            socio.rehabilitar(
                self._uow.socios.situacion(socio_id),
                actor=_ref(actor),
                es_administrador=actor.puede(Permiso.SOCIO_ADMINISTRAR),
                ahora=self._reloj.ahora(),
            )
            self._uow.socios.guardar(socio)
        return socio

    def dar_de_baja(self, actor: Usuario, socio_id: int, motivo: str) -> Socio:
        """Baja lógica, solo sin préstamos en curso ni multas pendientes (RF-SOC-09)."""
        actor.exigir(Permiso.SOCIO_ADMINISTRAR)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            socio.dar_de_baja(
                self._uow.socios.situacion(socio_id),
                motivo,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            self._uow.socios.guardar(socio)
            # Sus reservas activas se cancelan y los ejemplares pasan a la siguiente.
            ReservaService(self._uow, self._reloj).cancelar_del_socio(socio_id, _ref(actor))
        return socio

    def reactivar(self, actor: Usuario, socio_id: int) -> Socio:
        """Reactiva a un socio dado de baja (en lugar de registrarlo de nuevo)."""
        actor.exigir(Permiso.SOCIO_ADMINISTRAR)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            socio.reactivar(actor=_ref(actor), ahora=self._reloj.ahora())
            self._uow.socios.guardar(socio)
        return socio

    # --- cuenta de acceso -----------------------------------------------------------------

    def crear_cuenta(self, actor: Usuario, socio_id: int, username: str, password: str) -> Socio:
        """Crea la cuenta con la que el socio entra al sistema (rol ``SOCIO``).

        Raises:
            SocioNoEncontrado, SocioEnBaja.
            SocioConCuenta: El socio ya tiene una cuenta.
            ErrorDeValidacion: Usuario o contraseña inválidos.
            DuplicadoError: El nombre de usuario ya existe.
        """
        actor.exigir(Permiso.SOCIO_REGISTRAR)
        clave = validar_clave(password)
        password_hash = self._hashear(clave)
        with self._transaccion():
            socio = self._para_modificar(socio_id)
            if socio.estado == EstadoSocio.BAJA:
                raise SocioEnBaja(f"El socio {socio.numero_socio} está dado de baja.")
            if socio.cuenta is not None:
                raise SocioConCuenta(
                    f"El socio {socio.numero_socio} ya tiene la cuenta {socio.cuenta.username}."
                )
            cuenta = Usuario.crear_cuenta_socio(
                username=username,
                nombre=socio.datos.nombre_completo,
                socio_id=socio_id,
                password_hash=password_hash,
                actor=_ref(actor),
                ahora=self._reloj.ahora(),
            )
            if self._uow.usuarios.obtener_por_username(cuenta.username) is not None:
                raise DuplicadoError(
                    f"Ya existe el usuario {cuenta.username}.",
                    [{"campo": "username", "problema": "duplicado"}],
                )
            self._uow.usuarios.agregar(cuenta)
            assert cuenta.id is not None
            socio.cuenta = CuentaSocio(cuenta.id, cuenta.username, cuenta.activo)
        return socio

    # --- lectura --------------------------------------------------------------------------

    def ficha(self, actor: Usuario, socio_id: int) -> FichaSocio:
        """Datos y situación del socio. Un socio solo ve la propia (CA-SOC-11).

        Raises:
            SocioNoEncontrado: No existe o no es visible para el usuario.
        """
        if not actor.puede(Permiso.SOCIO_LEER) and not (
            actor.puede(Permiso.SOCIO_VER_PROPIO) and actor.socio_id == socio_id
        ):
            raise SocioNoEncontrado(MENSAJE_NO_ENCONTRADO)
        socio = self._uow.socios.obtener(socio_id)
        if socio is None:
            raise SocioNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return FichaSocio(socio, self._uow.socios.situacion(socio_id))

    def listar(
        self,
        actor: Usuario,
        texto: str | None,
        documento: str | None,
        estado: EstadoSocio | None,
        page: int,
        size: int,
    ) -> Pagina[Socio]:
        """Búsqueda por número de socio, documento o nombre y apellido (RF-SOC-04)."""
        actor.exigir(Permiso.SOCIO_LEER)
        filtro = FiltroSocios(
            texto=normalizar(texto) if texto and texto.strip() else None,
            documento=_limpiar_documento(documento) if documento else None,
            estado=estado,
        )
        socios, total = self._uow.socios.listar(filtro, page, size)
        return Pagina(socios, total, page, size)

    def posibles_duplicados(
        self,
        actor: Usuario,
        tipo_documento: TipoDocumento | None,
        nro_documento: str | None,
        nombre: str | None,
        apellido: str | None,
        fecha_nacimiento: date | None,
    ) -> list[Socio]:
        """Búsqueda previa al alta: por documento y por nombre más fecha de nacimiento."""
        actor.exigir(Permiso.SOCIO_REGISTRAR)
        encontrados: dict[int, Socio] = {}
        if tipo_documento and nro_documento:
            try:
                documento = Documento.crear(tipo_documento, nro_documento)
            except ErrorDeValidacion:
                documento = None
            if documento and (socio := self._uow.socios.buscar_por_documento(documento)):
                assert socio.id is not None
                encontrados[socio.id] = socio
        if nombre and apellido and fecha_nacimiento:
            for socio in self._uow.socios.buscar_por_persona(
                _clave(nombre), _clave(apellido), fecha_nacimiento
            ):
                assert socio.id is not None
                encontrados.setdefault(socio.id, socio)
        return list(encontrados.values())

    # --- internos -------------------------------------------------------------------------

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        try:
            yield
        except BaseException:
            self._uow.rollback()
            raise
        else:
            self._uow.commit()

    def _validar(self, datos: DatosSocio) -> DatosPersonales:
        return DatosPersonales.crear(
            documento=Documento.crear(datos.tipo_documento, datos.nro_documento),
            nombre=datos.nombre,
            apellido=datos.apellido,
            fecha_nacimiento=datos.fecha_nacimiento,
            email=datos.email,
            telefono=datos.telefono,
            domicilio=datos.domicilio,
            hoy=self._reloj.hoy(),
        )

    @staticmethod
    def _sede_de_alta(actor: Usuario, sede_alta_id: int | None) -> int:
        if actor.rol == Rol.BIBLIOTECARIO:
            assert actor.sede_id is not None
            if sede_alta_id is not None and sede_alta_id != actor.sede_id:
                raise ErrorDeValidacion(
                    "El bibliotecario registra socios en su propia sede.",
                    [{"campo": "sede_alta_id", "problema": "no_es_su_sede"}],
                )
            return actor.sede_id
        if sede_alta_id is None:
            raise ErrorDeValidacion(
                "Indique la sede de alta del socio.",
                [{"campo": "sede_alta_id", "problema": "obligatorio"}],
            )
        return sede_alta_id

    def _rechazar_documento_repetido(
        self, documento: Documento, excluir_id: int | None = None
    ) -> None:
        existente = self._uow.socios.buscar_por_documento(documento, excluir_id=excluir_id)
        if existente is None:
            return
        de_baja = existente.estado == EstadoSocio.BAJA
        mensaje = f"Ya existe el socio {existente.numero_socio} con el documento {documento}."
        if de_baja:
            mensaje += " Está dado de baja: puede reactivarse."
        raise DuplicadoError(
            mensaje,
            [{"campo": "nro_documento", "problema": "duplicado", **_resumen(existente)}],
        )

    def _rechazar_posible_duplicado(self, datos: DatosPersonales) -> None:
        if datos.fecha_nacimiento is None:
            return
        parecidos = self._uow.socios.buscar_por_persona(
            _clave(datos.nombre), _clave(datos.apellido), datos.fecha_nacimiento
        )
        if parecidos:
            raise PosibleDuplicado(
                "Hay socios con el mismo nombre y fecha de nacimiento. Confirme que es otra "
                "persona para registrarlo.",
                [
                    {"campo": "nombre", "problema": "posible_duplicado", **_resumen(socio)}
                    for socio in parecidos
                ],
            )

    def _para_modificar(self, socio_id: int) -> Socio:
        socio = self._uow.socios.obtener_para_modificar(socio_id)
        if socio is None:
            raise SocioNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return socio


def _resumen(socio: Socio) -> dict[str, Any]:
    return {
        "socio_id": socio.id,
        "numero_socio": socio.numero_socio,
        "nombre": socio.datos.nombre_completo,
        "estado": socio.estado.value,
        "puede_reactivarse": socio.estado == EstadoSocio.BAJA,
    }


def _clave(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples (igual que la consulta SQL)."""
    return " ".join(quitar_tildes(texto).lower().split())


def _limpiar_documento(texto: str) -> str:
    return texto.replace(".", "").replace("-", "").replace(" ", "").upper()


def _ref(usuario: Usuario) -> UsuarioRef:
    assert usuario.id is not None
    return UsuarioRef(usuario.id, usuario.nombre)
