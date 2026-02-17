"""
Busca semantica em turns de sessoes passadas do agente.

Funcao reutilizavel que busca pares user+assistant por similaridade
semantica em session_turn_embeddings via pgvector (ou fallback Python).

Uso:
    from app.embeddings.session_search import buscar_sessoes_semantica

    results = buscar_sessoes_semantica(
        "problema com entrega atrasada", user_id=1
    )
    # Retorna sessoes que discutiram atrasos de entrega
"""

import logging
from typing import List, Dict

from app.embeddings.config import EMBEDDINGS_ENABLED, SESSION_SEMANTIC_SEARCH

logger = logging.getLogger(__name__)


def buscar_sessoes_semantica(
    query: str,
    user_id: int,
    limite: int = 10,
    min_similarity: float = 0.35,
) -> List[Dict]:
    """
    Busca semantica em turns de sessoes passadas do usuario.

    Args:
        query: Texto de busca (pergunta, tema, situacao)
        user_id: ID do usuario (filtro obrigatorio)
        limite: Maximo de resultados
        min_similarity: Threshold minimo de similaridade (0-1)

    Returns:
        Lista de dicts ordenados por similarity (desc):
        {
            'session_id': str,
            'turn_index': int,
            'user_content': str,
            'assistant_summary': str,
            'session_title': str,
            'session_created_at': str (ISO),
            'similarity': float,
        }
    """
    if not query or not query.strip():
        return []

    if not EMBEDDINGS_ENABLED or not SESSION_SEMANTIC_SEARCH:
        return []

    if not user_id:
        return []

    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()

        return svc.search_session_turns(
            query=query,
            user_id=user_id,
            limit=limite,
            min_similarity=min_similarity,
        )

    except Exception as e:
        logger.warning(f"[session_search] Busca semantica falhou: {e}")
        return []
