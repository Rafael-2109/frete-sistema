"""Testes determinísticos do subsistema S2 — overlay de curadoria.

S2 (ver MASTER text-to-sql) eleva a qualidade de schema dando significado real
aos campos. Decisão fechada 1: descrições moram na FONTE (modelo); apenas
`business_rules` e `query_hints` (texto rico / SQL de exemplo) vivem em OVERLAY
(invariante 4: curadoria nunca em arquivo gerado — aplicada em RUNTIME pelo
SchemaProvider, não materializada em tables/*.json).

Estes testes cobrem o MECANISMO:
- função pura de merge (business_rules/query_hints/lineage, precedência);
- SchemaProvider aplica o overlay a tabelas não-core (hoje só linhagem é aplicada);
- o conteúdo curado é EXIBIDO em get_tables_schema_text e em _format_schema
  (o formatter de consultar_schema).

Invariante 6: pytest determinístico, SEM evals LLM, SEM create_app/DB
(SchemaProvider lê apenas JSONs do repo).
"""
import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

_REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO / ".claude/skills/consultando-sql/scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import text_to_sql as T  # noqa: E402


def _load_format_schema():
    """Carrega _format_schema de schema_mcp_tool isolando do pacote app.agente."""
    smt_path = _REPO / "app/agente/tools/schema_mcp_tool.py"
    spec = importlib.util.spec_from_file_location("schema_mcp_tool_s2mod", smt_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["schema_mcp_tool_s2mod"] = mod
    spec.loader.exec_module(mod)
    return mod._format_schema


def _load_generate_schemas():
    """Carrega o gerador de schemas (S0) para testar extração da descrição-na-fonte."""
    gs_path = _REPO / ".claude/skills/consultando-sql/scripts/generate_schemas.py"
    spec = importlib.util.spec_from_file_location("generate_schemas_s2mod", gs_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_schemas_s2mod"] = mod
    spec.loader.exec_module(mod)
    return mod


# tabela real, não-core, com tables/*.json e no catálogo — sem business_rules hoje
_TABELA_NAO_CORE = "fretes"

_OVERLAY_FAKE = {
    "table": _TABELA_NAO_CORE,
    "version": "1.1.0",
    "business_rules": [
        "REGRA_TESTE: custo real usa valor_pago",
        "REGRA_TESTE: divergencia = ABS(valor_cte - valor_cotado)",
    ],
    "query_hints": [
        {
            "descricao": "HINT_TESTE pendentes no Odoo",
            "sql": "SELECT * FROM fretes WHERE status='APROVADO' AND lancado_odoo_em IS NULL",
        }
    ],
}


# =====================================================================
# Função pura de merge de overlay
# =====================================================================

class TestMergeOverlayIntoSchema:
    def test_aplica_business_rules_quando_ausente(self):
        schema = {"name": "t", "fields": []}
        out = T._merge_overlay_into_schema(schema, {"business_rules": ["R1"]})
        assert out["business_rules"] == ["R1"]

    def test_nao_sobrescreve_business_rules_existente(self):
        # As 9 core mantêm as regras vindas do schema.json (decisão 2).
        schema = {"name": "carteira", "business_rules": ["CORE"], "fields": []}
        T._merge_overlay_into_schema(schema, {"business_rules": ["OVERLAY"]})
        assert schema["business_rules"] == ["CORE"]

    def test_aplica_query_hints(self):
        schema = {"name": "t", "fields": []}
        hints = [{"descricao": "d", "sql": "SELECT 1"}]
        T._merge_overlay_into_schema(schema, {"query_hints": hints})
        assert schema["query_hints"] == hints

    def test_aplica_lineage_quando_overlay_tem_source_ou_fields(self):
        schema = {"name": "t", "fields": []}
        overlay = {"source": {"primary": {"system": "Odoo"}}, "fields": {"x": {}}}
        T._merge_overlay_into_schema(schema, overlay)
        assert schema["lineage"] == overlay

    def test_overlay_so_regras_nao_cria_lineage(self):
        # overlay puramente de curadoria (sem proveniência) não injeta lineage vazio
        schema = {"name": "t", "fields": []}
        T._merge_overlay_into_schema(schema, {"business_rules": ["R"]})
        assert "lineage" not in schema

    def test_overlay_none_nao_altera(self):
        schema = {"name": "t", "fields": [], "x": 1}
        out = T._merge_overlay_into_schema(schema, None)
        assert out == {"name": "t", "fields": [], "x": 1}

    def test_overlay_vazio_nao_altera(self):
        schema = {"name": "t", "fields": []}
        T._merge_overlay_into_schema(schema, {})
        assert "business_rules" not in schema
        assert "query_hints" not in schema
        assert "lineage" not in schema


# =====================================================================
# SchemaProvider aplica overlay de regras/hints (não só linhagem)
# =====================================================================

class TestSchemaProviderOverlayCuradoria:
    @pytest.fixture
    def provider_com_overlay(self):
        provider = T.SchemaProvider()
        # injeta overlay de curadoria numa tabela real não-core e limpa cache
        provider._overlays[_TABELA_NAO_CORE] = dict(_OVERLAY_FAKE)
        provider._table_cache.pop(_TABELA_NAO_CORE, None)
        return provider

    def test_get_table_schema_inclui_business_rules_do_overlay(self, provider_com_overlay):
        schema = provider_com_overlay.get_table_schema(_TABELA_NAO_CORE)
        assert schema is not None
        assert schema.get("business_rules") == _OVERLAY_FAKE["business_rules"]

    def test_get_table_schema_inclui_query_hints_do_overlay(self, provider_com_overlay):
        schema = provider_com_overlay.get_table_schema(_TABELA_NAO_CORE)
        assert schema.get("query_hints") == _OVERLAY_FAKE["query_hints"]

    def test_get_tables_schema_text_exibe_regras_e_hints(self, provider_com_overlay):
        texto = provider_com_overlay.get_tables_schema_text([_TABELA_NAO_CORE])
        assert "REGRA_TESTE: custo real usa valor_pago" in texto
        assert "HINT_TESTE pendentes no Odoo" in texto

    def test_format_schema_consultar_schema_exibe_regras_e_hints(self, provider_com_overlay):
        _format_schema = _load_format_schema()
        schema = provider_com_overlay.get_table_schema(_TABELA_NAO_CORE)
        texto = _format_schema(schema)
        assert "REGRA_TESTE: custo real usa valor_pago" in texto
        assert "HINT_TESTE pendentes no Odoo" in texto

    def test_core_mantem_business_rules_do_schema_json(self):
        # carteira_principal é core: regras vêm do schema.json mesmo se houver overlay
        provider = T.SchemaProvider()
        provider._overlays["carteira_principal"] = {
            "business_rules": ["NAO_DEVE_APARECER"],
        }
        provider._table_cache.pop("carteira_principal", None)
        schema = provider.get_table_schema("carteira_principal")
        # core tem business_rules do schema.json; overlay não sobrescreve
        assert schema.get("business_rules")
        assert "NAO_DEVE_APARECER" not in schema["business_rules"]


# =====================================================================
# Gate S2 item 1: descrição curada na FONTE (modelo) aparece no schema
# gerado E em consultar_schema. Decisão 1: descrição mora no modelo
# (col.info['description']), extraída automaticamente pelo gerador.
# =====================================================================

class TestDescricaoNaFonteAparece:
    def _modelo_sintetico(self):
        md = MetaData()
        t = Table(
            "tabela_s2_fonte", md,
            Column("id", Integer, primary_key=True),
            Column("campo_curado", String(50),
                   info={"description": "Saldo pendente a faturar (fonte da verdade)"}),
            Column("campo_sem_desc", String(50)),
        )

        class _Model:
            __table__ = t

        return t, _Model

    def test_extract_field_description_le_info_da_fonte(self):
        gs = _load_generate_schemas()
        _t, model = self._modelo_sintetico()
        desc = gs.extract_field_description(model, "campo_curado")
        assert desc == "Saldo pendente a faturar (fonte da verdade)"

    def test_descricao_da_fonte_aparece_no_schema_gerado(self):
        gs = _load_generate_schemas()
        t, model = self._modelo_sintetico()
        schema = gs.extract_table_schema("tabela_s2_fonte", t, model)
        campos = {f["name"]: f for f in schema["fields"]}
        assert campos["campo_curado"]["description"] == \
            "Saldo pendente a faturar (fonte da verdade)"

    def test_descricao_da_fonte_aparece_em_consultar_schema(self):
        gs = _load_generate_schemas()
        t, model = self._modelo_sintetico()
        schema = gs.extract_table_schema("tabela_s2_fonte", t, model)
        texto = _load_format_schema()(schema)
        assert "Saldo pendente a faturar (fonte da verdade)" in texto


# =====================================================================
# Evidência Gate S2 item 2: overlay REAL no disco (fretes) — sem injeção
# =====================================================================

class TestOverlayRealFretes:
    def test_fretes_serve_business_rules_e_query_hints_do_disco(self):
        provider = T.SchemaProvider()
        schema = provider.get_table_schema("fretes")
        assert schema is not None
        assert schema.get("business_rules"), "fretes deve ter business_rules do overlay real"
        assert schema.get("query_hints"), "fretes deve ter query_hints do overlay real"
        # fundamentado: a regra de custo real menciona valor_pago (campo real do schema)
        assert any("valor_pago" in r for r in schema["business_rules"])
        # query_hint estruturado {descricao, sql}
        assert all("descricao" in h and "sql" in h for h in schema["query_hints"])


# =====================================================================
# Invariante 4 / Gate S2 item 4: curadoria NUNCA é materializada no arquivo
# gerado — o gerador não emite business_rules/query_hints (runtime-only),
# logo a idempotência S0 é preservada na presença de overlays.
# =====================================================================

class TestGeradorNaoMaterializaCuradoria:
    def test_extract_table_schema_nao_emite_business_rules_nem_query_hints(self):
        gs = _load_generate_schemas()
        md = MetaData()
        t = Table(
            "tabela_s2_nao_materializa", md,
            Column("id", Integer, primary_key=True),
            Column("valor_pago", String(10)),
        )

        class _M:
            __table__ = t

        schema = gs.extract_table_schema("tabela_s2_nao_materializa", t, _M)
        assert "business_rules" not in schema
        assert "query_hints" not in schema


# =====================================================================
# Cobertura máxima (decisão do usuário): carvia/hora/motos_assai entram no
# model_map do gerador → descrição de TABELA (docstring) deixa de ser genérica.
# Nota (integração S0b+S2): a cobertura, antes via lista manual MODEL_MODULES,
# passou a vir da AUTO-DESCOBERTA dinâmica do S0b (`_discover_model_modules`), que
# varre os pacotes models/ por `__tablename__` — superconjunto da lista manual.
# =====================================================================

class TestGeradorCobreCarviaHoraAssai:
    def test_autodescoberta_cobre_carvia_hora_assai(self):
        gs = _load_generate_schemas()
        mods = gs._discover_model_modules()
        for prefixo in ("app.carvia", "app.hora", "app.motos_assai"):
            assert any(m.startswith(prefixo) for m in mods), \
                f"auto-descoberta não cobriu {prefixo}"
        # hora_tagplus_notificacao_whatsapp: submódulo tagplus (não reexportado no
        # __init__ de hora) é pego pela auto-descoberta varrendo os arquivos do pacote.
        assert any("tagplus" in m for m in mods if m.startswith("app.hora")), \
            "auto-descoberta não cobriu app.hora.models.tagplus"


# =====================================================================
# Bug exposto pela cobertura máxima: extract_class_docstring NÃO pode herdar a
# docstring de db.Model (ex.: AssaiLoja sem docstring vazava "The base class of
# the SQLAlchemy.Model..."). Deve usar a docstring PRÓPRIA da classe.
# =====================================================================

class TestExtractClassDocstringNaoHerda:
    def test_nao_herda_docstring_da_base(self):
        gs = _load_generate_schemas()

        class _Base:
            "Docstring da base que NAO deve vazar para a filha"

        class _Filha(_Base):
            pass  # sem docstring própria

        assert gs.extract_class_docstring(_Filha) == ""

    def test_usa_docstring_propria_quando_existe(self):
        gs = _load_generate_schemas()

        class _Base:
            "Docstring da base"

        class _ComDoc(_Base):
            "Descricao propria da tabela filha"

        assert gs.extract_class_docstring(_ComDoc) == "Descricao propria da tabela filha"


# =====================================================================
# Gate S2 item 3 (guard de não-regressão): amostra de tabelas top-40 por uso
# tem descrição de tabela real + business_rules + query_hints servidos em runtime.
# =====================================================================

class TestGateS2Top40:
    TABELAS = [
        "fretes", "transportadoras", "tabelas_frete", "cidades_atendidas",
        "carvia_operacoes", "carvia_fretes", "carvia_cotacoes",
        "hora_moto_evento", "hora_loja",
        "validacao_nf_po_dfe", "match_nf_po_item",
        "faturamento_produto", "carteira_principal", "separacao",
        "movimentacao_estoque", "embarques", "entregas_monitoradas",
        "agendamentos_entrega", "nf_devolucao", "pedido_compras",
    ]

    def test_top_tabelas_tem_descricao_business_rules_e_query_hints(self):
        p = T.SchemaProvider()
        falhas = []
        for t in self.TABELAS:
            s = p.get_table_schema(t)
            if not s:
                falhas.append(f"{t}: sem schema"); continue
            desc = (s.get("description") or "").strip()
            if not desc or desc.startswith("Tabela "):
                falhas.append(f"{t}: descrição de tabela genérica")
            if not s.get("business_rules"):
                falhas.append(f"{t}: sem business_rules")
            if not s.get("query_hints"):
                falhas.append(f"{t}: sem query_hints")
        assert not falhas, "Gate S2 incompleto: " + "; ".join(falhas)

    def test_query_hints_tem_formato_descricao_sql(self):
        p = T.SchemaProvider()
        for t in self.TABELAS:
            s = p.get_table_schema(t) or {}
            for h in s.get("query_hints", []):
                assert "descricao" in h and "sql" in h, f"{t}: query_hint sem descricao/sql"
