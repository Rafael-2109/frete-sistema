"""
Testes do subsistema S3-A do pacote Text-to-SQL (nucleo de geracao).

Plano: docs/superpowers/plans/2026-06-07-text-to-sql-S3-nucleo-geracao.md
MASTER: docs/superpowers/specs/2026-06-07-text-to-sql-arquitetura-MASTER-design.md

Determinísticos (regra do projeto: sem evals LLM caros). Generator/Executor sao
monkeypatched; o validador deterministico le apenas schemas JSON; nenhum toca DB,
Redis ou LLM real.

Escopo S3-A coberto aqui:
  G1  contrato explicito sql=/pergunta= (mata F5: heuristica fragil)
  G2  F1 — Generator max_tokens 500 -> >=2000 (anti-truncamento de CTE)
  G3  F4 — revalidacao de template >=0.92 contra schema (stale = campo velho)
  G5  auditoria entry_kind (sql_explicit | sql_heuristic | nl) p/ decisao #1
  G6  SQL-first default 'on' no codigo (decisao #5; pos-S1)
  G8  admin/comum usam a MESMA via de geracao; diferem SO em permissao (Safety)
"""
import os
import sys

import pytest

# Tornar text_to_sql importavel (mesmo pattern dos tools MCP em app/agente/tools/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, '.claude', 'skills', 'consultando-sql', 'scripts')
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import text_to_sql as T  # noqa: E402


def _boom_generator(*args, **kwargs):
    raise AssertionError("Generator NAO deveria ser chamado neste caminho")


@pytest.fixture(scope="module")
def pipeline():
    # So' carrega schemas JSON — sem DB, sem LLM.
    return T.TextToSQLPipeline()


# =====================================================================
# G1 — Contrato explicito sql= (literal) vs pergunta= (NL) — mata F5
# =====================================================================

class TestExplicitSqlContract:
    def test_sql_literal_executes_literal_bypassing_heuristic(self, pipeline, monkeypatch):
        # "SELECT 1" sem FROM: looks_like_raw_sql REJEITA (conservador). O contrato
        # explicito sql_literal forca a execucao literal mesmo assim (mata F5).
        captured = {}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(
            pipeline.executor, "execute",
            lambda sql, read_write=False: captured.__setitem__("sql", sql) or ([{"x": 1}], ["x"]),
        )
        assert T.looks_like_raw_sql("SELECT 1") is False  # heuristica rejeitaria
        res = pipeline.run("pergunta ignorada", sql_literal="SELECT 1")
        assert res["sucesso"] is True
        assert captured["sql"] == "SELECT 1"            # literal, sem Generator
        assert res["etapas"].get("sql_first") is True

    def test_sql_literal_strips_markdown_fences(self, pipeline, monkeypatch):
        captured = {}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(
            pipeline.executor, "execute",
            lambda sql, read_write=False: captured.__setitem__("sql", sql) or ([], []),
        )
        res = pipeline.run("x", sql_literal="```sql\nSELECT cod_produto FROM carteira_principal\n```")
        assert res["sucesso"] is True
        assert captured["sql"] == "SELECT cod_produto FROM carteira_principal"

    def test_no_sql_literal_uses_pergunta_nl(self, pipeline, monkeypatch):
        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT cod_produto FROM carteira_principal LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], ["cod_produto"]))
        res = pipeline.run("Quais produtos pendentes?")  # sem sql_literal -> NL
        assert calls["gen"] == 1
        assert res["etapas"].get("sql_first") is not True

    def test_sql_literal_admin_dml_read_write(self, pipeline, monkeypatch):
        captured = {}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)

        def fake_exec(sql, read_write=False):
            captured["rw"] = read_write
            return ([], [])

        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)
        res = pipeline.run(
            "x",
            sql_literal="UPDATE cadastro_palletizacao SET tipo_materia_prima = 'MP' WHERE cod_produto = '1'",
            admin_mode=True,
        )
        assert res["sucesso"] is True
        assert captured["rw"] is True


