import tomllib
from importlib import metadata
from pathlib import Path

NOMBRE_PAQUETE = "tpi-dao-backend"
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def obtener_version() -> str:
    """Devuelve la versión del backend declarada en ``pyproject.toml``.

    Si el archivo no está disponible (por ejemplo, en una imagen que solo
    contiene el paquete instalado), usa la versión de los metadatos del paquete.
    """
    try:
        with PYPROJECT.open("rb") as archivo:
            return tomllib.load(archivo)["project"]["version"]
    except (OSError, KeyError):
        try:
            return metadata.version(NOMBRE_PAQUETE)
        except metadata.PackageNotFoundError:
            return "desconocida"
