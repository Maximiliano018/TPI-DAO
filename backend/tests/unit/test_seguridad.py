from datetime import timedelta

import pytest

from biblioteca.domain.errors import NoAutenticado
from biblioteca.infrastructure.security import HasherArgon2, TokensJwt
from tests.apoyo import RelojFijo


class TestHasherArgon2:
    def test_verifica_la_contrasena_correcta(self) -> None:
        hasher = HasherArgon2()
        hash_guardado = hasher.hashear("secreta123")
        assert hash_guardado.startswith("$argon2")
        assert hasher.verificar("secreta123", hash_guardado)
        assert not hasher.verificar("otra-clave", hash_guardado)

    def test_un_hash_desconocido_no_verifica(self) -> None:
        assert not HasherArgon2().verificar("secreta123", "no-es-un-hash")


class TestTokensJwt:
    def _tokens(self, reloj: RelojFijo, secreto: str = "secreto-de-prueba") -> TokensJwt:
        return TokensJwt(secreto * 4, timedelta(hours=8), reloj)

    def test_el_token_identifica_al_usuario(self) -> None:
        tokens = self._tokens(RelojFijo())
        emitido = tokens.emitir(42)
        assert tokens.leer_usuario_id(emitido.token) == 42

    def test_informa_cuando_expira(self) -> None:
        reloj = RelojFijo()
        emitido = self._tokens(reloj).emitir(42)
        assert emitido.expira_en == reloj.ahora() + timedelta(hours=8)

    def test_el_token_vencido_no_sirve(self) -> None:
        reloj = RelojFijo()
        tokens = self._tokens(reloj)
        emitido = tokens.emitir(42)
        reloj.adelantar(hours=8)
        with pytest.raises(NoAutenticado, match="expiró"):
            tokens.leer_usuario_id(emitido.token)

    def test_un_token_firmado_con_otro_secreto_no_sirve(self) -> None:
        reloj = RelojFijo()
        ajeno = self._tokens(reloj, secreto="otro-secreto").emitir(42)
        with pytest.raises(NoAutenticado, match="no es válido"):
            self._tokens(reloj).leer_usuario_id(ajeno.token)

    def test_un_texto_cualquiera_no_es_un_token(self) -> None:
        with pytest.raises(NoAutenticado):
            self._tokens(RelojFijo()).leer_usuario_id("cualquier-cosa")
