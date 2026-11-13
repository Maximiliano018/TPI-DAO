"""API del catálogo contra PostgreSQL: libros, ejemplares, disponibilidad y baja de sede."""

import pytest
from sqlalchemy import select, text

from app.db.models import CategoriaORM, EjemplarORM, LocalidadORM
from tests.controllers.test_sede_api import _alta, _error

API = "/api/v1"


@pytest.fixture
def localidad_id(sesion) -> int:
    return sesion.scalar(select(LocalidadORM.id).where(LocalidadORM.nombre == "Córdoba"))


@pytest.fixture
def categoria_id(sesion) -> int:
    return sesion.scalar(
        select(CategoriaORM.id).where(CategoriaORM.nombre == "Literatura argentina")
    )


@pytest.fixture
def h_admin(crear_usuario, autenticar):
    return autenticar(crear_usuario("ADMIN", nombre="Ana Admin", username="ana.admin"))


def _sede(cliente, h_admin, localidad_id, codigo, numero):
    return _alta(
        cliente,
        h_admin,
        localidad_id,
        codigo=codigo,
        nombre=f"Sede {codigo}",
        calle=f"Calle {codigo}",
        numero=numero,
    ).json()


@pytest.fixture
def sede_a(cliente, h_admin, localidad_id):
    return _sede(cliente, h_admin, localidad_id, "SEDE_A", "1")


@pytest.fixture
def sede_b(cliente, h_admin, localidad_id):
    return _sede(cliente, h_admin, localidad_id, "SEDE_B", "2")


@pytest.fixture
def h_biblio_a(crear_usuario, autenticar, sede_a):
    return autenticar(crear_usuario("BIBLIOTECARIO", sede_id=sede_a["id"], nombre="Bea"))


@pytest.fixture
def h_socio(crear_usuario, autenticar, sesion, sede_a):
    from app.db.models import SocioORM

    socio = SocioORM(
        numero_socio="S000010",
        tipo_documento="DNI",
        nro_documento="30000010",
        nombre="So",
        apellido="Cio",
        email="so@example.com",
        sede_alta_id=sede_a["id"],
    )
    sesion.add(socio)
    sesion.flush()
    return autenticar(crear_usuario("SOCIO", socio_id=socio.id))


def _libro(cliente, headers, categoria, **over):
    datos = {
        "isbn": "978-950-07-0578-3",
        "titulo": "Rayuela",
        "autores": ["Julio Cortázar"],
        "editorial": "Sudamericana",
        "anio_edicion": 1963,
        "categoria_id": categoria,
    }
    datos.update(over)
    return cliente.post(f"{API}/libros", json=datos, headers=headers)


@pytest.fixture
def libro(cliente, h_admin, categoria_id):
    return _libro(cliente, h_admin, categoria_id).json()


def _ejemplar(cliente, headers, libro_id, codigo, **over):
    datos = {"libro_id": libro_id, "codigo_inventario": codigo, "estado_fisico": "BUENO"}
    datos.update(over)
    return cliente.post(f"{API}/ejemplares", json=datos, headers=headers)


# --- libros ----------------------------------------------------------------------------------


def test_alta_de_libro_con_categoria_y_autores(cliente, h_admin, categoria_id):
    r = _libro(cliente, h_admin, categoria_id, autores=["Julio Cortázar", "Otro Autor"])

    assert r.status_code == 201, r.json()
    libro = r.json()
    assert r.headers["location"] == f"{API}/libros/{libro['id']}"
    assert (libro["isbn"], libro["autores"], libro["categoria"]["nombre"]) == (
        "9789500705783",
        ["Julio Cortázar", "Otro Autor"],
        "Literatura argentina",
    )
    assert (libro["ejemplares"], libro["disponibles"]) == (0, 0)


@pytest.mark.ca("CA-CAT-01")
def test_un_isbn_repetido_se_rechaza(cliente, h_admin, categoria_id, libro):
    r = _libro(cliente, h_admin, categoria_id, titulo="Otra")

    error = _error(r, 409, "LIBRO_DUPLICADO")
    assert error["detalles"][0]["libro_id"] == libro["id"]


