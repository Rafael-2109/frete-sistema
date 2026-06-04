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


# =====================================================================
# Task 2 — Branch SQL-first em run() (Generator/Executor monkeypatched)
# =====================================================================

def _boom_generator(*args, **kwargs):
    raise AssertionError("Generator NAO deveria ser chamado em SQL-first")


@pytest.fixture(scope="module")
def pipeline():
    # Instancia o pipeline (so' carrega schemas JSON — sem DB, sem LLM).
    return T.TextToSQLPipeline()


class TestSqlFirstBranch:
    def test_off_mode_uses_generator(self, pipeline, monkeypatch):
        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT cod_produto FROM carteira_principal LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], ["cod_produto"]))
        res = pipeline.run("SELECT cod_produto FROM carteira_principal LIMIT 5", sql_first_mode="off")
        # OFF: comportamento atual — a "pergunta" (mesmo SQL) passa pelo Generator
        assert calls["gen"] == 1
        assert res["etapas"].get("sql_first") is not True

    def test_on_mode_raw_sql_skips_generator_executes_literal(self, pipeline, monkeypatch):
        calls = {"gen": 0}
        captured = {}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT 999 FROM outra"

        def fake_exec(sql, read_write=False):
            captured["sql"] = sql
            captured["rw"] = read_write
            return ([{"cod_produto": "ABC"}], ["cod_produto"])

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)
        literal = "SELECT cod_produto FROM carteira_principal WHERE ativo = True LIMIT 5"
        res = pipeline.run(literal, sql_first_mode="on")
        assert calls["gen"] == 0                  # Generator NAO chamado
        assert res["sucesso"] is True
        assert captured["sql"].startswith("SELECT cod_produto FROM carteira_principal")
        assert res["sql"] == literal              # executado LITERAL (sem reescrita)
        assert captured["rw"] is False            # nao-admin -> read-only
        assert res["etapas"].get("sql_first") is True

    def test_on_mode_strips_fences_before_executing(self, pipeline, monkeypatch):
        captured = {}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(pipeline.executor, "execute",
                            lambda sql, read_write=False: captured.__setitem__("sql", sql) or ([], []))
        res = pipeline.run("```sql\nSELECT cod_produto FROM carteira_principal\n```", sql_first_mode="on")
        assert res["sucesso"] is True
        assert captured["sql"] == "SELECT cod_produto FROM carteira_principal"

    def test_on_mode_natural_language_falls_back_to_generator(self, pipeline, monkeypatch):
        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT cod_produto FROM carteira_principal LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], ["cod_produto"]))
        res = pipeline.run("Quais produtos da carteira estao pendentes?", sql_first_mode="on")
        assert calls["gen"] == 1                   # NL -> fallback Generator
        assert res["etapas"].get("sql_first") is not True

    def test_on_mode_admin_dml_executes_read_write(self, pipeline, monkeypatch):
        captured = {}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)

        def fake_exec(sql, read_write=False):
            captured["rw"] = read_write
            captured["sql"] = sql
            return ([], [])

        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)
        res = pipeline.run(
            "UPDATE cadastro_palletizacao SET tipo_materia_prima = 'MP' WHERE cod_produto = '1'",
            sql_first_mode="on", admin_mode=True,
        )
        assert res["sucesso"] is True
        assert captured["rw"] is True              # admin -> read_write
        assert res["etapas"].get("sql_first") is True

    def test_shadow_mode_logs_but_uses_generator(self, pipeline, monkeypatch):
        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT cod_produto FROM carteira_principal LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], ["cod_produto"]))
        res = pipeline.run("SELECT cod_produto FROM carteira_principal LIMIT 5", sql_first_mode="shadow")
        # SHADOW: observa (registra etapa) mas NAO muda comportamento (Generator roda)
        assert calls["gen"] == 1
        assert res["etapas"].get("sql_first") is not True
        assert "sql_first_shadow" in res["etapas"]

    def test_default_mode_off_when_param_omitted(self, pipeline, monkeypatch):
        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT cod_produto FROM carteira_principal LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], ["cod_produto"]))
        # Sem sql_first_mode -> default "off" -> Generator (zero regressao)
        res = pipeline.run("SELECT cod_produto FROM carteira_principal LIMIT 5")
        assert calls["gen"] == 1


# =====================================================================
# Task 3 — Feedback de schema do Deterministic Validator (campo_inexistente)
# =====================================================================

