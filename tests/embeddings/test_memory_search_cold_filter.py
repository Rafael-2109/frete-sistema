"""F5.4 PAD-CTX — busca semantica de memorias NAO retorna memorias frias.

Gap diagnosticado em PROD (2026-06-09): memorias `_archived_*` tem is_cold=true
em agent_memories MAS o embedding permanece ativo em agent_memory_embeddings —
a busca pgvector nao filtrava cold e desperdicava slots do top-K com memorias
depreciadas (3 de 10 no caso real da query "Transforme em excel ... NF da
Carvia"). O filtro pos-retrieval do memory_injection descartava depois, mas o
slot ja tinha sido consumido — e callers como a deteccao de conflito recebiam
lixo.

Fix: _search_pgvector_memories e _search_fallback_memories excluem memorias
com agent_memories.is_cold = true (JOIN logico via memory_id).
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


_PREFIX = "/memories/empresa/heuristicas/_pytest_coldfilter"
_USER = 0  # empresa


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
def par_quente_fria(app):
    """Cria 1 memoria QUENTE e 1 FRIA, ambas com o MESMO embedding (vetor
    unitario na dimensao 0) — a busca com query identica retornaria as duas
    com similarity 1.0; o filtro de cold deve excluir a fria."""
    _cleanup()
    dim = 1024
    vec = [1.0] + [0.0] * (dim - 1)

    quente = AgentMemory.create_file(_USER, f"{_PREFIX}/quente.xml", "conteudo quente")
    fria = AgentMemory.create_file(_USER, f"{_PREFIX}/fria.xml", "conteudo frio")
    fria.is_cold = True
    db.session.flush()

    # model_used DEVE ser o modelo de memorias vigente — a busca filtra
    # model_used = VOYAGE_MEMORY_MODEL (migracao 2026-06-10)
    from app.embeddings.config import VOYAGE_MEMORY_MODEL
    for mem in (quente, fria):
        db.session.add(AgentMemoryEmbedding(
            memory_id=mem.id,
            user_id=_USER,
            path=mem.path,
            texto_embedado=f"[{mem.path}]: {mem.content}",
            embedding=vec,
            model_used=VOYAGE_MEMORY_MODEL,
        ))
    db.session.commit()

    yield {"quente": quente.id, "fria": fria.id, "vec": vec}
    _cleanup()


def test_busca_pgvector_exclui_memoria_fria(app, par_quente_fria):
    from app.embeddings.service import EmbeddingService

    svc = EmbeddingService()
    if not svc._is_pgvector_available():
        pytest.skip("pgvector indisponivel no banco de teste")

    results = svc._search_pgvector_memories(
        par_quente_fria["vec"], user_id=_USER, limit=50, min_similarity=0.9,
    )
    ids = {r["memory_id"] for r in results}
    assert par_quente_fria["quente"] in ids
    assert par_quente_fria["fria"] not in ids, (
        "memoria is_cold=true NAO pode aparecer na busca semantica"
    )


def test_busca_fallback_exclui_memoria_fria(app, par_quente_fria):
    """Fallback so roda em banco SEM pgvector (search_memories checa
    _is_pgvector_available antes). Em banco pgvector o embedding volta como
    vector nativo e json.loads falha por design — skip honesto."""
    from app.embeddings.service import EmbeddingService

    svc = EmbeddingService()
    if svc._is_pgvector_available():
        pytest.skip("banco de teste tem pgvector — fallback e caminho morto aqui")

    results = svc._search_fallback_memories(
        par_quente_fria["vec"], user_id=_USER, limit=50, min_similarity=0.9,
    )
    ids = {r["memory_id"] for r in results}
    assert par_quente_fria["quente"] in ids
    assert par_quente_fria["fria"] not in ids
