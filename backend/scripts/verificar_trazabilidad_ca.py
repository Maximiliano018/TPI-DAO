"""Compara los criterios de aceptación (CA) de la documentación con las pruebas.

Uso:
    python scripts/verificar_trazabilidad_ca.py [--prefijos SED,ACC] [--estricto]

Busca los identificadores ``CA-XXX-nn`` de ``docs/funcional/*.md`` y los cruza con los que
aparecen en ``backend/tests`` y ``frontend/src``. Los criterios que todavía no se pueden
probar porque dependen de módulos futuros se listan en ``scripts/ca_pendientes.txt``.
Con ``--estricto`` termina con error si hay criterios sin prueba (y no pendientes).
"""

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PATRON = re.compile(r"CA-[A-Z]{3}-\d{2}")


def criterios_documentados(prefijos: set[str]) -> set[str]:
    """Identificadores definidos en las tablas de criterios de ``docs/funcional``."""
    ids: set[str] = set()
    for archivo in (RAIZ / "docs" / "funcional").glob("*.md"):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.startswith("| CA-"):
                ids.add(PATRON.match(linea[2:]).group(0))  # type: ignore[union-attr]
    return {i for i in ids if not prefijos or i.split("-")[1] in prefijos}


def criterios_probados() -> set[str]:
    """Identificadores mencionados en las pruebas del backend y del frontend."""
    ids: set[str] = set()
    carpetas = [
        (RAIZ / "backend" / "tests", "*.py"),
        (RAIZ / "frontend" / "src", "*.test.jsx"),
        (RAIZ / "frontend" / "tests", "*.js*"),
    ]
    for carpeta, patron in carpetas:
        for archivo in carpeta.rglob(patron) if carpeta.exists() else []:
            ids.update(PATRON.findall(archivo.read_text(encoding="utf-8")))
    return ids


def pendientes() -> set[str]:
    """Criterios que dependen de módulos futuros (``scripts/ca_pendientes.txt``)."""
    archivo = Path(__file__).with_name("ca_pendientes.txt")
    if not archivo.exists():
        return set()
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    return {ln.split("#")[0].strip() for ln in lineas if ln.split("#")[0].strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefijos", default="", help="Prefijos a revisar, por ejemplo SED,ACC")
    parser.add_argument("--estricto", action="store_true")
    args = parser.parse_args()
    prefijos = {p for p in args.prefijos.split(",") if p}

    documentados = criterios_documentados(prefijos)
    sin_prueba = sorted(documentados - criterios_probados() - pendientes())
    print(f"Criterios revisados: {len(documentados)}; sin prueba: {len(sin_prueba)}")
    for criterio in sin_prueba:
        print(f"  - {criterio}")
    return 1 if (sin_prueba and args.estricto) else 0


if __name__ == "__main__":
    sys.exit(main())
