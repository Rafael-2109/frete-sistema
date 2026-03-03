"""
Busca semantica em memorias persistentes do agente.

Funcao reutilizavel que busca memorias por similaridade semantica
em agent_memory_embeddings via pgvector (ou fallback Python).

Pipeline (T3-2): embed query → retrieve top-N → rerank (opcional) → top-K

Uso:
    from app.embeddings.memory_search import buscar_memorias_semantica

    results = buscar_memorias_semantica(
        "preferencia de formato", user_id=1
    )
    # Retorna /memories/preferences.xml e memorias relevantes
"""

import logging
from typing import List, Dict

from app.embeddings.config import EMBEDDINGS_ENABLED, MEMORY_SEMANTIC_SEARCH, THRESHOLD_MEMORY

logger = logging.getLogger(__name__)


def buscar_memorias_semantica(
    query: str,
    user_id: int,
    limite: int = 10,
    min_similarity: float | None = None,
) -> List[Dict]:
    """
    Busca semantica em memorias persistentes do usuario.

    Pipeline:
    1. Embedding da query via Voyage AI
    2. Busca vetorial top-N (N = limite*2 ou 20)
    3. Reranking via Voyage rerank-2.5-lite (se MEMORY_RERANKING_ENABLED)
    4. Retorna top-K (K = limite)

    Args:
        query: Texto de busca (tema, pergunta, contexto)
        user_id: ID do usuario (filtro obrigatorio)
        limite: Maximo de resultados finais
        min_similarity: Threshold minimo de similaridade (0-1).
            Default: THRESHOLD_MEMORY (0.40) de embeddings/config.py

    Returns:
        Lista de dicts ordenados por relevancia (desc):
        {
            'memory_id': int,
            'path': str,
            'texto_embedado': str,
            'similarity': float,
        }
    """
    if not query or not query.strip():
        return []

    if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
        return []

    if not user_id:
        return []

    # GAP 6: Default centralizado em THRESHOLD_MEMORY (0.40) de config.py
    if min_similarity is None:
        min_similarity = THRESHOLD_MEMORY

    try:
        from app.embeddings.service import EmbeddingService
        from app.embeddings.config import MEMORY_RERANKING_ENABLED
        svc = EmbeddingService()

        # T3-2: Over-fetch para reranking
        fetch_limit = max(limite * 2, 20) if MEMORY_RERANKING_ENABLED else limite

        results = svc.search_memories(
            query=query,
            user_id=user_id,
            limit=fetch_limit,
            min_similarity=min_similarity,
        )

        if not results:
            return []

        # T3-2: Reranking seletivo
        if MEMORY_RERANKING_ENABLED and len(results) > 1:
            try:
                documents = [r['texto_embedado'] for r in results]
                reranked = svc.rerank(
                    query=query,
                    documents=documents,
                    top_k=limite,
                )

                if reranked:
                    # Reconstruir resultados na nova ordem
                    reranked_results = []
                    for item in reranked:
                        idx = item["index"]
                        if idx < len(results):
                            result = results[idx].copy()
                            # Manter similarity original, adicionar rerank_score
                            result["rerank_score"] = item["relevance_score"]
                            reranked_results.append(result)

                    logger.debug(
                        f"[memory_search] Reranked {len(results)} → {len(reranked_results)} "
                        f"memorias para user_id={user_id}"
                    )
                    return reranked_results[:limite]

            except Exception as rerank_err:
                # Fallback: usar resultados sem reranking
                logger.warning(f"[memory_search] Rerank falhou (usando ordem original): {rerank_err}")

        return results[:limite]

    except Exception as e:
        logger.warning(f"[memory_search] Busca semantica falhou: {e}")
        return []
