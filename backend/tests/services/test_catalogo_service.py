"""Casos de uso del catálogo con repositorios en memoria."""

import pytest

from app.exceptions import (
    CategoriaInvalida,
    ConflictoDeVersion,
    EjemplarCodigoDuplicado,
    ErrorDeValidacion,
    LibroConEjemplares,
    LibroDuplicado,
    LibroNoEncontrado,
    PermisoDenegado,
    SedeEnBaja,
)
from app.models.ejemplar import EstadoFisico
from app.models.states.ejemplar import EstadoEjemplarEnum as E
from app.models.usuario import SedeRef
from app.services.catalogo_service import CatalogoService, DatosEjemplarNuevo, DatosLibroNuevo
from app.services.sede_service import SedeService
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
    return BibliotecarioFactory(id=200, sede=SedeRef(sedes["centro"].id, "CEN", "Centro"))


@pytest.fixture
def servicio(uow, reloj) -> CatalogoService:
    return CatalogoService(uow, reloj)


def _libro(**over) -> DatosLibroNuevo:
    valores = {
        "isbn": "9789500705783",
        "titulo": "Rayuela",
        "autores": ["Julio Cortázar"],
        "editorial": "Sudamericana",
        "anio_edicion": 1963,
        "categoria_id": 1,
    }
    valores.update(over)
    return DatosLibroNuevo(**valores)


@pytest.fixture
def libro(servicio):
    return servicio.crear_libro(ADMIN, _libro())


def _ejemplar(servicio, actor, libro, codigo="CEN-0001", **over):
    return servicio.crear_ejemplar(
        actor, DatosEjemplarNuevo(libro_id=libro.id, codigo_inventario=codigo, **over)
    )


# --- libros ----------------------------------------------------------------------------------


def test_el_administrador_da_de_alta_un_libro(libro):
    assert libro.id and libro.titulo == "Rayuela"
    assert libro.datos.categoria.nombre == "Literatura argentina"
    assert libro.creado_por.id == ADMIN.id


def test_solo_el_administrador_carga_libros(servicio, biblio):
    with pytest.raises(PermisoDenegado):
        servicio.crear_libro(biblio, _libro())


@pytest.mark.ca("CA-CAT-01")
def test_no_se_repite_un_isbn(servicio, libro):
    with pytest.raises(LibroDuplicado) as error:
        servicio.crear_libro(ADMIN, _libro(titulo="Otra edición"))
    assert error.value.detalles[0]["libro_id"] == libro.id


def test_sin_isbn_no_se_repite_titulo_autor_editorial_y_anio(servicio):
    servicio.crear_libro(ADMIN, _libro(isbn=None))

    with pytest.raises(LibroDuplicado):
        servicio.crear_libro(ADMIN, _libro(isbn=None, titulo="RAYUELA"))
    servicio.crear_libro(ADMIN, _libro(isbn=None, anio_edicion=1984))


def test_la_categoria_debe_existir(servicio):
    with pytest.raises(CategoriaInvalida):
        servicio.crear_libro(ADMIN, _libro(categoria_id=99))


def test_modificar_un_libro_no_puede_chocar_con_otro(servicio, libro):
    otro = servicio.crear_libro(ADMIN, _libro(isbn="9789875801233", titulo="Ficciones"))

    with pytest.raises(LibroDuplicado):
        servicio.modificar_libro(ADMIN, otro.id, _libro(titulo="Ficciones"), otro.version)
    modificado = servicio.modificar_libro(
        ADMIN, libro.id, _libro(editorial="Alfaguara"), libro.version
    )
    assert modificado.datos.editorial == "Alfaguara"


@pytest.mark.ca("CA-CAT-19")
def test_modificar_un_libro_con_version_desactualizada_se_rechaza(servicio, libro):
    version = libro.version
    servicio.modificar_libro(ADMIN, libro.id, _libro(editorial="Alfaguara"), version)

    with pytest.raises(ConflictoDeVersion):
        servicio.modificar_libro(ADMIN, libro.id, _libro(editorial="Debolsillo"), version)
    assert servicio.obtener_libro(ADMIN, libro.id).datos.editorial == "Alfaguara"


@pytest.mark.ca("CA-CAT-09")
def test_un_libro_con_ejemplares_no_se_elimina(servicio, libro, biblio):
    _ejemplar(servicio, biblio, libro)

    with pytest.raises(LibroConEjemplares):
        servicio.eliminar_libro(ADMIN, libro.id)
    sin_ejemplares = servicio.crear_libro(ADMIN, _libro(isbn="9789875801233"))
    servicio.eliminar_libro(ADMIN, sin_ejemplares.id)
    with pytest.raises(LibroNoEncontrado):
        servicio.obtener_libro(ADMIN, sin_ejemplares.id)


def test_cualquier_rol_busca_en_el_catalogo(servicio, libro):
    socio = SocioUsuarioFactory(id=300, socio_id=1)

    pagina = servicio.buscar_libros(socio, "cortazar", None, None, 1, 20)

    assert [lb.id for lb in pagina.items] == [libro.id]
    assert servicio.buscar_libros(socio, "borges", None, None, 1, 20).total == 0


# --- ejemplares ------------------------------------------------------------------------------