def test_los_autores_se_reutilizan_y_el_libro_se_modifica(
    cliente, h_admin, categoria_id, libro, sesion
):
    _libro(cliente, h_admin, categoria_id, isbn="9789875801233", titulo="Bestiario")
    r = cliente.put(
        f"{API}/libros/{libro['id']}",
        json={
            "isbn": "9789500705783",
            "titulo": "Rayuela (edición crítica)",
            "autores": ["JULIO CORTAZAR"],
            "categoria_id": categoria_id,
        },
        headers=h_admin,
    )

    assert r.status_code == 200, r.json()
    assert r.json()["titulo"] == "Rayuela (edición crítica)"
    assert sesion.scalar(text("SELECT count(*) FROM autor")) == 1


@pytest.mark.parametrize(
    ("over", "campo"),
    [
        ({"isbn": "9789500705780"}, "isbn"),
        ({"titulo": " "}, "titulo"),
        ({"autores": []}, "autores"),
        ({"categoria_id": 999999}, "categoria_id"),
    ],
)
def test_datos_de_libro_invalidos_responden_422(cliente, h_admin, categoria_id, over, campo):
    r = _libro(cliente, h_admin, categoria_id, **over)

    assert r.status_code == 422
    assert r.json()["error"]["detalles"][0]["campo"] == campo


def test_la_busqueda_encuentra_por_titulo_autor_e_isbn(
    cliente, h_admin, h_socio, categoria_id, libro
):
    _libro(
        cliente,
        h_admin,
        categoria_id,
        isbn="9789875801233",
        titulo="Ficciones",
        autores=["Jorge Luis Borges"],
    )

    def titulos(**params):
        r = cliente.get(f"{API}/libros", params=params, headers=h_socio)
        return [lb["titulo"] for lb in r.json()["items"]]

    assert titulos() == ["Ficciones", "Rayuela"]
    assert titulos(q="cortazar") == ["Rayuela"]
    assert titulos(q="BORGES") == ["Ficciones"]
    assert titulos(q="978-987-580") == ["Ficciones"]
    assert titulos(categoria_id=categoria_id) == ["Ficciones", "Rayuela"]


@pytest.mark.ca("CA-CAT-09")
def test_un_libro_con_ejemplares_no_se_elimina(cliente, h_admin, h_biblio_a, libro, categoria_id):
    _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001")
    vacio = _libro(cliente, h_admin, categoria_id, isbn="9789875801233", titulo="Otro").json()

    _error(
        cliente.delete(f"{API}/libros/{libro['id']}", headers=h_admin), 409, "LIBRO_CON_EJEMPLARES"
    )
    assert cliente.delete(f"{API}/libros/{vacio['id']}", headers=h_admin).status_code == 204
    _error(cliente.get(f"{API}/libros/{vacio['id']}", headers=h_admin), 404, "LIBRO_NO_ENCONTRADO")


def test_bibliotecario_y_socio_no_administran_libros(
    cliente, h_biblio_a, h_socio, categoria_id, libro
):
    for headers in (h_biblio_a, h_socio):
        _error(_libro(cliente, headers, categoria_id), 403, "FORBIDDEN")
        _error(cliente.delete(f"{API}/libros/{libro['id']}", headers=headers), 403, "FORBIDDEN")
    _error(cliente.get(f"{API}/libros"), 401, "TOKEN_INVALIDO")


# --- ejemplares ------------------------------------------------------------------------------


@pytest.mark.ca("CA-CAT-02", "CA-CAT-03")
def test_alta_de_ejemplares_con_codigo_unico_en_la_red(
    cliente, h_admin, h_biblio_a, libro, sede_a, sede_b
):
    r = _ejemplar(cliente, h_biblio_a, libro["id"], "a-0001")
    otro = _ejemplar(cliente, h_biblio_a, libro["id"], "A-0002")

    assert r.status_code == 201, r.json()
    ejemplar = r.json()
    assert (ejemplar["codigo_inventario"], ejemplar["estado"], ejemplar["libro"]) == (
        "A-0001",
        "DISPONIBLE",
        "Rayuela",
    )
    assert ejemplar["sede_propietaria_id"] == ejemplar["sede_actual_id"] == sede_a["id"]
    assert otro.status_code == 201
    _error(
        _ejemplar(cliente, h_admin, libro["id"], "A-0001", sede_id=sede_b["id"]),
        409,
        "EJEMPLAR_CODIGO_DUPLICADO",
    )


