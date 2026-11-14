"""Casos de uso de socios con repositorios en memoria."""

from datetime import date

import pytest

from app.exceptions import (
    DuplicadoError,
    ErrorDeValidacion,
    PermisoDenegado,
    PosibleDuplicado,
    SedeEnBaja,
    SocioConActividadPendiente,
    SocioConCuenta,
    SocioEnBaja,
    SocioNoEncontrado,
)
from app.models.socio import EstadoSocio, MotivoInhabilitacion, SituacionSocio, TipoDocumento
from app.models.usuario import Rol, SedeRef
from app.services.sede_service import SedeService
from app.services.socio_service import DatosSocio, SocioService
from tests.factories.dominio import BibliotecarioFactory, SocioUsuarioFactory, UsuarioFactory
from tests.factories.sede import datos_sede
from tests.fakes.repositorios import UnitOfWorkEnMemoria
from tests.fakes.verificadores import verificador_con

ADMIN = UsuarioFactory(id=100, nombre="Admin")


@pytest.fixture
def uow() -> UnitOfWorkEnMemoria:
    return UnitOfWorkEnMemoria()


@pytest.fixture
def sedes(uow, reloj):
    servicio = SedeService(uow, reloj, verificador_con())
    return {
        "centro": servicio.crear(ADMIN, "CEN", datos_sede(nombre="Centro")).sede,
        "norte": servicio.crear(ADMIN, "NORTE", datos_sede(nombre="Norte")).sede,
    }


@pytest.fixture
def biblio(sedes):
    sede = sedes["centro"]
    return BibliotecarioFactory(id=200, sede=SedeRef(sede.id, "CEN", "Centro"))


@pytest.fixture
def servicio(uow, reloj) -> SocioService:
    return SocioService(uow, reloj, hashear=lambda clave: f"hash:{clave}")


def _datos(**over) -> DatosSocio:
    valores = {
        "tipo_documento": TipoDocumento.DNI,
        "nro_documento": "30.111.222",
        "nombre": "Lucía",
        "apellido": "Gómez",
        "fecha_nacimiento": date(1995, 4, 12),
        "email": "lucia@example.com",
    }
    valores.update(over)
    return DatosSocio(**valores)


# --- alta ------------------------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-01")
def test_el_bibliotecario_registra_un_socio_habilitado_en_su_sede(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())

    assert socio.id and socio.numero_socio == "00001"
    assert socio.estado == EstadoSocio.HABILITADO
    assert socio.sede_alta_id == biblio.sede_id and socio.sede_alta_nombre == "Centro"
    assert socio.datos.documento.numero == "30111222"
    assert socio.creado_por.id == biblio.id
    confirmaciones = uow.confirmaciones
    segundo = servicio.crear(biblio, _datos(nro_documento="30111223", nombre="Juan"))
    assert segundo.numero_socio == "00002"
    assert uow.confirmaciones == confirmaciones + 1


def test_el_administrador_indica_la_sede_de_alta(servicio, sedes):
    with pytest.raises(ErrorDeValidacion) as error:
        servicio.crear(ADMIN, _datos())
    assert error.value.detalles[0]["campo"] == "sede_alta_id"

    socio = servicio.crear(ADMIN, _datos(), sede_alta_id=sedes["norte"].id)
    assert socio.sede_alta_id == sedes["norte"].id


def test_el_bibliotecario_no_registra_socios_en_otra_sede(servicio, biblio, sedes):
    with pytest.raises(ErrorDeValidacion):
        servicio.crear(biblio, _datos(), sede_alta_id=sedes["norte"].id)


@pytest.mark.ca("CA-SED-24")
def test_no_se_da_de_alta_un_socio_en_una_sede_en_baja(servicio, sedes, uow, reloj):
    norte = sedes["norte"]
    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, norte.id, norte.version, "Cierre por mudanza"
    )

    with pytest.raises(SedeEnBaja):
        servicio.crear(ADMIN, _datos(), sede_alta_id=sedes["norte"].id)
    assert uow.socios.socios == {}


@pytest.mark.ca("CA-SOC-02")
def test_no_se_registran_dos_socios_con_el_mismo_documento(servicio, biblio):
    existente = servicio.crear(biblio, _datos())

    with pytest.raises(DuplicadoError) as error:
        servicio.crear(biblio, _datos(nro_documento="30111222", nombre="Otra", apellido="Persona"))
    detalle = error.value.detalles[0]
    assert error.value.codigo == "DUPLICADO"
    assert (detalle["socio_id"], detalle["puede_reactivarse"]) == (existente.id, False)


@pytest.mark.ca("CA-SOC-03")
def test_si_el_socio_existe_dado_de_baja_se_ofrece_reactivarlo(servicio, biblio):
    existente = servicio.crear(biblio, _datos())
    servicio.dar_de_baja(ADMIN, existente.id, "Se mudó de ciudad")

    with pytest.raises(DuplicadoError) as error:
        servicio.crear(biblio, _datos())
    assert error.value.detalles[0]["puede_reactivarse"] is True
    assert "puede reactivarse" in error.value.mensaje

    assert servicio.reactivar(ADMIN, existente.id).estado == EstadoSocio.HABILITADO