def test_el_bibliotecario_carga_ejemplares_en_su_sede(servicio, biblio, libro, uow):
    ejemplar = _ejemplar(servicio, biblio, libro, codigo="cen-0001")

    assert ejemplar.codigo_inventario == "CEN-0001" and ejemplar.estado_nombre == E.DISPONIBLE
    assert ejemplar.sede_propietaria_id == biblio.sede_id == ejemplar.sede_actual_id
    assert [m.estado_nuevo for m in uow.ejemplares.historial(ejemplar.id)] == [E.DISPONIBLE]


@pytest.mark.ca("CA-CAT-02", "CA-CAT-03")
def test_el_codigo_es_unico_en_la_red_y_dos_copias_conviven(servicio, biblio, libro, sedes):
    _ejemplar(servicio, biblio, libro, codigo="INV-1")
    _ejemplar(servicio, biblio, libro, codigo="INV-2")

    with pytest.raises(EjemplarCodigoDuplicado):
        _ejemplar(servicio, ADMIN, libro, codigo="inv-1", sede_id=sedes["norte"].id)


@pytest.mark.ca("CA-CAT-04")
def test_no_se_cargan_ejemplares_en_una_sede_en_baja(servicio, libro, sedes, uow, reloj):
    norte = sedes["norte"]
    SedeService(uow, reloj, verificador_con()).dar_de_baja(
        ADMIN, norte.id, norte.version, "Cierre por mudanza"
    )

    with pytest.raises(SedeEnBaja):
        _ejemplar(servicio, ADMIN, libro, sede_id=norte.id)


def test_el_administrador_indica_la_sede_y_el_bibliotecario_no_elige_otra(
    servicio, biblio, libro, sedes
):
    with pytest.raises(ErrorDeValidacion):
        _ejemplar(servicio, ADMIN, libro)
    with pytest.raises(PermisoDenegado):
        _ejemplar(servicio, biblio, libro, sede_id=sedes["norte"].id)


@pytest.mark.ca("CA-CAT-05")
def test_un_bibliotecario_no_modifica_ejemplares_de_otra_sede(servicio, libro, sedes):
    ajeno = _ejemplar(servicio, ADMIN, libro, codigo="NOR-1", sede_id=sedes["norte"].id)
    biblio_centro = BibliotecarioFactory(id=201, sede=SedeRef(sedes["centro"].id, "CEN", "C"))

    with pytest.raises(PermisoDenegado):
        servicio.modificar_ejemplar(
            biblio_centro, ajeno.id, ajeno.version, EstadoFisico.REGULAR, None
        )
    with pytest.raises(PermisoDenegado):
        servicio.dar_de_baja_ejemplar(biblio_centro, ajeno.id, ajeno.version, "Muy dañado")


def test_la_baja_queda_en_el_historial(servicio, biblio, libro):
    ejemplar = _ejemplar(servicio, biblio, libro)
    servicio.dar_de_baja_ejemplar(biblio, ejemplar.id, ejemplar.version, "Hojas arrancadas")

    detalle = servicio.detalle_ejemplar(biblio, ejemplar.id)

    assert detalle.ejemplar.estado_nombre == E.BAJA
    assert [m.estado_nuevo for m in detalle.historial] == [E.DISPONIBLE, E.BAJA]


# --- disponibilidad --------------------------------------------------------------------------


@pytest.mark.ca("CA-CAT-10")
def test_la_disponibilidad_cuenta_por_sede_y_estado(servicio, biblio, libro, uow, reloj):
    actor = biblio
    disponible = _ejemplar(servicio, actor, libro, codigo="A-1")
    prestado = _ejemplar(servicio, actor, libro, codigo="A-2")
    en_transito = _ejemplar(servicio, actor, libro, codigo="A-3")
    de_baja = _ejemplar(servicio, actor, libro, codigo="A-4")
    caminos = [(prestado, ["apartar", "prestar"]), (en_transito, ["apartar", "poner_en_transito"])]
    for ejemplar, pasos in caminos:
        for paso in pasos:
            getattr(uow.ejemplares.obtener(ejemplar.id), paso)(None, reloj.ahora(), "prueba")
    servicio.dar_de_baja_ejemplar(actor, de_baja.id, de_baja.version, "Destruido")

    d = servicio.disponibilidad(actor, libro.id)

    [sede] = d.por_sede
    assert (sede.totales, sede.disponibles, sede.prestados, sede.en_transito) == (3, 1, 1, 1)
    assert (d.totales, d.disponibles) == (3, 1)
    assert disponible.esta_disponible


@pytest.mark.ca("CA-CAT-11")
def test_los_ejemplares_de_una_sede_en_baja_no_se_ofrecen(servicio, libro, sedes, uow, reloj):
    norte = sedes["norte"]
    _ejemplar(servicio, ADMIN, libro, codigo="NOR-1", sede_id=norte.id)
    # La baja de una sede con ejemplares se bloquea; se fuerza para probar la consulta.
    uow.sedes.sedes[norte.id].estado = type(norte.estado)("BAJA")

    d = servicio.disponibilidad(ADMIN, libro.id)

    assert d.por_sede == [] and d.disponibles == 0
