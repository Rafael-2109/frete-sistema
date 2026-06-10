"""Migração do retrieval de memórias para voyage-4-large (decisão Rafael 2026-06-10).

Base empírica (relatorios/estudo_contexto_boot_2026-06-09/
precision_at_k_baseline_2026-06-10.md): no MESMO corpus e 20 queries reais,
large@0.45 = 0.842 vs lite@0.45 = 0.558 de precision@4 (+50%); @0.40 large
cobre 18/20 turnos com 0.673.

Desenho da migração (cirúrgico — só o que foi MEDIDO muda):
- VOYAGE_MEMORY_MODEL (default voyage-4-large) governa SÓ o retrieval de
  memórias: coluna `embedding` + query da busca. DEDUP permanece no default
  (lite) — threshold 0.85/0.80 do dedup foi calibrado no lite e não foi medido
  no large.
- A busca filtra `model_used = VOYAGE_MEMORY_MODEL`: durante a transição
  (deploy → reindex), NUNCA compara query large com doc lite (cross-model
  cosine é ruído — mesma lição do threshold 0.55).
- Threshold default da injeção recalibrado 0.45 → 0.40 (medição do large).
"""
from unittest.mock import patch

import pytest

from app import create_app, db
from app.agente.models import AgentMemory
from app.embeddings.models import AgentMemoryEmbedding


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


class TestConfig:
    def test_voyage_memory_model_default_large(self):
        from app.embeddings.config import VOYAGE_MEMORY_MODEL
        assert VOYAGE_MEMORY_MODEL == "voyage-4-large"

    def test_threshold_injecao_default_040(self, monkeypatch):
        # delenv: o DEFAULT do codigo e o contrato aqui (env de PROD/local
        # pode legitimamente sobrescrever — foi o proprio bug do 0.55)
        monkeypatch.delenv("AGENT_MEMORY_MIN_SIMILARITY", raising=False)
        import importlib
        import app.agente.config.feature_flags as ff
        importlib.reload(ff)
        assert ff.MEMORY_INJECTION_MIN_SIMILARITY == pytest.approx(0.40)
        # restaurar estado do modulo p/ demais testes
        importlib.reload(ff)


class TestSearchUsaMemoryModel:
    def test_query_embedada_com_memory_model(self, app):
        from app.embeddings.service import EmbeddingService
        from app.embeddings.config import VOYAGE_MEMORY_MODEL

        svc = EmbeddingService()
        with patch.object(svc, "_safe_embed_query", return_value=None) as m:
            svc.search_memories("qualquer pergunta", user_id=1)
        m.assert_called_once()
        assert m.call_args.kwargs.get("model") == VOYAGE_MEMORY_MODEL


_PREFIX = "/memories/empresa/heuristicas/_pytest_modelmig"


def _cleanup():
    mem_ids = [m.id for m in AgentMemory.query.filter(
        AgentMemory.path.like(f"{_PREFIX}%")).all()]
    if mem_ids:
        AgentMemoryEmbedding.query.filter(
            AgentMemoryEmbedding.memory_id.in_(mem_ids)
        ).delete(synchronize_session=False)
        AgentMemory.query.filter(AgentMemory.id.in_(mem_ids)).delete(
            synchronize_session=False)
    db.session.commit()


@pytest.fixture
def par_modelos(app):
    """2 memórias quentes com o MESMO vetor, uma indexada no modelo alvo e
    outra num modelo legado — a busca deve retornar SÓ a do modelo alvo."""
    from app.embeddings.config import VOYAGE_MEMORY_MODEL
    _cleanup()
    dim = 1024
    vec = [1.0] + [0.0] * (dim - 1)

    alvo = AgentMemory.create_file(0, f"{_PREFIX}/alvo.xml", "doc modelo alvo")
    legado = AgentMemory.create_file(0, f"{_PREFIX}/legado.xml", "doc modelo legado")
    db.session.flush()
    for mem, modelo in ((alvo, VOYAGE_MEMORY_MODEL), (legado, "voyage-4-lite-LEGADO")):
        db.session.add(AgentMemoryEmbedding(
            memory_id=mem.id, user_id=0, path=mem.path,
            texto_embedado=f"[{mem.path}]", embedding=vec, model_used=modelo,
        ))
    db.session.commit()
    yield {"alvo": alvo.id, "legado": legado.id, "vec": vec}
    _cleanup()


class TestFiltroModelUsed:
    def test_pgvector_so_retorna_modelo_alvo(self, app, par_modelos):
        from app.embeddings.service import EmbeddingService

        svc = EmbeddingService()
        if not svc._is_pgvector_available():
            pytest.skip("pgvector indisponivel")
        results = svc._search_pgvector_memories(
            par_modelos["vec"], user_id=0, limit=50, min_similarity=0.9)
        ids = {r["memory_id"] for r in results}
        assert par_modelos["alvo"] in ids
        assert par_modelos["legado"] not in ids, (
            "doc indexado em modelo legado NAO pode casar com query do modelo "
            "alvo (cross-model cosine e ruido)")
