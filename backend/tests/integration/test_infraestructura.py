"""Humo de la infraestructura de pruebas contra PostgreSQL."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_la_base_de_pruebas_responde(sesion: Session):
    assert sesion.execute(text("SELECT 1")).scalar() == 1
