"""FRENTE 1 (plano 2026-06-10-engenharia-memoria-rerank-write-quality) — escala
de rerank vs cosine nos gates + observabilidade do rerank.

Contexto medido (A/B 2026-06-10, 20 turnos reais PROD, judges Sonnet):
- rerank-2.5-lite melhora precision@4 de 0.388 -> 0.463 (+19%) sem perder
  cobertura — flag MEMORY_RERANKING_ENABLED permanece ON por medida.
- MAS a escala do rerank_score (~0.5-0.75) NAO e comparavel a escala cosine:
  60% dos top-4 rerank passam 0.55 vs 27% no cosine. Gates calibrados na
  distribuicao cosine (FEWSHOT_MIN_SIMILARITY=0.55 = "match excepcional")
  NAO podem receber rerank_score — receber dispara few-shot 2.2x mais que o
  calibrado (1200c em vez de 300c por memoria episodica).

Bug de intencao corrigido: _pass1_similarity (comentado como "similarity
CRUA") recebia rerank_score via sim_map. Fix: _build_similarity_maps separa
sim_map (ordenacao/composite — prefere rerank) de cosine_map (gates).
"""
import logging

import pytest


# ======================================================================
# _build_similarity_maps — duas escalas, dois mapas
# ======================================================================

class TestBuildSimilarityMaps:
    def _filtered(self):
        return [
            {'memory_id': 1, 'similarity': 0.45, 'rerank_score': 0.71},
            {'memory_id': 2, 'similarity': 0.52},  # sem rerank (fallback)
            {'memory_id': 3, 'similarity': 0.41, 'rerank_score': 0.38},
        ]

    def test_sim_map_prefere_rerank_score(self):
        from app.agente.sdk.memory_injection import _build_similarity_maps
        sim_map, _ = _build_similarity_maps(self._filtered())
        assert sim_map[1] == 0.71
        assert sim_map[2] == 0.52  # sem rerank -> cosine
        assert sim_map[3] == 0.38

    def test_cosine_map_sempre_escala_cosine(self):
        from app.agente.sdk.memory_injection import _build_similarity_maps
        _, cosine_map = _build_similarity_maps(self._filtered())
        assert cosine_map[1] == 0.45  # NUNCA o rerank_score 0.71
        assert cosine_map[2] == 0.52
        assert cosine_map[3] == 0.41

    def test_vazio(self):
        from app.agente.sdk.memory_injection import _build_similarity_maps
        sim_map, cosine_map = _build_similarity_maps([])
        assert sim_map == {} and cosine_map == {}


# ======================================================================
# buscar_memorias_semantica — observabilidade do rerank (item 1.5)
# ======================================================================

class _FakeSvc:
    """EmbeddingService fake: 6 candidatos cosine; rerank inverte a ordem."""

    def search_memories(self, query, user_id, limit, min_similarity, agente_id='web'):
        return [
            {'memory_id': i, 'path': f'/memories/m{i}.xml',
             'texto_embedado': f'texto {i}', 'similarity': round(0.50 - i * 0.01, 2)}
            for i in range(6)
        ]

    def rerank(self, query, documents, top_k):
        n = min(top_k, len(documents))
        return [
            {'index': len(documents) - 1 - i, 'document': documents[len(documents) - 1 - i],
             'relevance_score': round(0.90 - i * 0.05, 2)}
            for i in range(n)
        ]


@pytest.fixture
def fake_svc(monkeypatch):
    monkeypatch.setattr('app.embeddings.service.EmbeddingService', _FakeSvc)
    monkeypatch.setattr('app.embeddings.config.MEMORY_RERANKING_ENABLED', True)
    monkeypatch.setattr('app.embeddings.memory_search.EMBEDDINGS_ENABLED', True)
    monkeypatch.setattr('app.embeddings.memory_search.MEMORY_SEMANTIC_SEARCH', True)


class TestRerankObservabilidade:
    def test_rerank_reordena_e_popula_rerank_score(self, fake_svc):
        from app.embeddings.memory_search import buscar_memorias_semantica
        res = buscar_memorias_semantica("query teste", user_id=5, limite=4)
        assert len(res) == 4
        # rerank inverteu: primeiro resultado = ultimo candidato cosine
        assert res[0]['memory_id'] == 5
        assert res[0]['rerank_score'] == 0.90
        # similarity cosine ORIGINAL preservada lado a lado
        assert res[0]['similarity'] == 0.45

    def test_log_info_com_latencia(self, fake_svc, caplog):
        """1.5: validar rerank em PROD pelos logs exige INFO (debug e
        invisivel) com latencia em ms."""
        from app.embeddings.memory_search import buscar_memorias_semantica
        with caplog.at_level(logging.INFO, logger='app.embeddings.memory_search'):
            buscar_memorias_semantica("query teste", user_id=5, limite=4)
        rerank_logs = [r for r in caplog.records
                       if '[memory_search]' in r.message and 'rerank' in r.message]
        assert rerank_logs, "esperado log INFO '[memory_search] rerank ...'"
        msg = rerank_logs[0].message
        assert 'ms' in msg, f"log deve conter latencia em ms: {msg}"