class TestResolveToolInput:
    """Helper puro de roteamento do contrato da tool (sql= vs pergunta=)."""

    def _f(self):
        from app.agente.tools.text_to_sql_tool import _resolve_tool_input
        return _resolve_tool_input

    def test_sql_param_routes_to_literal(self):
        pergunta, literal = self._f()({"sql": "SELECT 1 FROM carteira_principal"})
        assert literal == "SELECT 1 FROM carteira_principal"

    def test_pergunta_only_is_nl(self):
        pergunta, literal = self._f()({"pergunta": "Top 10 clientes por valor"})
        assert literal is None
        assert pergunta == "Top 10 clientes por valor"

    def test_sql_takes_precedence_over_pergunta(self):
        pergunta, literal = self._f()({"sql": "SELECT 1 FROM t", "pergunta": "algo"})
        assert literal == "SELECT 1 FROM t"

    def test_empty_both(self):
        pergunta, literal = self._f()({})
        assert literal is None
        assert pergunta == ""

    def test_whitespace_only_sql_is_nl(self):
        pergunta, literal = self._f()({"sql": "   ", "pergunta": "quanto de palmito"})
        assert literal is None
        assert pergunta == "quanto de palmito"


class TestToolInputSchemaOptional:
    """O contrato e' 'UM ou outro': nem pergunta nem sql podem ser obrigatorios no
    schema (o wrapper enhanced marca TODO param de dict-simples como required —
    por isso usamos JSON-schema completo com required vazio)."""

    def _schema(self):
        from app.agente.tools.text_to_sql_tool import CONSULTAR_SQL_INPUT_SCHEMA
        return CONSULTAR_SQL_INPUT_SCHEMA

    def test_pergunta_and_sql_present_as_properties(self):
        props = self._schema()["properties"]
        assert "pergunta" in props
        assert "sql" in props

    def test_neither_param_is_required(self):
        # agente manda sql= OU pergunta= -> nenhum obrigatorio (tool valida vazio).
        assert self._schema().get("required", []) == []


class TestToolForwardsSqlLiteral:
    def test_execute_forwards_sql_literal_to_run(self, app):
        from app.agente.tools import text_to_sql_tool as tool

        captured = {}

        class FakePipeline:
            def run(self, pergunta, **kwargs):
                captured["pergunta"] = pergunta
                captured.update(kwargs)
                return {"sucesso": True}

        with app.app_context():
            tool._execute_in_app_context(
                FakePipeline(), "ignored", sql_literal="SELECT 1 FROM carteira_principal"
            )
        assert captured.get("sql_literal") == "SELECT 1 FROM carteira_principal"

    def test_execute_defaults_sql_literal_none(self, app):
        from app.agente.tools import text_to_sql_tool as tool

        captured = {}

        class FakePipeline:
            def run(self, pergunta, **kwargs):
                captured.update(kwargs)
                return {"sucesso": True}

        with app.app_context():
            tool._execute_in_app_context(FakePipeline(), "Top 10 clientes")
        assert captured.get("sql_literal") is None


# =====================================================================
# G2 — F1: Generator max_tokens 500 -> >=2000 (anti-truncamento de CTE)
# =====================================================================

class TestGeneratorMaxTokens:
    def test_generator_uses_increased_max_tokens(self, pipeline, monkeypatch):
        captured = {}

        class _Resp:
            content = [type("X", (), {"text": "SELECT cod_produto FROM carteira_principal LIMIT 5"})()]

        def fake_call(client, model, max_tokens, **kwargs):
            captured["max_tokens"] = max_tokens
            return _Resp()

        monkeypatch.setattr(T, "_call_api_with_retry", fake_call)
        pipeline.generator.generate("Quais produtos pendentes?")
        assert captured["max_tokens"] >= 2000  # F1: era 500 (truncava CTE/JOIN longo)

    def test_generator_max_tokens_env_override(self, pipeline, monkeypatch):
        captured = {}

        class _Resp:
            content = [type("X", (), {"text": "SELECT 1 FROM carteira_principal"})()]

        def fake_call(client, model, max_tokens, **kwargs):
            captured["max_tokens"] = max_tokens
            return _Resp()

        monkeypatch.setenv("TEXT_TO_SQL_GEN_MAX_TOKENS", "3000")
        monkeypatch.setattr(T, "_call_api_with_retry", fake_call)
        pipeline.generator.generate("x")
        assert captured["max_tokens"] == 3000


