"""Ejemplar y sus estados (patrón State): transiciones válidas, inválidas e historial."""

from datetime import UTC, datetime

import pytest

from app.exceptions import (
    ConflictoDeVersion,
    EjemplarNoDisponible,
    ErrorDeValidacion,
    TransicionInvalida,
)
from app.models.ejemplar import Ejemplar, EstadoFisico, TipoMovimiento
from app.models.sede import Cambio
from app.models.states.ejemplar import EstadoEjemplarEnum as E
from app.models.states.ejemplar import estado_ejemplar
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
BIBLIO = UsuarioRef(2, "Biblio")

# operación → estado de partida → estado de llegada (todas las transiciones válidas del diagrama)
VALIDAS = [
    ("apartar", E.DISPONIBLE, E.APARTADO),
    ("reservar", E.DISPONIBLE, E.RESERVADO),
    ("prestar", E.APARTADO, E.PRESTADO),
    ("poner_en_transito", E.APARTADO, E.EN_TRANSITO),
    ("liberar", E.APARTADO, E.DISPONIBLE),
    ("prestar", E.RESERVADO, E.PRESTADO),
    ("poner_en_transito", E.RESERVADO, E.EN_TRANSITO),
    ("liberar", E.RESERVADO, E.DISPONIBLE),
    ("apartar", E.EN_TRANSITO, E.APARTADO),
    ("liberar", E.EN_TRANSITO, E.DISPONIBLE),
    ("enviar_a_revision", E.EN_TRANSITO, E.EN_REVISION),
    ("liberar", E.PRESTADO, E.DISPONIBLE),
    ("apartar", E.PRESTADO, E.APARTADO),
    ("enviar_a_revision", E.PRESTADO, E.EN_REVISION),
]
OPERACIONES = [
    "apartar",
    "reservar",
    "prestar",
    "poner_en_transito",
    "liberar",
    "enviar_a_revision",
]


def ejemplar(estado: E = E.DISPONIBLE) -> Ejemplar:
    nuevo = Ejemplar.registrar(
        codigo_inventario="cen-000123",
        libro_id=1,
        sede_id=1,
        estado_fisico=EstadoFisico.BUENO,
        observaciones=None,
        actor=BIBLIO,
        ahora=AHORA,
    )
    nuevo.id = 1
    nuevo.estado = estado_ejemplar(estado)
    nuevo.movimientos_pendientes.clear()
    return nuevo


def test_el_alta_queda_disponible_con_codigo_en_mayusculas_y_primer_movimiento():
    nuevo = Ejemplar.registrar(
        codigo_inventario=" cen-000123 ",
        libro_id=1,
        sede_id=3,
        estado_fisico=EstadoFisico.NUEVO,
        observaciones="  Donación  ",
        actor=BIBLIO,
        ahora=AHORA,
    )

    assert nuevo.codigo_inventario == "CEN-000123" and nuevo.esta_disponible
    assert (nuevo.sede_propietaria_id, nuevo.sede_actual_id) == (3, 3)
    assert nuevo.observaciones == "Donación"
    [primero] = nuevo.movimientos_pendientes
    assert (primero.estado_anterior, primero.estado_nuevo) == (None, E.DISPONIBLE)


@pytest.mark.parametrize("codigo", ["AB", "CEN 0001", "-CEN", "x" * 31])
def test_un_codigo_de_inventario_invalido_se_rechaza(codigo):
    with pytest.raises(ErrorDeValidacion):
        Ejemplar.registrar(
            codigo_inventario=codigo,
            libro_id=1,
            sede_id=1,
            estado_fisico=EstadoFisico.BUENO,
            observaciones=None,
            actor=BIBLIO,
            ahora=AHORA,
        )


@pytest.mark.ca("CA-CAT-06")
@pytest.mark.parametrize(("operacion", "desde", "hasta"), VALIDAS)
def test_cada_transicion_valida_cambia_el_estado_y_queda_en_el_historial(operacion, desde, hasta):
    e = ejemplar(desde)
    version = e.version

    getattr(e, operacion)(BIBLIO, AHORA, "motivo de prueba")

    assert e.estado_nombre == hasta and e.version == version + 1
    [mov] = e.movimientos_pendientes
    assert (mov.estado_anterior, mov.estado_nuevo, mov.usuario, mov.fecha_hora) == (
        desde,
        hasta,
        BIBLIO,
        AHORA,
    )


@pytest.mark.parametrize(
    ("operacion", "desde"),
    [
        (op, estado)
        for estado in E
        for op in OPERACIONES
        if (op, estado) not in {(o, d) for o, d, _ in VALIDAS}
    ],
)
def test_toda_transicion_que_no_esta_en_el_diagrama_se_rechaza(operacion, desde):
    e = ejemplar(desde)

    with pytest.raises(TransicionInvalida):
        getattr(e, operacion)(BIBLIO, AHORA, "motivo")
    assert e.estado_nombre == desde and e.movimientos_pendientes == []


