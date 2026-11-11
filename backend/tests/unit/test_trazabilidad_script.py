"""Prueba mínima del script de trazabilidad (infraestructura de pruebas)."""

import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "scripts" / "verificar_trazabilidad_ca.py"


def _cargar():
    spec = importlib.util.spec_from_file_location("trazabilidad", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_script_encuentra_los_criterios_documentados_de_sedes():
    modulo = _cargar()

    criterios = modulo.criterios_documentados({"SED"})

    assert "CA-SED-01" in criterios
    assert "CA-SED-47" in criterios