# =====================================================================
# G3 — F4: revalidacao de template contra schema (stale)
# =====================================================================

class TestTemplateFieldsValidation:
    def test_sql_with_nonexistent_field_is_invalid(self, pipeline):
        assert pipeline._sql_fields_valid("SELECT s.campo_que_nao_existe FROM separacao s") is False

    def test_sql_with_valid_field_is_valid(self, pipeline):
        assert pipeline._sql_fields_valid("SELECT s.qtd_saldo FROM separacao s") is True

    def test_stale_template_discarded_falls_through_to_generator(self, pipeline, monkeypatch):
        import app.embeddings.config as cfg
        import app.embeddings.service as svcmod
        monkeypatch.setattr(cfg, "EMBEDDINGS_ENABLED", True, raising=False)
        monkeypatch.setattr(cfg, "SQL_TEMPLATE_SEARCH", True, raising=False)

        class FakeSvc:
            def search_sql_templates(self, q, limit=3, min_similarity=0.75):
                # similaridade alta MAS SQL com campo velho (stale)
                return [{
                    "similarity": 0.97,
                    "sql_text": "SELECT s.campo_que_nao_existe FROM separacao s LIMIT 5",
                    "question_text": "separacoes do produto",
                }]

        monkeypatch.setattr(svcmod, "EmbeddingService", FakeSvc)

        calls = {"gen": 0}

        def fake_gen(q, catalog_text_override=None):
            calls["gen"] += 1
            return "SELECT s.qtd_saldo FROM separacao s LIMIT 5"

        monkeypatch.setattr(pipeline.generator, "generate", fake_gen)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], []))
        res = pipeline.run("separacoes do produto X")
        assert res["etapas"].get("template_stale_discarded") is True
        assert calls["gen"] == 1  # template descartado -> caiu no Generator

    def test_valid_template_used_directly(self, pipeline, monkeypatch):
        import app.embeddings.config as cfg
        import app.embeddings.service as svcmod
        monkeypatch.setattr(cfg, "EMBEDDINGS_ENABLED", True, raising=False)
        monkeypatch.setattr(cfg, "SQL_TEMPLATE_SEARCH", True, raising=False)

        class FakeSvc:
            def search_sql_templates(self, q, limit=3, min_similarity=0.75):
                return [{
                    "similarity": 0.97,
                    "sql_text": "SELECT s.qtd_saldo FROM separacao s LIMIT 5",
                    "question_text": "separacoes do produto",
                }]

        monkeypatch.setattr(svcmod, "EmbeddingService", FakeSvc)
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], []))
        res = pipeline.run("separacoes do produto X")
        assert res["etapas"].get("template_direct_hit") is True
        assert res["etapas"].get("template_stale_discarded") is not True


# =====================================================================
# G5 — Auditoria entry_kind (sql_explicit | sql_heuristic | nl)
# =====================================================================