class TestSqlFirstSchemaFeedback:
    def test_nonexistent_field_blocks_with_real_fields(self, pipeline, monkeypatch):
        called = {"exec": 0}

        def fake_exec(sql, read_write=False):
            called["exec"] += 1
            return ([], [])

        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        sql = "SELECT s.campo_que_nao_existe FROM separacao s LIMIT 5"
        res = pipeline.run(sql, sql_first_mode="on")
        assert res["sucesso"] is False
        assert called["exec"] == 0                       # NAO executou SQL invalida
        assert "campo_que_nao_existe" in res["aviso"]    # cita o campo errado
        assert "qtd_saldo" in res["aviso"]               # devolve campos REAIS da separacao
        assert res["etapas"].get("sql_first_blocked")

    def test_valid_field_executes(self, pipeline, monkeypatch):
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(pipeline.executor, "execute",
                            lambda sql, read_write=False: ([{"qtd_saldo": 10}], ["qtd_saldo"]))
        res = pipeline.run("SELECT s.qtd_saldo FROM separacao s LIMIT 5", sql_first_mode="on")
        assert res["sucesso"] is True


# =====================================================================
# Task 6 — resolve_sql_first_mode (flag SQL_AGENT_SQL_FIRST + escopo por admin)
# =====================================================================

class TestResolveSqlFirstMode:
    def _r(self):
        from app.agente.config.feature_flags import resolve_sql_first_mode
        return resolve_sql_first_mode

    def test_default_off_when_unset(self, monkeypatch):
        monkeypatch.delenv("SQL_AGENT_SQL_FIRST", raising=False)
        r = self._r()
        assert r(True) == "off"
        assert r(False) == "off"

    def test_off_explicit(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "off")
        r = self._r()
        assert r(True) == "off" and r(False) == "off"

    def test_shadow_for_everyone(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "shadow")
        r = self._r()
        assert r(True) == "shadow" and r(False) == "shadow"

    def test_admin_stage_admin_on_others_shadow(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "admin")
        r = self._r()
        assert r(True) == "on"        # admin -> SQL-first real
        assert r(False) == "shadow"   # nao-admin -> observa (sem mudar comportamento)

    def test_on_for_everyone(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "on")
        r = self._r()
        assert r(True) == "on" and r(False) == "on"

    def test_invalid_value_falls_back_off(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "garbage")
        r = self._r()
        assert r(True) == "off" and r(False) == "off"

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "ON")
        r = self._r()
        assert r(True) == "on"


# =====================================================================
# Task 6 — wiring na tool: _execute_in_app_context repassa sql_first_mode
# =====================================================================

class TestToolForwardsSqlFirstMode:
    def test_execute_forwards_sql_first_mode_to_run(self, app):
        from app.agente.tools import text_to_sql_tool as tool

        captured = {}

        class FakePipeline:
            def run(self, pergunta, **kwargs):
                captured["pergunta"] = pergunta
                captured.update(kwargs)
                return {"sucesso": True}

        with app.app_context():
            tool._execute_in_app_context(
                FakePipeline(), "SELECT 1 FROM carteira_principal", sql_first_mode="on"
            )
        assert captured.get("sql_first_mode") == "on"

    def test_execute_defaults_sql_first_mode_off(self, app):
        from app.agente.tools import text_to_sql_tool as tool

        captured = {}

        class FakePipeline:
            def run(self, pergunta, **kwargs):
                captured.update(kwargs)
                return {"sucesso": True}

        with app.app_context():
            tool._execute_in_app_context(FakePipeline(), "SELECT 1 FROM carteira_principal")
        assert captured.get("sql_first_mode") == "off"


# =====================================================================
# Task 5 — Regra 13 (contas a receber vencidas) exposta via schema (durable)
# =====================================================================

class TestSchemaRule13Exposed:
    def test_contas_a_receber_business_rule_present(self):
        sp = T.SchemaProvider()
        rules = (sp.get_table_schema("contas_a_receber") or {}).get("business_rules", []) or []
        joined = " ".join(rules).lower()
        assert "vencidas" in joined        # palavra exclusiva da regra (nao e' nome de campo)
        assert "parcela_paga" in joined
        assert "vencimento" in joined

    def test_rule13_in_schema_feedback_text(self):
        sp = T.SchemaProvider()
        txt = sp.get_tables_schema_text(["contas_a_receber"]).lower()
        assert "vencidas" in txt            # regra exposta no texto do schema (feedback SQL-first)


# =====================================================================
# Task 4 — Description da tool: contrato SQL-first + budget de tamanho
# =====================================================================

class TestToolDescription:
    def _desc(self):
        from app.agente.tools.text_to_sql_tool import CONSULTAR_SQL_DESCRIPTION
        return CONSULTAR_SQL_DESCRIPTION

    def test_description_within_budget(self):
        # MCP tool description — manter enxuta (folga ampla vs limites do SDK).
        assert 0 < len(self._desc()) < 2000

    def test_description_mentions_sql_first_contract(self):
        d = self._desc().lower()
        assert "sql-first" in d or "sql first" in d
        # contrato: aceita SQL pronto + devolve schema real se errar campo
        assert "schema" in d