def test_el_ejemplar_en_revision_se_repara_y_queda_regular():
    e = ejemplar(E.EN_REVISION)

    e.reparar(BIBLIO, AHORA)

    assert e.estado_nombre == E.DISPONIBLE and e.estado_fisico == EstadoFisico.REGULAR
    with pytest.raises(TransicionInvalida):
        ejemplar(E.DISPONIBLE).reparar(BIBLIO, AHORA)


def test_enviar_a_revision_lo_marca_danado():
    e = ejemplar(E.PRESTADO)

    e.enviar_a_revision(BIBLIO, AHORA, "Tapa rota")

    assert e.estado_fisico == EstadoFisico.DANADO


@pytest.mark.ca("CA-CAT-08")
@pytest.mark.parametrize("desde", [E.DISPONIBLE, E.EN_REVISION])
def test_la_baja_manual_de_un_ejemplar_disponible_o_en_revision(desde):
    e = ejemplar(desde)

    e.dar_de_baja("Hojas arrancadas", BIBLIO, AHORA)

    assert e.estado_nombre == E.BAJA
    assert (e.fecha_baja, e.motivo_baja) == (AHORA, "Hojas arrancadas")


@pytest.mark.ca("CA-CAT-07")
@pytest.mark.parametrize("desde", [E.PRESTADO, E.RESERVADO, E.APARTADO, E.EN_TRANSITO, E.BAJA])
def test_la_baja_manual_de_un_ejemplar_en_uso_se_bloquea(desde):
    e = ejemplar(desde)

    with pytest.raises(EjemplarNoDisponible):
        e.dar_de_baja("Hojas arrancadas", BIBLIO, AHORA)
    assert e.estado_nombre == desde


@pytest.mark.parametrize("desde", [E.EN_TRANSITO, E.PRESTADO])
def test_un_extravio_da_de_baja_un_ejemplar_en_uso(desde):
    e = ejemplar(desde)

    e.registrar_baja("Extraviado en el envío", None, AHORA)

    assert e.estado_nombre == E.BAJA


def test_la_baja_exige_motivo():
    with pytest.raises(ErrorDeValidacion):
        ejemplar().dar_de_baja("x", BIBLIO, AHORA)


@pytest.mark.ca("CA-CAT-13")
def test_modificar_cambia_estado_fisico_y_observaciones_y_queda_en_el_historial():
    e = ejemplar()
    version = e.version

    assert (
        e.modificar(estado_fisico=EstadoFisico.BUENO, observaciones=None, actor=BIBLIO, ahora=AHORA)
        is False
    )
    assert e.movimientos_pendientes == [] and e.version == version
    assert (
        e.modificar(
            estado_fisico=EstadoFisico.REGULAR,
            observaciones="Lomo gastado",
            actor=BIBLIO,
            ahora=AHORA,
        )
        is True
    )
    assert (e.estado_fisico, e.observaciones, e.estado_nombre) == (
        EstadoFisico.REGULAR,
        "Lomo gastado",
        E.DISPONIBLE,
    )
    [mov] = e.movimientos_pendientes
    assert (mov.tipo, mov.estado_anterior, mov.estado_nuevo, mov.usuario) == (
        TipoMovimiento.MODIFICACION,
        E.DISPONIBLE,
        E.DISPONIBLE,
        BIBLIO,
    )
    assert mov.cambios == (
        Cambio("estado_fisico", "BUENO", "REGULAR"),
        Cambio("observaciones", None, "Lomo gastado"),
    )
    assert e.version == version + 1


@pytest.mark.ca("CA-CAT-15")
def test_un_ejemplar_dado_de_baja_no_se_edita():
    e = ejemplar()
    e.dar_de_baja("Destruido por agua", BIBLIO, AHORA)
    e.movimientos_pendientes.clear()

    with pytest.raises(TransicionInvalida, match="editar"):
        e.modificar(estado_fisico=EstadoFisico.NUEVO, observaciones=None, actor=BIBLIO, ahora=AHORA)
    assert e.estado_fisico == EstadoFisico.BUENO and e.movimientos_pendientes == []


