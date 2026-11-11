"""Contrato de los verificadores de baja de sede (puerto Strategy del dominio).

Cada módulo que aporta actividad a una sede (usuarios, ejemplares, préstamos, remitos, reservas)
debe registrar su verificador en ``get_verificador_baja_sede``. Esta prueba falla si aparece un
tipo de impedimento nuevo sin verificador ni anotación explícita de que está pendiente.
"""

import inspect

import pytest

from app.controllers.dependencies import get_verificador_baja_sede
from app.models.policies.verificacion_baja_sede import (
    ETIQUETAS,
    Impedimento,
    TipoImpedimento,
    VerificadorBajaSede,
)

# Tipos cuyo módulo todavía no existe. Solo puede achicarse: cada módulo quita el suyo al
# registrar su verificador (y agrega sus pruebas de contrato).
TIPOS_PENDIENTES_DE_MODULO: set[TipoImpedimento] = {
    TipoImpedimento.PRESTAMOS_EN_CURSO,
    TipoImpedimento.REMITOS_ABIERTOS,
    TipoImpedimento.RESERVAS_PENDIENTES,
    TipoImpedimento.EJEMPLARES_EN_SEDE,
    TipoImpedimento.EJEMPLARES_PROPIOS_FUERA,
    TipoImpedimento.BIBLIOTECARIOS_ASIGNADOS,
}


def _registrados(uow=None) -> VerificadorBajaSede:
    parametros = inspect.signature(get_verificador_baja_sede).parameters
    return get_verificador_baja_sede(**{nombre: uow for nombre in parametros})


@pytest.mark.ca("CA-SED-20")
def test_cada_tipo_de_impedimento_tiene_verificador_o_esta_declarado_pendiente():
    cubiertos = _registrados().tipos_cubiertos

    sin_clasificar = set(TipoImpedimento) - cubiertos - TIPOS_PENDIENTES_DE_MODULO
    assert not sin_clasificar, (
        f"Falta un verificador (o declararlo pendiente) para: {sin_clasificar}"
    )
    registrados_y_pendientes = cubiertos & TIPOS_PENDIENTES_DE_MODULO
    assert not registrados_y_pendientes, (
        f"Ya tienen verificador; quitar de TIPOS_PENDIENTES_DE_MODULO: {registrados_y_pendientes}"
    )


def test_todo_tipo_tiene_etiqueta_en_singular_y_plural_para_el_mensaje_de_error():
    for tipo in TipoImpedimento:
        singular, plural = ETIQUETAS[tipo]
        assert singular and plural and singular != plural


def test_el_compuesto_solo_informa_los_tipos_con_impedimentos():
    class Con:
        tipo = TipoImpedimento.REMITOS_ABIERTOS

        def verificar(self, sede_id: int) -> Impedimento | None:
            return Impedimento(self.tipo, 1, [])

    class Sin:
        tipo = TipoImpedimento.PRESTAMOS_EN_CURSO

        def verificar(self, sede_id: int) -> Impedimento | None:
            return None

    compuesto = VerificadorBajaSede([Con(), Sin()])

    assert [i.tipo for i in compuesto.verificar(1)] == [TipoImpedimento.REMITOS_ABIERTOS]
    assert compuesto.tipos_cubiertos == {
        TipoImpedimento.REMITOS_ABIERTOS,
        TipoImpedimento.PRESTAMOS_EN_CURSO,
    }
    assert VerificadorBajaSede([]).verificar(1) == []
