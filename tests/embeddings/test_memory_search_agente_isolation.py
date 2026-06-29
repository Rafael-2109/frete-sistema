"""F2 fatia2/E01 — busca semantica de memorias isola por agente (web|lojas).

A materializacao (memory_injection._load Tier 2, linha ~1427) JA filtra
AgentMemory.agente == agente_id (fatia 1/M05) — o fail-closed end-to-end ja
esta garantido la. Este E01 e a 2a camada/otimizacao: o JOIN pgvector e o
fallback ORM nao devem nem RETORNAR (gastar slot do top-K com) memoria de
outro agente.

Espelha o padrao de tests/embeddings/test_memory_search_cold_filter.py
(vetor unitario + skip honesto conforme pgvector disponivel).
"""
import pytest

from app import create_app, db
from app.agente.models import AgentMemory
from app.embeddings.models import AgentMemoryEmbedding


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app


_PREFIX = "/memories/empresa/heuristicas/_pytest_agiso"


def _cleanup():
    mem_ids = [
        m.id for m in AgentMemory.query.filter(
            AgentMemory.path.like(f"{_PREFIX}%")
        ).all()
    ]
    if mem_ids:
        AgentMemoryEmbedding.query.filter(
            AgentMemoryEmbedding.memory_id.in_(mem_ids)
        ).delete(synchronize_session=False)
        AgentMemory.query.filter(AgentMemory.id.in_(mem_ids)).delete(
            synchronize_session=False
        )
    db.session.commit()


@pytest.fixture
def par_web_lojas(app):
    """1 memoria empresa 'web' e 1 'lojas', MESMO embedding (vetor unitario) —
    a busca com query identica retornaria as duas com similarity 1.0; o filtro
    de agente deve excluir a do outro agente."""
    _cleanup()
    dim = 1024
    vec = [1.0] + [0.0] * (dim - 1)

    from app.embeddings.config import VOYAGE_MEMORY_MODEL
    web = AgentMemory(user_id=0, path=f"{_PREFIX}/web.xml", content="c",
                      agente="web", is_directory=False)
    lojas = AgentMemory(user_id=0, path=f"{_PREFIX}/lojas.xml", content="c",
                        agente="lojas", is_directory=False)
    db.session.add_all([web, lojas])
    db.session.flush()
    for mem in (web, lojas):
        db.session.add(AgentMemoryEmbedding(
            memory_id=mem.id, user_id=0, path=mem.path,
            texto_embedado=f"[{mem.path}]", embedding=vec,
            model_used=VOYAGE_MEMORY_MODEL,
        ))
    db.session.commit()

    yield {"web": web.id, "lojas": lojas.id, "vec": vec}
    _cleanup()


def test_pgvector_isola_por_agente(app, par_web_lojas):
    from app.embeddings.service import EmbeddingService

    svc = EmbeddingService()
    if not svc._is_pgvector_available():
        pytest.skip("pgvector indisponivel no banco de teste")

    res = svc._search_pgvector_memories(
        par_web_lojas["vec"], user_id=0, limit=50, min_similarity=0.9,
        agente_id="lojas",
    )
    ids = {r["memory_id"] for r in res}
    assert par_web_lojas["lojas"] in ids
    assert par_web_lojas["web"] not in ids, (
        "memoria 'web' vazou na busca semantica 'lojas' (JOIN m.agente)"
    )


def test_fallback_isola_por_agente(app, par_web_lojas):
    """Fallback so roda em banco SEM pgvector (search_memories checa
    _is_pgvector_available antes). Skip honesto em banco pgvector."""
    from app.embeddings.service import EmbeddingService

    svc = EmbeddingService()
    if svc._is_pgvector_available():
        pytest.skip("banco de teste tem pgvector — fallback e caminho morto aqui")

    res = svc._search_fallback_memories(
        par_web_lojas["vec"], user_id=0, limit=50, min_similarity=0.9,
        agente_id="lojas",
    )
    ids = {r["memory_id"] for r in res}
    assert par_web_lojas["lojas"] in ids
    assert par_web_lojas["web"] not in ids
