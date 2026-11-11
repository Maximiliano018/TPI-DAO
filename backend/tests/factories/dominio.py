"""Fábricas de objetos de dominio con valores válidos por defecto."""

import factory

from app.config.security import hashear_clave
from app.models.usuario import Rol, SedeRef, Usuario

CLAVE_DE_PRUEBA = "Clave-de-prueba-1"
_HASH = hashear_clave(CLAVE_DE_PRUEBA)  # un solo hash: Argon2 es lento a propósito


class UsuarioFactory(factory.Factory):
    class Meta:
        model = Usuario

    id = factory.Sequence(lambda n: n + 1)
    username = factory.Sequence(lambda n: f"usuario{n}")
    nombre = factory.Sequence(lambda n: f"Usuario {n}")
    rol = Rol.ADMIN
    activo = True
    sede = None
    socio_id = None
    password_hash = _HASH


class BibliotecarioFactory(UsuarioFactory):
    rol = Rol.BIBLIOTECARIO
    sede = factory.LazyAttribute(lambda o: SedeRef(1, "CEN", "Sede Central"))


class SocioUsuarioFactory(UsuarioFactory):
    rol = Rol.SOCIO
    socio_id = factory.Sequence(lambda n: n + 1)
