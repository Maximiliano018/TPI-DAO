from datetime import UTC, datetime, time

import pytest

from biblioteca.domain.entities.sede import HorarioSede, Sede
from biblioteca.domain.errors import (
    DatoInvalido,
    SedeConActividadAbierta,
    SedeDadaDeBaja,
    TransicionInvalida,
)

AHORA = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)


def _sede() -> Sede:
    return Sede("cen", "Sede Central", "Av. Colón 100", "Córdoba")


def test_normaliza_el_codigo_a_mayusculas() -> None:
    assert _sede().codigo == "CEN"


@pytest.mark.parametrize("codigo", ["C", "CENTRAL", "C3N", ""])
def test_rechaza_codigos_invalidos(codigo: str) -> None:
    with pytest.raises(DatoInvalido, match="código"):
        Sede(codigo, "Sede", "Calle 1", "Córdoba")


def test_rechaza_email_sin_arroba() -> None:
    with pytest.raises(DatoInvalido, match="email"):
        Sede("CEN", "Sede", "Calle 1", "Córdoba", email="central.biblioteca")


class TestHorarios:
    def test_admite_horario_cortado(self) -> None:
        sede = _sede()
        sede.definir_horarios(
            [HorarioSede(1, time(16), time(20)), HorarioSede(1, time(8), time(12))]
        )
        assert [(h.hora_apertura, h.hora_cierre) for h in sede.horarios] == [
            (time(8), time(12)),
            (time(16), time(20)),
        ]

    def test_rechaza_franjas_superpuestas_el_mismo_dia(self) -> None:
        with pytest.raises(DatoInvalido, match="lunes se superponen"):
            _sede().definir_horarios(
                [HorarioSede(1, time(8), time(13)), HorarioSede(1, time(12), time(20))]
            )

    def test_franjas_iguales_en_dias_distintos_no_se_superponen(self) -> None:
        sede = _sede()
        sede.definir_horarios(
            [HorarioSede(1, time(8), time(12)), HorarioSede(2, time(8), time(12))]
        )
        assert len(sede.horarios) == 2

    def test_rechaza_apertura_posterior_al_cierre(self) -> None:
        with pytest.raises(DatoInvalido, match="anterior al cierre"):
            HorarioSede(1, time(20), time(8))

    def test_rechaza_dia_inexistente(self) -> None:
        with pytest.raises(DatoInvalido, match="día de la semana"):
            HorarioSede(8, time(8), time(12))


class TestBaja:
    def test_dar_de_baja_registra_la_fecha(self) -> None:
        sede = _sede()
        sede.dar_de_baja(AHORA, tiene_actividad_abierta=False)
        assert not sede.activa
        assert sede.fecha_baja == AHORA

    def test_no_se_da_de_baja_con_actividad_abierta(self) -> None:
        sede = _sede()
        with pytest.raises(SedeConActividadAbierta):
            sede.dar_de_baja(AHORA, tiene_actividad_abierta=True)
        assert sede.activa

    def test_no_se_da_de_baja_dos_veces(self) -> None:
        sede = _sede()
        sede.dar_de_baja(AHORA, tiene_actividad_abierta=False)
        with pytest.raises(TransicionInvalida):
            sede.dar_de_baja(AHORA, tiene_actividad_abierta=False)

    def test_una_sede_de_baja_bloquea_operaciones_nuevas(self) -> None:
        sede = _sede()
        sede.dar_de_baja(AHORA, tiene_actividad_abierta=False)
        with pytest.raises(SedeDadaDeBaja):
            sede.verificar_activa()

    def test_reactivar_limpia_la_baja(self) -> None:
        sede = _sede()
        sede.dar_de_baja(AHORA, tiene_actividad_abierta=False)
        sede.reactivar()
        assert sede.activa
        assert sede.fecha_baja is None

    def test_no_se_reactiva_una_sede_activa(self) -> None:
        with pytest.raises(TransicionInvalida):
            _sede().reactivar()
