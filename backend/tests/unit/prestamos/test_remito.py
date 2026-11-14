"""Ciclo de vida del remito (patrón State): sin saltos, sin retrocesos y con trazabilidad."""

from datetime import UTC, datetime, timedelta

import pytest

from app.exceptions import (
    ErrorDeValidacion,
    PlazoDeTransitoVigente,
    RemitoInvalido,
    TransicionInvalida,
)
from app.models.ejemplar import EstadoFisico
from app.models.remito import LineaRemito, MotivoRemito, RecepcionLinea, Remito
from app.models.states.remito import EstadoRemitoEnum as R
from app.models.states.remito import estado_remito
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
BIBLIO = UsuarioRef(2, "Biblio")
FINALES = [R.RECIBIDO, R.EXTRAVIADO, R.DANADO, R.DESTRUIDO, R.INCOMPLETO, R.ANULADO]


def remito(estado: R = R.GENERADO, lineas: int = 1, motivo=MotivoRemito.ENVIO) -> Remito:
    nuevo = Remito.generar(
        numero="R-2026-000001",
        sede_origen_id=1,
        sede_destino_id=2,
        motivo=motivo,
        lineas=[
            LineaRemito(
                100 + i, None if motivo == MotivoRemito.TRASLADO else 10 + i, EstadoFisico.BUENO
            )
            for i in range(lineas)
        ],
        observaciones=None,
        actor=BIBLIO,
        ahora=AHORA,
    )
    nuevo.id = 1
    nuevo.estado = estado_remito(estado)
    if estado in (R.DESPACHADO, R.EN_TRANSITO):
        nuevo.fecha_despacho = AHORA
    nuevo.movimientos_pendientes.clear()
    return nuevo


def recepcion(*resultados) -> list[RecepcionLinea]:
    return [
        RecepcionLinea(100 + i, fisico, destruido, obs)
        for i, (fisico, destruido, obs) in enumerate(resultados)
    ]


BIEN = (EstadoFisico.BUENO, False, None)
DANADO = (EstadoFisico.DANADO, False, "Tapa rota")
DESTRUIDO = (EstadoFisico.DANADO, True, "Mojado, ilegible")


# --- generación ------------------------------------------------------------------------------


@pytest.mark.ca("CA-REM-02")
def test_un_envio_de_tres_ejemplares_es_un_remito_con_tres_lineas():
    r = remito(lineas=3)

    assert len(r.lineas) == 3 and r.estado_nombre == R.GENERADO
    assert {linea.prestamo_id for linea in r.lineas} == {10, 11, 12}


@pytest.mark.parametrize(
    ("origen", "destino", "lineas", "motivo"),
    [
        (1, 1, [LineaRemito(1, 5, EstadoFisico.BUENO)], MotivoRemito.ENVIO),
        (1, 2, [], MotivoRemito.ENVIO),
        (1, 2, [LineaRemito(1, 5, EstadoFisico.BUENO)] * 2, MotivoRemito.ENVIO),
        (1, 2, [LineaRemito(1, None, EstadoFisico.BUENO)], MotivoRemito.ENVIO),
        (1, 2, [LineaRemito(1, 5, EstadoFisico.BUENO)], MotivoRemito.TRASLADO),
    ],
)
def test_un_remito_mal_armado_se_rechaza(origen, destino, lineas, motivo):
    with pytest.raises(RemitoInvalido):
        Remito.generar(
            numero="R-1",
            sede_origen_id=origen,
            sede_destino_id=destino,
            motivo=motivo,
            lineas=lineas,
            observaciones=None,
            actor=BIBLIO,
            ahora=AHORA,
        )


# --- ciclo completo y trazabilidad -----------------------------------------------------------


