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
from app.models.usuario import SedeRef
from tests.factories.dominio import BibliotecarioFactory
from tests.fakes.repositorios import UnitOfWorkEnMemoria

# Tipos cuyo módulo todavía no existe. Solo puede achicarse: cada módulo quita el suyo al
# registrar su verificador (y agrega sus pruebas de contrato).
TIPOS_PENDIENTES_DE_MODULO: set[TipoImpedimento] = set()


def _registrados(uow=None) -> VerificadorBajaSede:
    uow = uow or UnitOfWorkEnMemoria()
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


@pytest.mark.ca("CA-SED-16", "CA-ACC-10")
def test_bibliotecarios_asignados_cuenta_solo_los_activos_de_esa_sede_y_limita_la_muestra():
    uow = UnitOfWorkEnMemoria()
    for n in range(12):
        uow.usuarios.agregar(BibliotecarioFactory(id=None, username=f"biblio{n:02d}"))
    uow.usuarios.agregar(BibliotecarioFactory(id=None, username="inactivo", activo=False))
    uow.usuarios.agregar(
        BibliotecarioFactory(id=None, username="otra.sede", sede=SedeRef(2, "NORTE", "Sede Norte"))
    )

    impedimento = _registrados(uow).verificar(1)

    assert [i.tipo for i in impedimento] == [TipoImpedimento.BIBLIOTECARIOS_ASIGNADOS]
    unico = impedimento[0]
    assert unico.cantidad == 12 and len(unico.elementos) == 10 and unico.hay_mas
    assert all(e.estado == "ACTIVO" for e in unico.elementos)
    assert unico.elementos[0].referencia == "biblio00"
    assert _registrados(uow).verificar(3) == []
