"""
Testes do redesign SQL-first da tool consultar_sql (Fix B — sessao #787).

Determinísticos: NÃO dependem de DB, Redis nem LLM. As funções puras (Task 1)
não tocam nada; o Deterministic Validator (Task 3) lê apenas schemas JSON; o
branch SQL-first (Task 2) é exercido com Generator/Executor monkeypatched.

Plano: docs/superpowers/plans/2026-06-04-redesign-consultar-sql-sql-first.md
"""
import os
import sys

import pytest

# Tornar text_to_sql importável (mesmo pattern dos tools MCP em app/agente/tools/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, '.claude', 'skills', 'consultando-sql', 'scripts')
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import text_to_sql as T  # noqa: E402


# =====================================================================
# Task 1 — normalize_sql_candidate (strip fences/comentários)
# =====================================================================

class TestNormalizeSqlCandidate:
    def test_strip_markdown_fences_sql(self):
        assert T.normalize_sql_candidate("```sql\nSELECT * FROM separacao\n```") == "SELECT * FROM separacao"

    def test_strip_markdown_fences_plain(self):
        assert T.normalize_sql_candidate("```\nSELECT 1 FROM t\n```") == "SELECT 1 FROM t"

    def test_strip_leading_and_trailing_whitespace(self):
        assert T.normalize_sql_candidate("   \n  SELECT * FROM t  ") == "SELECT * FROM t"

    def test_strip_leading_line_comment(self):
        assert T.normalize_sql_candidate("-- comentário do agente\nSELECT * FROM t") == "SELECT * FROM t"

    def test_strip_leading_block_comment(self):
        assert T.normalize_sql_candidate("/* nota */ SELECT * FROM t") == "SELECT * FROM t"

    def test_plain_passthrough(self):
        assert T.normalize_sql_candidate("SELECT a FROM t") == "SELECT a FROM t"

    def test_empty_returns_empty(self):
        assert T.normalize_sql_candidate("") == ""
        assert T.normalize_sql_candidate("   ") == ""

    def test_inline_comment_preserved_for_execution(self):
        # Comentário no MEIO é inofensivo no Postgres — não removemos (literal).
        out = T.normalize_sql_candidate("SELECT a FROM t  -- coluna a")
        assert out.startswith("SELECT a FROM t")


# =====================================================================
# Task 1 — looks_like_raw_sql (detector conservador)
# =====================================================================

class TestLooksLikeRawSqlPositive:
    @pytest.mark.parametrize("txt", [
        "SELECT * FROM separacao",
        "select cod_produto, sum(qtd_saldo) from separacao group by cod_produto",
        "WITH base AS (SELECT id FROM embarques) SELECT * FROM base",
        "  \n SELECT 1 AS x FROM carteira_principal LIMIT 5",
        "```sql\nSELECT * FROM embarques\n```",
        "-- relatorio motos\nSELECT * FROM separacao",
        "UPDATE cadastro_palletizacao SET tipo_materia_prima = 'X' WHERE cod_produto = '123'",
        "INSERT INTO foo (a) VALUES (1)",
        "DELETE FROM foo WHERE id = 1",
    ])
    def test_detects_raw_sql(self, txt):
        assert T.looks_like_raw_sql(txt) is True

    def test_accent_inside_string_literal_still_sql(self):
        # Acento DENTRO de literal não desqualifica (literais são removidos no probe).
        assert T.looks_like_raw_sql("SELECT * FROM embarques WHERE cidade = 'São Paulo'") is True


class TestLooksLikeRawSqlNegative:
    @pytest.mark.parametrize("txt", [
        "",
        "   ",
        "Top 10 clientes por valor",
        "Pedidos pendentes por estado",
        "Quantas motos HORA em estoque?",
        "Valor médio de frete por transportadora",
        "Selecione os pedidos pendentes",            # 'SELECIONE' != 'SELECT'
        "WITH muito carinho responda a pergunta",    # WITH sem '<ident> AS ('
        "from the report, list the top clients",     # não começa com SELECT/WITH
        "SELECT 1",                                  # sem FROM (conservador)
    ])
    def test_rejects_natural_language(self, txt):
        assert T.looks_like_raw_sql(txt) is False

    def test_accented_word_outside_literal_is_natural_language(self):
        # 'São' fora de literal => trata como PT-BR/NL (guarda anti-falso-positivo).
        assert T.looks_like_raw_sql("Select all orders from São Paulo") is False

    def test_returns_real_bool(self):
        assert T.looks_like_raw_sql("SELECT * FROM t") is True
        assert T.looks_like_raw_sql("ola") is False