@pytest.mark.ca("CA-CAT-04")
def test_no_se_cargan_ejemplares_en_una_sede_en_baja(cliente, h_admin, libro, sede_b):
    cliente.post(
        f"{API}/sedes/{sede_b['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": sede_b["version"]},
        headers=h_admin,
    )

    _error(
        _ejemplar(cliente, h_admin, libro["id"], "B-0001", sede_id=sede_b["id"]),
        409,
        "SEDE_EN_BAJA",
    )


@pytest.mark.ca("CA-CAT-05")
def test_un_bibliotecario_no_toca_ejemplares_de_otra_sede(
    cliente, h_admin, h_biblio_a, libro, sede_b
):
    ajeno = _ejemplar(cliente, h_admin, libro["id"], "B-0001", sede_id=sede_b["id"]).json()
    ruta = f"{API}/ejemplares/{ajeno['id']}"

    _error(
        cliente.put(ruta, json={"estado_fisico": "REGULAR", "version": 1}, headers=h_biblio_a),
        403,
        "FORBIDDEN",
    )
    _error(
        cliente.post(
            f"{ruta}/baja", json={"motivo": "Muy dañado", "version": 1}, headers=h_biblio_a
        ),
        403,
        "FORBIDDEN",
    )
    _error(
        _ejemplar(cliente, h_biblio_a, libro["id"], "B-0002", sede_id=sede_b["id"]),
        403,
        "FORBIDDEN",
    )


@pytest.mark.ca("CA-CAT-06", "CA-CAT-08")
def test_modificar_y_dar_de_baja_queda_en_el_historial(cliente, h_biblio_a, libro):
    ejemplar = _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001").json()
    ruta = f"{API}/ejemplares/{ejemplar['id']}"

    r = cliente.put(
        ruta,
        json={
            "estado_fisico": "REGULAR",
            "observaciones": "Lomo gastado",
            "version": ejemplar["version"],
        },
        headers=h_biblio_a,
    )
    assert (r.status_code, r.json()["estado_fisico"]) == (200, "REGULAR")
    _error(
        cliente.post(
            f"{ruta}/baja", json={"motivo": "Hojas arrancadas", "version": 1}, headers=h_biblio_a
        ),
        409,
        "CONFLICTO_DE_VERSION",
    )
    baja = cliente.post(
        f"{ruta}/baja",
        json={"motivo": "Hojas arrancadas", "version": r.json()["version"]},
        headers=h_biblio_a,
    )
    assert baja.json()["estado"] == "BAJA"

    detalle = cliente.get(ruta, headers=h_biblio_a).json()
    assert [(m["estado_anterior"], m["estado_nuevo"]) for m in detalle["historial"]] == [
        (None, "DISPONIBLE"),
        ("DISPONIBLE", "BAJA"),
    ]
    assert detalle["historial"][1]["usuario"]["nombre"] == "Bea"
    assert detalle["historial"][1]["observacion"] == "Hojas arrancadas"


@pytest.mark.ca("CA-CAT-07")
def test_un_ejemplar_prestado_no_se_da_de_baja(cliente, h_biblio_a, libro, sesion):
    ejemplar = _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001").json()
    sesion.execute(
        text("UPDATE ejemplar SET estado = 'PRESTADO' WHERE id = :id"), {"id": ejemplar["id"]}
    )

    r = cliente.post(
        f"{API}/ejemplares/{ejemplar['id']}/baja",
        json={"motivo": "Hojas arrancadas", "version": ejemplar["version"]},
        headers=h_biblio_a,
    )

    _error(r, 409, "EJEMPLAR_NO_DISPONIBLE")


def test_reparar_solo_aplica_a_ejemplares_en_revision(cliente, h_biblio_a, libro, sesion):
    ejemplar = _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001").json()
    ruta = f"{API}/ejemplares/{ejemplar['id']}/reparado"

    _error(cliente.post(ruta, json={"version": 1}, headers=h_biblio_a), 409, "TRANSICION_INVALIDA")
    sesion.execute(
        text("UPDATE ejemplar SET estado = 'EN_REVISION' WHERE id = :id"), {"id": ejemplar["id"]}
    )
    r = cliente.post(ruta, json={"version": 1}, headers=h_biblio_a)
    assert (r.json()["estado"], r.json()["estado_fisico"]) == ("DISPONIBLE", "REGULAR")


