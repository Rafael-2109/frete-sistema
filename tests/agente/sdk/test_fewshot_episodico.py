"""F5.5 PAD-CTX — few-shot episodico condicional no Tier 2.

Quando o turno tem match EXCEPCIONAL (similarity >= AGENT_FEWSHOT_MIN_SIMILARITY)
com uma memoria EPISODICA (correcao / caso em /corrections/ ou /casos/), o
conteudo entra COMPLETO como exemplo (tier="exemplo", cap proprio maior) em vez
do destilado de 300c — exemplo trabalhado vale mais que resumo nesses casos.

DESVIO DECLARADO do plano (5.5 dizia cosine >0,75): a distribuicao REAL do
voyage-4-lite query->doc medida em PROD (2026-06-09, 27 queries) vive em
0.24-0.55 — max observado 0.5520. Threshold 0.75 NUNCA dispararia. Default
calibrado: 0.55 (so match excepcional), configuravel via env.
"""
from datetime import datetime
from types import SimpleNamespace

from app.agente.sdk.memory_injection import (
    FEWSHOT_CONTENT_CAP,
    FEWSHOT_MIN_SIMILARITY,
    TIER2_MEMORY_CHAR_CAP,
    _is_episodic_memory,
    _render_tier2_candidate,
)


def _mem(path="/memories/corrections/caso-x.xml", meta=None, **kw):
    base = dict(
        id=1, path=path, meta=meta, user_id=5,
        source_session_id=None, created_by=None,
        created_at=datetime(2026, 6, 1), updated_at=datetime(2026, 6, 5),
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestIsEpisodicMemory:
    def test_path_corrections(self):
        assert _is_episodic_memory(_mem("/memories/corrections/x.xml"))

    def test_path_casos(self):
        assert _is_episodic_memory(_mem("/memories/empresa/casos/fatura-161-9.xml"))

    def test_kind_correcao(self):
        assert _is_episodic_memory(
            _mem("/memories/empresa/regras/y.xml", meta={"kind": "correcao"})
        )

    def test_heuristica_nao_e_episodica(self):
        assert not _is_episodic_memory(
            _mem("/memories/empresa/heuristicas/z.xml", meta={"kind": "heuristica"})
        )


class TestRenderTier2Candidate:
    def test_match_excepcional_episodico_vira_exemplo_completo(self):
        content = "CASO: fatura CarVia 161-9. " + ("detalhe importante. " * 30)
        assert len(content) > TIER2_MEMORY_CHAR_CAP
        mem = _mem("/memories/corrections/fatura-161-9.xml")
        text = _render_tier2_candidate(mem, content, similarity=0.60)
        assert 'tier="exemplo"' in text
        # exemplo NAO e destilado a 300c — entra (quase) completo
        assert "detalhe importante" in text
        assert len(text) > TIER2_MEMORY_CHAR_CAP + 100

    def test_exemplo_respeita_cap_proprio(self):
        content = "x" * (FEWSHOT_CONTENT_CAP * 3)
        mem = _mem("/memories/corrections/grande.xml")
        text = _render_tier2_candidate(mem, content, similarity=0.60)
        assert len(text) <= FEWSHOT_CONTENT_CAP + 400  # + tag/ponteiro

    def test_match_fraco_episodico_destila_normal(self):
        content = "CASO antigo. " + ("bla " * 200)
        mem = _mem("/memories/corrections/caso-y.xml")
        text = _render_tier2_candidate(
            mem, content, similarity=FEWSHOT_MIN_SIMILARITY - 0.05
        )
        assert 'tier="exemplo"' not in text

    def test_match_forte_nao_episodico_destila_normal(self):
        content = "heuristica enorme. " + ("bla " * 200)
        mem = _mem("/memories/empresa/heuristicas/h.xml",
                   meta={"kind": "heuristica"})
        text = _render_tier2_candidate(mem, content, similarity=0.70)
        assert 'tier="exemplo"' not in text

    def test_fallback_sem_similarity_destila_normal(self):
        content = "qualquer coisa longa. " + ("bla " * 200)
        mem = _mem("/memories/corrections/caso-z.xml")
        text = _render_tier2_candidate(mem, content, similarity=0.0)
        assert 'tier="exemplo"' not in text
