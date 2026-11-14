"""Elección de la sede origen de una solicitud por libro (RF-PRE-16)."""

import pytest

from app.models.policies.asignacion_prestamo import elegir_sede_origen


@pytest.mark.ca("CA-PRE-19")
def test_con_disponibles_en_destino_el_origen_es_el_destino():
    assert elegir_sede_origen({1: 1, 3: 5}, sede_destino_id=1) == 1


@pytest.mark.ca("CA-PRE-20")
def test_sin_disponibles_en_destino_gana_la_sede_con_mas_disponibles():
    assert elegir_sede_origen({1: 0, 2: 1, 3: 3}, sede_destino_id=1) == 3


@pytest.mark.ca("CA-PRE-21")
def test_con_empate_gana_la_sede_de_menor_id():
    assert elegir_sede_origen({3: 2, 2: 2, 5: 1}, sede_destino_id=1) == 2


@pytest.mark.ca("CA-PRE-22")
@pytest.mark.parametrize("disponibles", [{}, {1: 0, 2: 0}])
def test_sin_disponibles_en_la_red_no_hay_origen(disponibles):
    assert elegir_sede_origen(disponibles, sede_destino_id=1) is None
