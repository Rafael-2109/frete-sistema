"""Tests para is_cannot_marshal_none em app/odoo/utils/connection.py.

Funcao pura (sem Flask/DB) — testa o helper canonico do gotcha O6:
'cannot marshal None' = SUCESSO-com-aviso (metodo Odoo retornou None).

Semantica: .claude/references/odoo/GOTCHAS.md (Matriz de Erros).
"""
from app.odoo.utils.connection import is_cannot_marshal_none


class TestIsCannotMarshalNone:
    # --- casos TRUE (deve detectar como sucesso O6) ---

    def test_excecao_mensagem_exata(self):
        """Mensagem exata da fault XML-RPC deve retornar True."""
        exc = Exception("cannot marshal None unless allow_none is enabled")
        assert is_cannot_marshal_none(exc) is True

    def test_excecao_mensagem_lowercase(self):
        """Variante toda minuscula deve retornar True (case-insensitive)."""
        exc = Exception("cannot marshal none unless allow_none is enabled")
        assert is_cannot_marshal_none(exc) is True

    def test_excecao_mensagem_mixed_case(self):
        """Variante de casing misto deve retornar True."""
        exc = Exception("Cannot Marshal None unless allow_none is enabled")
        assert is_cannot_marshal_none(exc) is True

    def test_excecao_mensagem_uppercase(self):
        """Variante toda maiuscula deve retornar True."""
        exc = Exception("CANNOT MARSHAL NONE")
        assert is_cannot_marshal_none(exc) is True

    def test_string_direta_true(self):
        """String direta (nao excecao) com o texto deve retornar True."""
        assert is_cannot_marshal_none("cannot marshal None") is True

    def test_string_direta_parcial(self):
        """String com apenas a parte relevante deve retornar True."""
        assert is_cannot_marshal_none("prefix cannot marshal none suffix") is True

    def test_excecao_sem_allow_none_no_texto(self):
        """Apenas 'cannot marshal None' sem o restante deve retornar True."""
        assert is_cannot_marshal_none(Exception("cannot marshal None")) is True

    # --- casos FALSE (NAO deve detectar como sucesso O6) ---

    def test_excecao_timeout(self):
        """Timeout nao e o gotcha O6."""
        assert is_cannot_marshal_none(Exception("timeout")) is False

    def test_excecao_connection_refused(self):
        """Connection refused nao e o gotcha O6."""
        assert is_cannot_marshal_none(Exception("connection refused")) is False

    def test_excecao_vazia(self):
        """Excecao sem mensagem deve retornar False."""
        assert is_cannot_marshal_none(Exception()) is False

    def test_string_vazia(self):
        """String vazia deve retornar False."""
        assert is_cannot_marshal_none("") is False

    def test_string_parcial_marshal_sem_none(self):
        """Texto 'cannot marshal' sem 'none' deve retornar False."""
        assert is_cannot_marshal_none("cannot marshal") is False

    def test_excecao_authentication_failed(self):
        """Authentication failed nao e o gotcha O6."""
        assert is_cannot_marshal_none(Exception("Authentication failed")) is False

    def test_excecao_field_does_not_exist(self):
        """Erro de campo inexistente nao e o gotcha O6."""
        assert is_cannot_marshal_none(
            Exception("Field 'x' does not exist")
        ) is False

    def test_aceita_base_exception(self):
        """Deve aceitar BaseException alem de Exception."""
        exc = BaseException("cannot marshal None")
        assert is_cannot_marshal_none(exc) is True