def test_un_cambio_de_estado_fisico_verificado_queda_en_el_historial():
    e = ejemplar(E.PRESTADO)

    e.registrar_estado_fisico(EstadoFisico.BUENO, BIBLIO, AHORA, "Devuelto")
    assert e.movimientos_pendientes == []
    e.registrar_estado_fisico(EstadoFisico.REGULAR, BIBLIO, AHORA, "Devuelto")
    [mov] = e.movimientos_pendientes
    assert (mov.tipo, mov.cambios) == (
        TipoMovimiento.MODIFICACION,
        (Cambio("estado_fisico", "BUENO", "REGULAR"),),
    )


def test_la_version_desactualizada_se_rechaza():
    e = ejemplar()

    e.validar_version(e.version)
    with pytest.raises(ConflictoDeVersion):
        e.validar_version(e.version - 1)


@pytest.mark.ca("CA-CAT-14")
def test_llegada_y_traslado_cambian_las_sedes_y_quedan_en_el_historial():
    e = ejemplar(E.EN_TRANSITO)

    e.recibir_en(
        2, EstadoFisico.BUENO, trasladar=False, actor=BIBLIO, ahora=AHORA, observacion="R-1"
    )
    assert (e.sede_propietaria_id, e.sede_actual_id) == (1, 2)
    [llegada] = e.movimientos_pendientes
    assert (llegada.tipo, llegada.cambios) == (
        TipoMovimiento.CAMBIO_DE_UBICACION,
        (Cambio("sede_actual", 1, 2),),
    )

    e.movimientos_pendientes.clear()
    e.recibir_en(
        3, EstadoFisico.REGULAR, trasladar=True, actor=BIBLIO, ahora=AHORA, observacion="R-2"
    )
    assert (e.sede_propietaria_id, e.sede_actual_id) == (3, 3)
    assert e.pertenece_a(3) and not e.pertenece_a(1)
    [traslado] = e.movimientos_pendientes
    assert traslado.tipo == TipoMovimiento.TRASLADO
    assert traslado.cambios == (
        Cambio("sede_actual", 2, 3),
        Cambio("sede_propietaria", 1, 3),
        Cambio("estado_fisico", "BUENO", "REGULAR"),
    )


def test_una_transicion_rechazada_no_cambia_el_estado_fisico():
    e = ejemplar(E.DISPONIBLE)

    with pytest.raises(TransicionInvalida):
        e.enviar_a_revision(BIBLIO, AHORA, "Tapa rota")
    assert e.estado_fisico == EstadoFisico.BUENO


def test_revision_y_reparacion_registran_el_estado_fisico_en_el_movimiento():
    e = ejemplar(E.PRESTADO)

    e.enviar_a_revision(BIBLIO, AHORA, "Tapa rota")
    e.reparar(BIBLIO, AHORA)

    revision, reparacion = e.movimientos_pendientes
    assert (revision.tipo, revision.cambios) == (
        TipoMovimiento.CAMBIO_DE_ESTADO,
        (Cambio("estado_fisico", "BUENO", "DANADO"),),
    )
    assert reparacion.cambios == (Cambio("estado_fisico", "DANADO", "REGULAR"),)


# --- recuperar un extraviado -------------------------------------------------------------------


@pytest.mark.ca("CA-CAT-20")
def test_un_ejemplar_dado_de_baja_se_recupera_en_su_sede():
    e = ejemplar(E.EN_TRANSITO)
    e.recibir_en(2, EstadoFisico.BUENO, trasladar=False, actor=BIBLIO, ahora=AHORA, observacion="x")
    e.registrar_baja("Faltante en el remito R-1", BIBLIO, AHORA)
    e.movimientos_pendientes.clear()

    e.recuperar(EstadoFisico.REGULAR, "Apareció en el depósito", BIBLIO, AHORA)

    assert (e.estado_nombre, e.fecha_baja, e.motivo_baja) == (E.DISPONIBLE, None, None)
    assert (e.sede_actual_id, e.estado_fisico) == (1, EstadoFisico.REGULAR)
    [mov] = e.movimientos_pendientes
    assert (mov.estado_anterior, mov.estado_nuevo) == (E.BAJA, E.DISPONIBLE)
    assert mov.observacion == "Recuperado: Apareció en el depósito"
    assert mov.cambios == (
        Cambio("sede_actual", 2, 1),
        Cambio("estado_fisico", "BUENO", "REGULAR"),
    )


def test_un_recuperado_danado_va_a_revision_y_solo_se_recupera_desde_baja():
    e = ejemplar(E.DISPONIBLE)
    with pytest.raises(TransicionInvalida, match="recuperar"):
        e.recuperar(EstadoFisico.BUENO, "Apareció", BIBLIO, AHORA)

    e.dar_de_baja("Extraviado en la sala", BIBLIO, AHORA)
    e.recuperar(EstadoFisico.DANADO, "Apareció mojado", BIBLIO, AHORA)

    assert e.estado_nombre == E.EN_REVISION
