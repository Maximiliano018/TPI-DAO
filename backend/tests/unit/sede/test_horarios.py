"""Horario semanal y excepciones de horario."""

from datetime import date, time

import pytest

from app.exceptions import ExcepcionHorarioInvalida, HorarioInvalido
from app.models.horario import ExcepcionHorario, TipoExcepcion, validar_horarios
from app.models.valores import FranjaHoraria

F = FranjaHoraria


@pytest.mark.ca("CA-SED-26")
def test_el_horario_debe_tener_al_menos_una_franja():
    with pytest.raises(HorarioInvalido) as error:
        validar_horarios([])

    assert error.value.detalles[0]["problema"] == "sin_franjas"


@pytest.mark.ca("CA-SED-04")
def test_franjas_solapadas_el_mismo_dia_se_rechazan_indicando_el_dia():
    with pytest.raises(HorarioInvalido) as error:
        validar_horarios([F(3, time(9), time(13)), F(3, time(12), time(16))])

    assert error.value.detalles[0] == {"campo": "horarios", "problema": "solapadas", "dia": 3}


@pytest.mark.ca("CA-SED-27")
def test_un_dia_sin_franjas_es_un_dia_cerrado_y_las_contiguas_son_validas():
    horario = validar_horarios(
        [F(2, time(15), time(19)), F(2, time(9), time(15)), F(1, time(9), time(13))]
    )

    assert [(f.dia, f.apertura) for f in horario] == [(1, time(9)), (2, time(9)), (2, time(15))]
    assert not any(f.dia == 7 for f in horario)


def test_un_dia_admite_hasta_cuatro_franjas():
    cuatro = [F(1, time(h), time(h + 1)) for h in (8, 10, 12, 14)]
    validar_horarios(cuatro)

    with pytest.raises(HorarioInvalido) as error:
        validar_horarios([*cuatro, F(1, time(16), time(17))])

    assert error.value.detalles[0]["problema"] == "demasiadas_franjas"


def _total(fecha=date(2026, 12, 25), **kw):
    return ExcepcionHorario(fecha=fecha, tipo=TipoExcepcion.CIERRE_TOTAL, **kw)


def _parcial(desde, hasta, fecha=date(2026, 12, 25)):
    return ExcepcionHorario(
        fecha=fecha, tipo=TipoExcepcion.CIERRE_PARCIAL, desde=desde, hasta=hasta
    )


def test_un_cierre_total_no_lleva_horas_y_uno_parcial_las_exige_en_orden():
    with pytest.raises(ExcepcionHorarioInvalida):
        _total(desde=time(9))
    with pytest.raises(ExcepcionHorarioInvalida):
        ExcepcionHorario(fecha=date(2026, 12, 25), tipo=TipoExcepcion.CIERRE_PARCIAL)
    with pytest.raises(ExcepcionHorarioInvalida):
        _parcial(time(18), time(9))
    with pytest.raises(ExcepcionHorarioInvalida):
        _parcial(time(9), time(9))


def test_el_motivo_admite_hasta_150_caracteres():
    _total(motivo="x" * 150)
    with pytest.raises(ExcepcionHorarioInvalida):
        _total(motivo="x" * 151)


@pytest.mark.ca("CA-SED-31")
def test_solapamiento_de_excepciones_de_la_misma_fecha():
    assert _total().se_solapa_con(_parcial(time(9), time(10)))
    assert _total().se_solapa_con(_total())
    assert _parcial(time(9), time(12)).se_solapa_con(_parcial(time(11), time(14)))
    assert not _parcial(time(9), time(12)).se_solapa_con(_parcial(time(12), time(14)))
    assert not _total().se_solapa_con(_total(fecha=date(2026, 12, 26)))


def test_un_cierre_parcial_cierra_en_el_intervalo_semiabierto():
    parcial = _parcial(time(14), time(18))

    assert parcial.cierra_en(time(14, 0))
    assert parcial.cierra_en(time(17, 59))
    assert not parcial.cierra_en(time(18, 0))
    assert not parcial.cierra_en(time(13, 59))
    assert _total().cierra_en(time(3, 0))
