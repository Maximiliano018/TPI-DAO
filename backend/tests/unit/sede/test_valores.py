"""Objetos de valor de la sede: formato, normalización e inmutabilidad."""

from datetime import time

import pytest

from app.exceptions import ErrorDeValidacion, HorarioInvalido
from app.models.valores import CodigoSede, Contacto, Direccion, Email, FranjaHoraria, Telefono
from tests.factories.sede import CORDOBA, RIO_CUARTO


@pytest.mark.ca("CA-SED-40")
@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("cen", "CEN"), (" norte_2 ", "NORTE_2"), ("A1B", "A1B"), ("a" * 15, "A" * 15)],
)
def test_el_codigo_se_guarda_en_mayusculas(entrada, esperado):
    assert CodigoSede.crear(entrada).valor == esperado


@pytest.mark.ca("CA-SED-40")
@pytest.mark.parametrize("entrada", ["", "ab", "a" * 16, "CEN-1", "CEN 1", "CÉN", "CEN.2"])
def test_un_codigo_con_largo_o_caracteres_invalidos_se_rechaza(entrada):
    with pytest.raises(ErrorDeValidacion) as error:
        CodigoSede.crear(entrada)

    assert error.value.detalles[0]["campo"] == "codigo"


@pytest.mark.ca("CA-SED-39")
@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("+543514221234", "+543514221234"),
        ("+54 351 422-1234", "+543514221234"),
        ("+54 (351) 422 1234", "+543514221234"),
    ],
)
def test_el_telefono_se_normaliza_a_e164(entrada, esperado):
    assert Telefono.crear(entrada).valor == esperado


@pytest.mark.ca("CA-SED-39")
@pytest.mark.parametrize(
    "entrada", ["", "3514221234", "+0543514221234", "+54351", "+5435142212345678"]
)
def test_un_telefono_fuera_de_e164_se_rechaza(entrada):
    with pytest.raises(ErrorDeValidacion) as error:
        Telefono.crear(entrada)

    assert error.value.detalles[0]["campo"] == "telefono"


@pytest.mark.ca("CA-SED-39")
def test_el_correo_se_valida_y_pasa_a_minusculas():
    assert Email.crear(" Central@Red.Example ").valor == "central@red.example"
    for invalido in ["", "sin-arroba", "a@", "@b.com", "a b@c.com"]:
        with pytest.raises(ErrorDeValidacion) as error:
            Email.crear(invalido)
        assert error.value.detalles[0]["campo"] == "email"


@pytest.mark.parametrize("numero", ["1250", "1250b", "S/N", "s/n", "7"])
def test_numeros_de_puerta_validos(numero):
    assert Direccion.crear("Av. Colón", numero, CORDOBA).numero == numero.upper()


@pytest.mark.parametrize("numero", ["", "abc", "12345678", "12 50", "-5"])
def test_numeros_de_puerta_invalidos(numero):
    with pytest.raises(ErrorDeValidacion) as error:
        Direccion.crear("Av. Colón", numero, CORDOBA)

    assert error.value.detalles[0]["campo"] == "numero"


def test_la_calle_debe_tener_entre_2_y_100_caracteres():
    for invalida in ["", "A", "x" * 101]:
        with pytest.raises(ErrorDeValidacion):
            Direccion.crear(invalida, "10", CORDOBA)


@pytest.mark.ca("CA-SED-03")
def test_direcciones_equivalentes_tienen_la_misma_forma_normalizada():
    a = Direccion.crear("Av. Colón", "0250", CORDOBA)
    b = Direccion.crear("AVENIDA  colon", "250", CORDOBA)

    assert a.normalizada() == b.normalizada()


def test_la_direccion_normalizada_distingue_localidad_calle_y_numero():
    base = Direccion.crear("Colón", "250", CORDOBA).normalizada()

    assert Direccion.crear("Colón", "250", RIO_CUARTO).normalizada() != base
    assert Direccion.crear("Colón", "251", CORDOBA).normalizada() != base
    assert Direccion.crear("Sobremonte", "250", CORDOBA).normalizada() != base
    assert Direccion.crear("Gral. Paz", "1", CORDOBA).normalizada() == (
        Direccion.crear("General Paz", "1", CORDOBA).normalizada()
    )


def test_el_responsable_debe_tener_entre_3_y_100_caracteres():
    Contacto.crear("+543514221234", "a@b.com", "Ana")
    for invalido in ["", "Al", "x" * 101]:
        with pytest.raises(ErrorDeValidacion) as error:
            Contacto.crear("+543514221234", "a@b.com", invalido)
        assert error.value.detalles[0]["campo"] == "responsable"


@pytest.mark.ca("CA-SED-28")
@pytest.mark.parametrize("apertura, cierre", [(time(13), time(9)), (time(9), time(9))])
def test_una_franja_con_cierre_no_posterior_a_la_apertura_se_rechaza(apertura, cierre):
    with pytest.raises(HorarioInvalido) as error:
        FranjaHoraria(1, apertura, cierre)

    assert error.value.detalles[0]["dia"] == 1


@pytest.mark.parametrize("dia", [0, 8, -1])
def test_el_dia_de_la_semana_debe_estar_entre_1_y_7(dia):
    with pytest.raises(HorarioInvalido):
        FranjaHoraria(dia, time(9), time(10))


def test_las_franjas_se_solapan_solo_el_mismo_dia_y_si_se_cruzan():
    base = FranjaHoraria(1, time(9), time(13))

    assert base.se_solapa_con(FranjaHoraria(1, time(12), time(16)))
    assert base.se_solapa_con(FranjaHoraria(1, time(10), time(11)))
    assert not base.se_solapa_con(FranjaHoraria(1, time(13), time(18)))  # contigua
    assert not base.se_solapa_con(FranjaHoraria(2, time(9), time(13)))  # otro día
