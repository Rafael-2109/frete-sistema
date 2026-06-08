"""Testes determinísticos do indexer do catalogo de tabelas (S1, Parte C).

Cobre collect_table_catalog (sem DB/Voyage): le o catalog.json real e produz
1 registro por tabela com content_hash ESTAVEL (idempotencia da reindexacao —
so re-embeda o que mudou). A indexacao em si (embed + upsert) depende de
Voyage/pgvector e e exercida em PROD/scheduler, nao no gate determinístico.

Invariante 6 do MASTER: pytest determinístico, SEM evals LLM.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_INDEXER = _REPO / "app/embeddings/indexers/table_catalog_indexer.py"


def _load():
    spec = importlib.util.spec_from_file_location("table_catalog_indexer_mod", _INDEXER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["table_catalog_indexer_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


tci = _load()


class TestCollect:
    def test_uma_entry_por_tabela(self):
        entries = tci.collect_table_catalog()
        nomes = [e["table_name"] for e in entries]
        assert len(nomes) == len(set(nomes)), "table_name deve ser unico (1 linha/tabela)"
        assert len(entries) > 200, "deveria cobrir o catalogo (300+ tabelas)"

    def test_entry_tem_campos_obrigatorios(self):
        entries = tci.collect_table_catalog()
        for e in entries[:5]:
            assert e["table_name"]
            assert e["texto_embedado"]
            assert "content_hash" in e and len(e["content_hash"]) == 32  # md5 hex

    def test_texto_embedado_inclui_nome_e_dominio(self):
        entries = {e["table_name"]: e for e in tci.collect_table_catalog()}
        cp = entries["carteira_principal"]
        assert "carteira_principal" in cp["texto_embedado"]
        assert "Carteira" in cp["texto_embedado"]  # dominio
        assert cp["dominio"] == "Carteira"

    def test_content_hash_deterministico(self):
        a = tci.collect_table_catalog()
        b = tci.collect_table_catalog()
        ha = {e["table_name"]: e["content_hash"] for e in a}
        hb = {e["table_name"]: e["content_hash"] for e in b}
        assert ha == hb

    def test_content_hash_muda_com_o_texto(self):
        h1 = tci._content_hash(tci._build_texto_embedado("t", "Dom", "desc A", "a, b"))
        h2 = tci._content_hash(tci._build_texto_embedado("t", "Dom", "desc B", "a, b"))
        assert h1 != h2

    def test_inclui_tabelas_admin(self):
        # tabelas_admin tambem sao indexadas (visibilidade filtrada na busca)
        nomes = {e["table_name"] for e in tci.collect_table_catalog()}
        assert "table_catalog_embeddings" in nomes  # admin_only, mas indexada


class TestModeloDedicado:
    """voyage-4-large dedicado ao catalogo (S1), ISOLADO do default global.
    A/B real: top-3 coloquial 93% (large) vs 73% (lite). Source-checks
    deterministicos (sem app/DB)."""

    def test_config_tem_modelo_dedicado_large(self):
        cfg = (_REPO / "app/embeddings/config.py").read_text(encoding="utf-8")
        assert "VOYAGE_TABLE_CATALOG_MODEL" in cfg
        assert "voyage-4-large" in cfg
        # default global NAO mudou (continua lite) -> isolamento
        assert 'VOYAGE_DEFAULT_MODEL = os.environ.get("VOYAGE_DEFAULT_MODEL", "voyage-4-lite")' in cfg

    def test_indexer_usa_modelo_dedicado_e_reindexa_ao_trocar(self):
        idx = (_REPO / "app/embeddings/indexers/table_catalog_indexer.py").read_text(encoding="utf-8")
        assert "VOYAGE_TABLE_CATALOG_MODEL" in idx
        assert "model=modelo" in idx                 # embeda com o modelo dedicado
        assert "model_used = :modelo" in idx         # re-embeda linhas de modelo antigo

    def test_search_usa_mesmo_modelo(self):
        svc = (_REPO / "app/embeddings/service.py").read_text(encoding="utf-8")
        # query e documentos no mesmo espaco vetorial
        assert "VOYAGE_TABLE_CATALOG_MODEL" in svc
        assert "_safe_embed_query(query, model=VOYAGE_TABLE_CATALOG_MODEL)" in svc


class TestFreshnessScheduler:
    """Freshness (decisao 1a S1): o indice semantico reindexa no gatilho diario de
    reindexacao (mesmo lugar dos outros embeddings), nao no hook do S0 — que nao
    toca banco. content_hash garante que so re-embeda o que mudou."""

    def test_step_acoplado_ao_scheduler(self):
        src = (_REPO / "app/scheduler/reindexacao_embeddings.py").read_text(encoding="utf-8")
        assert "table_catalog_indexer" in src
        assert "collect_table_catalog" in src
        assert "index_table_catalog" in src
        assert "total_steps = 11" in src  # 10 -> 11 com o novo modulo
