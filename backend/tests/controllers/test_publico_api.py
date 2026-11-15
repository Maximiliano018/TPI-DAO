"""Página de inicio pública: datos de la colección sin iniciar sesión."""

from tests.controllers.test_prestamo_api import _prestar, mundo  # noqa: F401

API = "/api/v1/publico/inicio"


def test_sin_sesion_muestra_la_red_y_los_libros_mas_pedidos(cliente, mundo):  # noqa: F811
    libro_0, libro_1 = mundo["libros"][0], mundo["libros"][1]
    # «Libro 0» se pide dos veces (en las dos sedes); «Libro 1», una.
    assert _prestar(cliente, mundo["h_a"], mundo["lucia"], mundo["ej_a"][0]).status_code == 201
    assert _prestar(cliente, mundo["h_b"], mundo["juan"], mundo["ej_b"][0]).status_code == 201
    assert _prestar(cliente, mundo["h_a"], mundo["juan"], mundo["ej_a"][1]).status_code == 201

    r = cliente.get(API, params={"limite": 3})

    assert r.status_code == 200, r.json()
    datos = r.json()
    assert (datos["sedes_activas"], datos["libros"], datos["ejemplares"]) == (3, 5, 7)
    destacados = datos["destacados"]
    assert [(d["libro_id"], d["pedidos"]) for d in destacados[:2]] == [
        (libro_0["id"], 2),
        (libro_1["id"], 1),
    ]
    # Si hay pocos pedidos, completa con los últimos libros del catálogo.
    assert len(destacados) == 3 and destacados[2]["pedidos"] == 0
    assert destacados[0]["titulo"] == "Libro 0" and destacados[0]["autores"] == ["Autor 0"]
    assert "socio" not in r.text


def test_la_portada_del_libro_se_guarda_y_se_valida(cliente, mundo):  # noqa: F811
    libro = mundo["libros"][2]
    url = "/portadas/libro-2.jpg"
    actual = cliente.get(f"/api/v1/libros/{libro['id']}", headers=mundo["h_admin"]).json()
    cuerpo = {
        "titulo": actual["titulo"],
        "autores": actual["autores"],
        "categoria_id": actual["categoria"]["id"],
        "version": actual["version"],
        "portada_url": url,
    }

    r = cliente.put(f"/api/v1/libros/{libro['id']}", json=cuerpo, headers=mundo["h_admin"])

    assert r.status_code == 200, r.json()
    assert r.json()["portada_url"] == url
    publico = cliente.get(API, params={"limite": 5}).json()["destacados"]
    assert url in [d["portada_url"] for d in publico]
    cuerpo |= {"version": r.json()["version"], "portada_url": "javascript:alert(1)"}
    invalida = cliente.put(f"/api/v1/libros/{libro['id']}", json=cuerpo, headers=mundo["h_admin"])
    assert invalida.status_code == 422
    assert invalida.json()["error"]["detalles"][0]["campo"] == "portada_url"