@pytest.mark.ca("CA-REM-07")
def test_el_ciclo_completo_deja_un_movimiento_por_transicion_en_orden():
    r = Remito.generar(
        numero="R-1",
        sede_origen_id=1,
        sede_destino_id=2,
        motivo=MotivoRemito.ENVIO,
        lineas=[LineaRemito(100, 10, EstadoFisico.BUENO)],
        observaciones=None,
        actor=BIBLIO,
        ahora=AHORA,
    )
    r.empaquetar(BIBLIO, AHORA + timedelta(hours=1))
    r.despachar(BIBLIO, AHORA + timedelta(hours=2))
    r.recibir(recepcion(BIEN), UsuarioRef(3, "Destino"), AHORA + timedelta(days=2))

    pasos = [(m.estado_anterior, m.estado_nuevo) for m in r.movimientos_pendientes]
    assert pasos == [
        (None, R.GENERADO),
        (R.GENERADO, R.EMPAQUETADO),
        (R.EMPAQUETADO, R.DESPACHADO),
        (R.DESPACHADO, R.EN_TRANSITO),  # la recepción completa el paso intermedio
        (R.EN_TRANSITO, R.RECIBIDO),
    ]
    assert r.fecha_despacho == AHORA + timedelta(hours=2)
    assert r.fecha_recepcion == AHORA + timedelta(days=2)
    assert r.movimientos_pendientes[-1].usuario == UsuarioRef(3, "Destino")


@pytest.mark.ca("CA-REM-04")
def test_no_se_despacha_sin_empaquetar():
    r = remito(R.GENERADO)

    with pytest.raises(TransicionInvalida, match="despachar un remito generado"):
        r.despachar(BIBLIO, AHORA)


@pytest.mark.ca("CA-REM-05")
@pytest.mark.parametrize("final", FINALES)
def test_un_remito_en_estado_final_no_cambia_mas(final):
    r = remito(final)

    for operacion in (
        lambda: r.empaquetar(BIBLIO, AHORA),
        lambda: r.despachar(BIBLIO, AHORA),
        lambda: r.pasar_a_transito(BIBLIO, AHORA),
        lambda: r.recibir(recepcion(BIEN), BIBLIO, AHORA),
        lambda: r.anular("Motivo válido", BIBLIO, AHORA),
        lambda: r.marcar_extraviado(7, "Motivo válido", BIBLIO, AHORA + timedelta(days=30)),
    ):
        with pytest.raises(TransicionInvalida):
            operacion()
    assert r.estado_nombre == final and r.movimientos_pendientes == []


@pytest.mark.ca("CA-REM-06")
def test_no_hay_retrocesos():
    en_transito = remito(R.EN_TRANSITO)

    with pytest.raises(TransicionInvalida):
        en_transito.empaquetar(BIBLIO, AHORA)
    with pytest.raises(TransicionInvalida):
        en_transito.despachar(BIBLIO, AHORA)


# --- recepción -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("resultados", "final"),
    [
        ((BIEN, BIEN), R.RECIBIDO),
        ((BIEN, DANADO), R.DANADO),
        ((DANADO, DESTRUIDO), R.DESTRUIDO),
    ],
)
def test_el_estado_final_sigue_a_la_peor_linea(resultados, final):
    r = remito(R.EN_TRANSITO, lineas=2)

    r.recibir(recepcion(*resultados), BIBLIO, AHORA)

    assert r.estado_nombre == final
    assert [linea.resultado.value for linea in r.lineas] == [
        "RECIBIDO" if not d and f != EstadoFisico.DANADO else ("DESTRUIDO" if d else "DANADO")
        for f, d, _ in resultados
    ]


def test_una_incidencia_exige_observacion_y_hay_que_verificar_cada_linea():
    r = remito(R.EN_TRANSITO, lineas=2)

    with pytest.raises(RemitoInvalido, match="observación"):
        r.recibir(recepcion(BIEN, (EstadoFisico.DANADO, False, None)), BIBLIO, AHORA)
    with pytest.raises(RemitoInvalido, match="cada ejemplar"):
        r.recibir(recepcion(BIEN), BIBLIO, AHORA)
    assert r.estado_nombre == R.EN_TRANSITO


def test_no_se_recibe_un_remito_que_no_salio():
    with pytest.raises(TransicionInvalida):
        remito(R.EMPAQUETADO).recibir(recepcion(BIEN), BIBLIO, AHORA)


# --- anulación y extravío --------------------------------------------------------------------