def test_el_socio_no_ve_ejemplares_ni_su_historial(cliente, h_socio, h_biblio_a, libro):
    ejemplar = _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001").json()

    _error(cliente.get(f"{API}/ejemplares", headers=h_socio), 403, "FORBIDDEN")
    _error(cliente.get(f"{API}/ejemplares/{ejemplar['id']}", headers=h_socio), 403, "FORBIDDEN")


# --- disponibilidad y baja de sede ----------------------------------------------------------


@pytest.mark.ca("CA-CAT-10", "CA-CAT-11")
def test_disponibilidad_por_sede_activa(
    cliente, h_admin, h_biblio_a, h_socio, libro, sede_b, sesion
):
    ids = [
        _ejemplar(cliente, h_biblio_a, libro["id"], f"A-000{i}").json()["id"] for i in range(1, 4)
    ]
    sesion.execute(text("UPDATE ejemplar SET estado = 'PRESTADO' WHERE id = :id"), {"id": ids[1]})
    sesion.execute(
        text("UPDATE ejemplar SET estado = 'EN_TRANSITO' WHERE id = :id"), {"id": ids[2]}
    )
    _ejemplar(cliente, h_admin, libro["id"], "B-0001", sede_id=sede_b["id"])
    sesion.execute(
        text(
            "UPDATE sede SET estado = 'BAJA', fecha_baja = now(), motivo_baja = 'x', "
            "baja_por_id = creado_por_id WHERE id = :id"
        ),
        {"id": sede_b["id"]},
    )

    d = cliente.get(f"{API}/libros/{libro['id']}/disponibilidad", headers=h_socio).json()

    [sede] = d["por_sede"]
    assert (
        sede["sede"],
        sede["totales"],
        sede["disponibles"],
        sede["prestados"],
        sede["en_transito"],
    ) == ("Sede SEDE_A", 3, 1, 1, 1)
    assert d["total_red"] == {"totales": 3, "disponibles": 1}
    listado = cliente.get(f"{API}/libros", headers=h_socio).json()["items"][0]
    assert (listado["ejemplares"], listado["disponibles"]) == (4, 1)


@pytest.mark.ca("CA-SED-17", "CA-SED-18")
def test_los_ejemplares_bloquean_la_baja_de_la_sede(
    cliente, h_admin, libro, sede_a, sede_b, sesion
):
    ejemplar = _ejemplar(cliente, h_admin, libro["id"], "A-0001", sede_id=sede_a["id"]).json()
    sesion.execute(
        text("UPDATE ejemplar SET estado = 'PRESTADO', sede_actual_id = :b WHERE id = :id"),
        {"b": sede_b["id"], "id": ejemplar["id"]},
    )
    sesion.commit()  # una solicitud rechazada revierte su transacción, no los datos preparados

    baja_a = cliente.post(
        f"{API}/sedes/{sede_a['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": sede_a["version"]},
        headers=h_admin,
    )
    baja_b = cliente.post(
        f"{API}/sedes/{sede_b['id']}/baja",
        json={"motivo": "Cierre por mudanza", "version": sede_b["version"]},
        headers=h_admin,
    )

    tipos_a = [d["tipo"] for d in _error(baja_a, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")["detalles"]]
    tipos_b = [d["tipo"] for d in _error(baja_b, 409, "SEDE_CON_ACTIVIDAD_PENDIENTE")["detalles"]]
    assert tipos_a == ["EJEMPLARES_PROPIOS_FUERA"]
    assert tipos_b == ["EJEMPLARES_EN_SEDE"]
    assert sesion.get(EjemplarORM, ejemplar["id"]).estado == "PRESTADO"


def test_el_historial_es_de_solo_insercion(cliente, h_biblio_a, libro, sesion):
    _ejemplar(cliente, h_biblio_a, libro["id"], "A-0001")

    with pytest.raises(Exception, match="solo inserción"), sesion.begin_nested():
        sesion.execute(text("DELETE FROM movimiento_ejemplar"))
