import pytest

from biblioteca.application.security.actor import UsuarioActual
from biblioteca.application.security.autorizacion import exigir_rol, exigir_sede
from biblioteca.domain.entities.usuario import Usuario, validar_contrasena
from biblioteca.domain.enums import Rol
from biblioteca.domain.errors import AccesoDenegado, DatoInvalido, TransicionInvalida


class TestUsuario:
    def test_normaliza_el_username(self) -> None:
        usuario = Usuario(" Admin ", "Ana Pérez", "hash", Rol.ADMIN, None)
        assert usuario.username == "admin"

    def test_el_admin_no_tiene_sede(self) -> None:
        with pytest.raises(DatoInvalido, match="no tiene sede"):
            Usuario("admin", "Ana Pérez", "hash", Rol.ADMIN, sede_id=1)

    @pytest.mark.parametrize("rol", [Rol.BIBLIOTECARIO, Rol.LOGISTICA])
    def test_los_demas_roles_requieren_sede(self, rol: Rol) -> None:
        with pytest.raises(DatoInvalido, match="sede asignada"):
            Usuario("empleado", "Ana Pérez", "hash", rol, sede_id=None)

    def test_rechaza_username_con_caracteres_invalidos(self) -> None:
        with pytest.raises(DatoInvalido):
            Usuario("ana pérez", "Ana Pérez", "hash", Rol.ADMIN, None)

    def test_desactivar_dos_veces_es_un_error(self) -> None:
        usuario = Usuario("admin", "Ana Pérez", "hash", Rol.ADMIN, None)
        usuario.desactivar()
        with pytest.raises(TransicionInvalida):
            usuario.desactivar()

    def test_contrasena_minima(self) -> None:
        with pytest.raises(DatoInvalido, match="8 caracteres"):
            validar_contrasena("corta")
        validar_contrasena("suficiente")


def _actor(rol: Rol, sede_id: int | None) -> UsuarioActual:
    return UsuarioActual(id=1, username="u", nombre_completo="U", rol=rol, sede_id=sede_id)


class TestAutorizacion:
    def test_exigir_rol(self) -> None:
        exigir_rol(_actor(Rol.ADMIN, None), Rol.ADMIN, Rol.BIBLIOTECARIO)
        with pytest.raises(AccesoDenegado, match="ADMIN"):
            exigir_rol(_actor(Rol.LOGISTICA, 1), Rol.ADMIN)

    def test_el_admin_opera_en_cualquier_sede(self) -> None:
        exigir_sede(_actor(Rol.ADMIN, None), 7)

    def test_el_personal_opera_solo_en_su_sede(self) -> None:
        bibliotecario = _actor(Rol.BIBLIOTECARIO, 1)
        exigir_sede(bibliotecario, 1)
        exigir_sede(bibliotecario, 2, 1)  # una de las sedes del recurso es la suya
        with pytest.raises(AccesoDenegado):
            exigir_sede(bibliotecario, 2)
