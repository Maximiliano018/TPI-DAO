"""Incidencias: quién es responsable y cómo se resuelve un extravío."""

from datetime import UTC, datetime

import pytest

from app.models.incidencia import Incidencia, OrigenIncidencia, TipoIncidencia
from app.models.usuario import UsuarioRef

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
BIBLIO = UsuarioRef(2, "Biblio")


@pytest.mark.ca("CA-REM-22")
def test_la_incidencia_de_un_remito_es_de_la_sede_origen_y_no_tiene_socio():
    i = Incidencia.de_remito(
        tipo=TipoIncidencia.DANIO,
        remito_id=7,
        sede_origen_id=1,
        ejemplar_id=100,
        prestamo_id=10,
        descripcion="Mojado",
        actor=BIBLIO,
        ahora=AHORA,
    )

    assert (i.origen, i.sede_responsable_id, i.socio_id, i.prestamo_id) == (
        OrigenIncidencia.REMITO,
        1,
        None,
        10,
    )


@pytest.mark.ca("CA-CAT-20")
def test_un_extravio_se_resuelve_sin_borrarse():
    i = Incidencia.de_remito(
        tipo=TipoIncidencia.EXTRAVIO,
        remito_id=7,
        sede_origen_id=1,
        ejemplar_id=100,
        prestamo_id=None,
        descripcion="No llegó",
        actor=BIBLIO,
        ahora=AHORA,
    )
    assert not i.resuelta

    i.resolver("Recuperado: apareció", BIBLIO, AHORA)

    assert (i.resuelta, i.resuelta_por, i.resolucion) == (True, BIBLIO, "Recuperado: apareció")