class TestEntryKindAudit:
    def test_entry_kind_sql_explicit(self, pipeline, monkeypatch):
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], []))
        res = pipeline.run("x", sql_literal="SELECT cod_produto FROM carteira_principal")
        assert res["etapas"].get("entry_kind") == "sql_explicit"

    def test_entry_kind_sql_heuristic(self, pipeline, monkeypatch):
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], []))
        res = pipeline.run("SELECT cod_produto FROM carteira_principal", sql_first_mode="on")
        assert res["etapas"].get("entry_kind") == "sql_heuristic"

    def test_entry_kind_nl(self, pipeline, monkeypatch):
        monkeypatch.setattr(
            pipeline.generator, "generate",
            lambda q, catalog_text_override=None: "SELECT cod_produto FROM carteira_principal LIMIT 5",
        )
        monkeypatch.setattr(pipeline.executor, "execute", lambda sql, read_write=False: ([], []))
        res = pipeline.run("Quais produtos pendentes?", sql_first_mode="on")
        assert res["etapas"].get("entry_kind") == "nl"


# =====================================================================
# G6 — SQL-first default 'on' no codigo (decisao #5; pos-S1)
# =====================================================================

class TestResolveSqlFirstDefaultOn:
    def _r(self):
        from app.agente.config.feature_flags import resolve_sql_first_mode
        return resolve_sql_first_mode

    def test_default_on_when_unset(self, monkeypatch):
        monkeypatch.delenv("SQL_AGENT_SQL_FIRST", raising=False)
        r = self._r()
        assert r(True) == "on"
        assert r(False) == "on"

    def test_explicit_off_still_off(self, monkeypatch):
        # Kill-switch continua funcionando: SQL_AGENT_SQL_FIRST=off desliga tudo.
        monkeypatch.setenv("SQL_AGENT_SQL_FIRST", "off")
        r = self._r()
        assert r(True) == "off"
        assert r(False) == "off"


# =====================================================================
# G8 — Permissao != geracao: admin e comum geram pela MESMA via
# =====================================================================

class TestPermissionVsGeneration:
    def test_admin_and_comum_same_literal_path_differ_only_in_rw(self, pipeline, monkeypatch):
        captured = {"rw": []}
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)

        def fake_exec(sql, read_write=False):
            captured["rw"].append(read_write)
            return ([], [])

        monkeypatch.setattr(pipeline.executor, "execute", fake_exec)
        sql = "SELECT cod_produto FROM carteira_principal LIMIT 5"
        r_comum = pipeline.run("x", sql_literal=sql, admin_mode=False)
        r_admin = pipeline.run("x", sql_literal=sql, admin_mode=True)
        # MESMA via: ambos literal (sql_first), Generator nunca chamado.
        assert r_comum["etapas"].get("sql_first") is True
        assert r_admin["etapas"].get("sql_first") is True
        # Unica diferenca = permissao: comum read-only, admin read_write.
        assert captured["rw"] == [False, True]

    def test_comum_blocked_table_barred_even_in_literal(self, pipeline, monkeypatch):
        # Safety NUNCA regride: comum referenciando tabela bloqueada -> barrado.
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        called = {"exec": 0}
        monkeypatch.setattr(
            pipeline.executor, "execute",
            lambda sql, read_write=False: called.__setitem__("exec", called["exec"] + 1) or ([], []),
        )
        res = pipeline.run(
            "x",
            sql_literal="SELECT * FROM pessoal_salarios",
            admin_mode=False,
            extra_blocked_tables={"pessoal_salarios"},
        )
        assert res["sucesso"] is False
        assert called["exec"] == 0  # nunca executou tabela bloqueada

    def test_comum_dml_barred_even_in_literal(self, pipeline, monkeypatch):
        # comum tentando DML literal -> barrado (Safety read-only/keywords).
        monkeypatch.setattr(pipeline.generator, "generate", _boom_generator)
        called = {"exec": 0}
        monkeypatch.setattr(
            pipeline.executor, "execute",
            lambda sql, read_write=False: called.__setitem__("exec", called["exec"] + 1) or ([], []),
        )
        res = pipeline.run(
            "x",
            sql_literal="DELETE FROM carteira_principal WHERE id = 1",
            admin_mode=False,
        )
        assert res["sucesso"] is False
        assert called["exec"] == 0
