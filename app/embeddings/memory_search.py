"""
Busca semantica em memorias persistentes do agente.

Funcao reutilizavel que busca memorias por similaridade semantica
em agent_memory_embeddings via pgvector (ou fallback Python).

Uso:
    from app.embeddings.memory_search import buscar_memorias_semantica

    results = buscar_memorias_semantica(
        "preferencia de formato", user_id=1
    )
    # Retorna /memories/preferences.xml e memorias relevantes
"""

import logging
from typing import List, Dict

from app.embeddings.config import EMBEDDINGS_ENABLED, MEMORY_SEMANTIC_SEARCH

logger = logging.getLogger(__name__)


def buscar_memorias_semantica(
    query: str,
    user_id: int,
    limite: int = 10,
    min_similarity: float = 0.30,
) -> List[Dict]:
    """
    Busca semantica em memorias persistentes do usuario.

    Args:
        query: Texto de busca (tema, pergunta, contexto)
        user_id: ID do usuario (filtro obrigatorio)
        limite: Maximo de resultados
        min_similarity: Threshold minimo de similaridade (0-1)

    Returns:
        Lista de dicts ordenados por similarity (desc):
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

    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()

        return svc.search_memories(
            query=query,
            user_id=user_id,
            limit=limite,
            min_similarity=min_similarity,
        )

    except Exception as e:
        logger.warning(f"[memory_search] Busca semantica falhou: {e}")
        return []
