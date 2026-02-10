"""
Testes para app.financeiro.parcela_utils.

Cobre edge cases de conversao do campo parcela entre VARCHAR e INTEGER.
"""

import logging
import pytest

from app.financeiro.parcela_utils import parcela_to_int, parcela_to_str, parcela_to_odoo


# =============================================================================
# parcela_to_int
# =============================================================================

class TestParcelaToInt:
    """Testes de conversao para int (usado em campos cache e Odoo API)."""

    def test_none_retorna_none(self):
        """None NUNCA deve retornar 0."""
        assert parcela_to_int(None) is None

    def test_int_passthrough(self):
        """Int deve ser retornado sem alteracao."""
        assert parcela_to_int(3) == 3

    def test_int_zero(self):
        """Zero explicito deve retornar 0 (nao None)."""
        assert parcela_to_int(0) == 0

    def test_float_para_int(self):
        """Float deve ser truncado para int."""
        assert parcela_to_int(3.0) == 3

    def test_string_numerica(self):
        """String numerica deve converter para int."""
        assert parcela_to_int("3") == 3

    def test_string_com_espacos(self):
        """String com espacos deve ser limpa."""
        assert parcela_to_int("  3  ") == 3

    def test_string_prefixo_p(self):
        """Prefixo P (CNAB) deve ser removido."""
        assert parcela_to_int("P3") == 3

    def test_string_prefixo_p_minusculo(self):
        """Prefixo p minusculo tambem deve funcionar."""
        assert parcela_to_int("p3") == 3

    def test_string_vazia(self):
        """String vazia deve retornar None."""
        assert parcela_to_int("") is None

    def test_string_so_espacos(self):
        """String so com espacos deve retornar None."""
        assert parcela_to_int("   ") is None

    def test_string_invalida(self, caplog):
        """String nao-numerica deve retornar None com warning."""
        with caplog.at_level(logging.WARNING):
            result = parcela_to_int("abc")
        assert result is None
        assert "valor invalido" in caplog.text

    def test_string_so_p(self):
        """String 'P' sozinha (sem numero) deve retornar None."""
        assert parcela_to_int("P") is None

    def test_inteiro_negativo(self):
        """Inteiro negativo deve ser passthrough (rarissimo, mas correto)."""
        assert parcela_to_int(-1) == -1

    def test_string_grande(self):
        """String numerica grande deve converter normalmente."""
        assert parcela_to_int("999") == 999


# =============================================================================
# parcela_to_str
# =============================================================================

class TestParcelaToStr:
    """Testes de conversao para string (usado ao buscar em contas_a_receber/pagar)."""

    def test_none_retorna_none(self):
        assert parcela_to_str(None) is None

    def test_string_passthrough(self):
        assert parcela_to_str("3") == "3"

    def test_string_com_espacos(self):
        """Espacos devem ser removidos."""
        assert parcela_to_str("  3  ") == "3"

    def test_string_vazia(self):
        assert parcela_to_str("") is None

    def test_string_so_espacos(self):
        assert parcela_to_str("   ") is None

    def test_int_para_str(self):
        assert parcela_to_str(3) == "3"

    def test_int_zero_para_str(self):
        assert parcela_to_str(0) == "0"

    def test_float_para_str(self):
        """Float deve ser truncado e convertido."""
        assert parcela_to_str(3.0) == "3"

    def test_string_com_prefixo_p(self):
        """Prefixo P deve ser preservado em to_str (nao remove)."""
        assert parcela_to_str("P3") == "P3"


# =============================================================================
# parcela_to_odoo
# =============================================================================

class TestParcelaToOdoo:
    """Testes do alias para Odoo (semanticamente identico a parcela_to_int)."""

    def test_none_retorna_none(self):
        """CRITICO: None NAO deve retornar 0 (quebraria busca no Odoo)."""
        assert parcela_to_odoo(None) is None

    def test_string_numerica(self):
        assert parcela_to_odoo("3") == 3

    def test_string_prefixo_p(self):
        assert parcela_to_odoo("P3") == 3

    def test_string_invalida(self):
        assert parcela_to_odoo("abc") is None

    def test_int_passthrough(self):
        assert parcela_to_odoo(1) == 1

    def test_zero_explicito(self):
        assert parcela_to_odoo(0) == 0
