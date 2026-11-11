"""Fixtures globales: configuración de prueba y reloj fijo."""

import os

# La configuración de prueba debe fijarse antes de importar la aplicación.
os.environ.setdefault("SECRET_KEY", "clave-de-pruebas-con-mas-de-treinta-y-dos-caracteres")
os.environ.setdefault("ENTORNO", "test")

import pytest  # noqa: E402

from tests.fakes.reloj import RelojFijo  # noqa: E402


@pytest.fixture
def reloj() -> RelojFijo:
    """Reloj fijo: martes 10/11/2026 12:00 en la zona de negocio."""
    return RelojFijo()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Marca como ``integration`` todo lo que está en ``tests/integration``."""
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)