@pytest.mark.ca("CA-REM-15")
@pytest.mark.parametrize("desde", [R.GENERADO, R.EMPAQUETADO])
def test_se_anula_antes_del_despacho_con_motivo(desde):
    r = remito(desde)

    with pytest.raises(ErrorDeValidacion):
        r.anular("x", BIBLIO, AHORA)
    r.anular("El socio desistió", BIBLIO, AHORA)

    assert r.estado_nombre == R.ANULADO
    assert r.movimientos_pendientes[-1].observacion == "El socio desistió"


@pytest.mark.ca("CA-REM-14")
@pytest.mark.parametrize("desde", [R.DESPACHADO, R.EN_TRANSITO])
def test_un_remito_despachado_no_se_anula(desde):
    with pytest.raises(TransicionInvalida):
        remito(desde).anular("El socio desistió", BIBLIO, AHORA)


@pytest.mark.ca("CA-REM-16", "CA-REM-17")
@pytest.mark.parametrize("desde", [R.DESPACHADO, R.EN_TRANSITO])
def test_extraviado_solo_despues_del_plazo_de_transito(desde):
    r = remito(desde)

    with pytest.raises(PlazoDeTransitoVigente):
        r.marcar_extraviado(7, "No llegó a destino", BIBLIO, AHORA + timedelta(days=3))
    r.marcar_extraviado(7, "No llegó a destino", BIBLIO, AHORA + timedelta(days=8))

    assert r.estado_nombre == R.EXTRAVIADO


def test_no_se_extravia_un_remito_que_no_salio():
    with pytest.raises(TransicionInvalida):
        remito(R.EMPAQUETADO).marcar_extraviado(7, "No llegó", BIBLIO, AHORA + timedelta(days=30))


# --- faltantes y plazo de despacho -------------------------------------------------------------


FALTA = RecepcionLinea(101, None, faltante=True, observacion="No venía en la caja")


@pytest.mark.ca("CA-REM-23")
def test_un_faltante_cierra_el_remito_como_incompleto_aunque_haya_destruidos():
    r = remito(R.EN_TRANSITO, lineas=3)

    r.recibir(
        [
            RecepcionLinea(100, EstadoFisico.BUENO),
            FALTA,
            RecepcionLinea(102, EstadoFisico.DANADO, destruido=True, observacion="Ilegible"),
        ],
        BIBLIO,
        AHORA,
    )

    assert r.estado_nombre == R.INCOMPLETO
    faltante = r.linea_de(101)
    assert (faltante.resultado.value, faltante.estado_fisico_llegada) == ("FALTANTE", None)
    assert r.movimientos_pendientes[-1].observacion == "Recibido con ejemplares faltantes"


@pytest.mark.ca("CA-REM-24")
def test_si_faltan_todos_o_uno_que_llego_no_tiene_estado_se_rechaza_sin_cambios():
    r = remito(R.EN_TRANSITO, lineas=1)
    with pytest.raises(RemitoInvalido, match="ningún ejemplar"):
        r.recibir(
            [RecepcionLinea(100, None, faltante=True, observacion="Caja vacía")], BIBLIO, AHORA
        )
    with pytest.raises(RemitoInvalido, match="estado físico"):
        r.recibir([RecepcionLinea(100, None)], BIBLIO, AHORA)
    assert r.estado_nombre == R.EN_TRANSITO
    sin_obs = remito(R.EN_TRANSITO, lineas=2)
    with pytest.raises(RemitoInvalido, match="observación"):
        sin_obs.recibir(
            [RecepcionLinea(100, EstadoFisico.BUENO), RecepcionLinea(101, None, faltante=True)],
            BIBLIO,
            AHORA,
        )


@pytest.mark.ca("CA-REM-25")
def test_el_plazo_de_despacho_cuenta_desde_la_generacion_y_termina_al_despachar():
    zona = UTC
    generado = remito(R.GENERADO)
    assert generado.limite_de_despacho(3, zona) == (AHORA + timedelta(days=3)).date()
    assert remito(R.EMPAQUETADO).limite_de_despacho(3, zona) is not None
    for estado in (R.DESPACHADO, R.EN_TRANSITO, R.RECIBIDO, R.ANULADO):
        assert remito(estado).limite_de_despacho(3, zona) is None