def test_un_posible_duplicado_por_nombre_y_nacimiento_se_confirma(servicio, biblio):
    existente = servicio.crear(biblio, _datos())

    with pytest.raises(PosibleDuplicado) as error:
        servicio.crear(biblio, _datos(nro_documento="40111222", nombre="LUCIA", apellido="gomez"))
    assert error.value.detalles[0]["socio_id"] == existente.id

    otro = servicio.crear(
        biblio, _datos(nro_documento="40111222"), confirmar_posible_duplicado=True
    )
    assert otro.id != existente.id


def test_sin_fecha_de_nacimiento_no_hay_posible_duplicado(servicio, biblio):
    servicio.crear(biblio, _datos(fecha_nacimiento=None))
    servicio.crear(biblio, _datos(nro_documento="40111222", fecha_nacimiento=None))


def test_la_busqueda_previa_encuentra_por_documento_y_por_persona(servicio, biblio):
    a = servicio.crear(biblio, _datos())
    b = servicio.crear(
        biblio,
        _datos(nro_documento="40111222", nombre="Juan", apellido="Paz"),
    )

    por_documento = servicio.posibles_duplicados(
        biblio, TipoDocumento.DNI, "30111222", None, None, None
    )
    por_persona = servicio.posibles_duplicados(biblio, None, None, "juan", "PAZ", date(1995, 4, 12))
    ambos = servicio.posibles_duplicados(
        biblio, TipoDocumento.DNI, "30111222", "Juan", "Paz", date(1995, 4, 12)
    )

    assert [s.id for s in por_documento] == [a.id]
    assert [s.id for s in por_persona] == [b.id]
    assert {s.id for s in ambos} == {a.id, b.id}
    assert servicio.posibles_duplicados(biblio, TipoDocumento.DNI, "1", None, None, None) == []


def test_un_socio_no_registra_socios(servicio):
    socio = SocioUsuarioFactory(id=300, socio_id=1)

    with pytest.raises(PermisoDenegado):
        servicio.crear(socio, _datos())


# --- modificación ----------------------------------------------------------------------------


def test_modificar_rechaza_el_documento_de_otro_socio(servicio, biblio):
    servicio.crear(biblio, _datos())
    otro = servicio.crear(biblio, _datos(nro_documento="40111222", nombre="Juan"))

    with pytest.raises(DuplicadoError):
        servicio.modificar(biblio, otro.id, _datos(nombre="Juan"))
    modificado = servicio.modificar(biblio, otro.id, _datos(nro_documento="40111222", nombre="Jua"))
    assert modificado.datos.nombre == "Jua"


def test_modificar_un_socio_en_baja_se_rechaza_antes_que_el_documento_repetido(servicio, biblio):
    servicio.crear(biblio, _datos())
    otro = servicio.crear(biblio, _datos(nro_documento="40111222", nombre="Juan"))
    servicio.dar_de_baja(ADMIN, otro.id, "Se mudó de ciudad")

    # El documento es de Lucía, pero el motivo del rechazo es que Juan está dado de baja.
    with pytest.raises(SocioEnBaja):
        servicio.modificar(biblio, otro.id, _datos(nombre="Juan"))


def test_modificar_un_socio_inexistente_es_404(servicio, biblio):
    with pytest.raises(SocioNoEncontrado):
        servicio.modificar(biblio, 999, _datos())


# --- estados ---------------------------------------------------------------------------------


def test_solo_el_administrador_inhabilita(servicio, biblio):
    socio = servicio.crear(biblio, _datos())

    with pytest.raises(PermisoDenegado):
        servicio.inhabilitar(biblio, socio.id, "Daño reiterado")
    inhabilitado = servicio.inhabilitar(ADMIN, socio.id, "Daño reiterado")
    assert inhabilitado.motivo_inhabilitacion == MotivoInhabilitacion.ADMINISTRATIVA


@pytest.mark.ca("CA-SOC-10")
def test_el_bibliotecario_no_rehabilita_una_inhabilitacion_administrativa(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())
    servicio.inhabilitar(ADMIN, socio.id, "Daño reiterado")

    with pytest.raises(PermisoDenegado):
        servicio.rehabilitar(biblio, socio.id)
    assert uow.reversiones >= 1
    assert servicio.rehabilitar(ADMIN, socio.id).estado == EstadoSocio.HABILITADO


def test_rehabilitar_usa_la_situacion_real_del_socio(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())
    servicio.inhabilitar(ADMIN, socio.id, "Daño reiterado")
    uow.socios.situaciones[socio.id] = SituacionSocio(prestamos_vencidos=1)

    rehabilitado = servicio.rehabilitar(ADMIN, socio.id)

    assert rehabilitado.estado == EstadoSocio.INHABILITADO
    assert rehabilitado.motivo_inhabilitacion == MotivoInhabilitacion.PRESTAMO_VENCIDO


@pytest.mark.ca("CA-SOC-09")
def test_la_baja_se_bloquea_si_tiene_prestamos_activos(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())
    uow.socios.situaciones[socio.id] = SituacionSocio(prestamos_activos=1)

    with pytest.raises(SocioConActividadPendiente):
        servicio.dar_de_baja(ADMIN, socio.id, "Se mudó de ciudad")
    assert uow.socios.obtener(socio.id).estado == EstadoSocio.HABILITADO


def test_baja_y_reactivacion_son_del_administrador(servicio, biblio):
    socio = servicio.crear(biblio, _datos())

    with pytest.raises(PermisoDenegado):
        servicio.dar_de_baja(biblio, socio.id, "Se mudó de ciudad")
    baja = servicio.dar_de_baja(ADMIN, socio.id, "Se mudó de ciudad")
    assert baja.socio.estado == EstadoSocio.BAJA and baja.reservas_canceladas == 0
    with pytest.raises(PermisoDenegado):
        servicio.reactivar(biblio, socio.id)


# --- cuenta de acceso ------------------------------------------------------------------------


def test_crear_la_cuenta_del_socio(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())

    con_cuenta = servicio.crear_cuenta(biblio, socio.id, "Lucia.Gomez", "Clave-segura-123")

    usuario = uow.usuarios.obtener_por_username("lucia.gomez")
    assert usuario.rol == Rol.SOCIO and usuario.socio_id == socio.id
    assert usuario.nombre == "Lucía Gómez" and usuario.password_hash == "hash:Clave-segura-123"
    assert con_cuenta.cuenta.username == "lucia.gomez"
    with pytest.raises(SocioConCuenta):
        servicio.crear_cuenta(biblio, socio.id, "otra.cuenta", "Clave-segura-123")


def test_la_cuenta_valida_clave_usuario_repetido_y_socio_en_baja(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())
    otro = servicio.crear(biblio, _datos(nro_documento="40111222", nombre="Juan"))
    servicio.crear_cuenta(biblio, socio.id, "lucia.gomez", "Clave-segura-123")

    with pytest.raises(ErrorDeValidacion):
        servicio.crear_cuenta(biblio, otro.id, "juan.gomez", "corta")
    with pytest.raises(DuplicadoError):
        servicio.crear_cuenta(biblio, otro.id, "lucia.gomez", "Clave-segura-123")
    servicio.dar_de_baja(ADMIN, otro.id, "Se mudó de ciudad")
    with pytest.raises(SocioEnBaja):
        servicio.crear_cuenta(biblio, otro.id, "juan.gomez", "Clave-segura-123")


# --- lectura ---------------------------------------------------------------------------------


@pytest.mark.ca("CA-SOC-11")
def test_un_socio_ve_su_ficha_pero_no_la_de_otro(servicio, biblio):
    propio = servicio.crear(biblio, _datos())
    ajeno = servicio.crear(biblio, _datos(nro_documento="40111222", nombre="Juan"))
    usuario_socio = SocioUsuarioFactory(id=300, socio_id=propio.id)

    assert servicio.ficha(usuario_socio, propio.id).socio.id == propio.id
    with pytest.raises(SocioNoEncontrado):
        servicio.ficha(usuario_socio, ajeno.id)
    with pytest.raises(PermisoDenegado):
        servicio.listar(usuario_socio, None, None, None, 1, 20)


def test_la_ficha_incluye_la_situacion(servicio, biblio, uow):
    socio = servicio.crear(biblio, _datos())
    uow.socios.situaciones[socio.id] = SituacionSocio(prestamos_activos=2, reservas_activas=1)

    ficha = servicio.ficha(biblio, socio.id)

    assert (ficha.situacion.prestamos_activos, ficha.situacion.reservas_activas) == (2, 1)
    with pytest.raises(SocioNoEncontrado):
        servicio.ficha(biblio, 999)


def test_la_busqueda_filtra_por_texto_documento_y_estado(servicio, biblio):
    servicio.crear(biblio, _datos())
    juan = servicio.crear(
        biblio, _datos(nro_documento="40111222", nombre="Juan", apellido="Álvarez")
    )
    servicio.dar_de_baja(ADMIN, juan.id, "Se mudó de ciudad")

    def nombres(**filtros):
        valores = {"texto": None, "documento": None, "estado": None, **filtros}
        pagina = servicio.listar(biblio, page=1, size=20, **valores)
        return [s.datos.apellido for s in pagina.items]

    assert nombres() == ["Álvarez", "Gómez"]
    assert nombres(texto="alvarez") == ["Álvarez"]
    assert nombres(texto="00001") == ["Gómez"]
    assert nombres(documento="40.111.222") == ["Álvarez"]
    assert nombres(estado=EstadoSocio.BAJA) == ["Álvarez"]
