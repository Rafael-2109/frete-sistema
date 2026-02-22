"""
Busca semantica de rotas e templates do sistema.

Funcao reutilizavel que busca rotas/templates por similaridade semantica
em route_template_embeddings via pgvector (ou fallback Python).

Uso:
    from app.embeddings.route_template_search import search_routes

    # Buscar tela por nome
    results = search_routes("contas a pagar")
    # Retorna rota /financeiro/contas-pagar/ com template e menu

    # Buscar API
    results = search_routes("filtrar fretes", tipo="rota_api")

    # Buscar por conceito
    results = search_routes("onde vejo entregas")
"""

import logging
from typing import Dict, List, Optional

from app.embeddings.config import EMBEDDINGS_ENABLED, ROUTE_TEMPLATE_SEMANTIC_SEARCH

logger = logging.getLogger(__name__)


def search_routes(
    query: str,
    tipo: Optional[str] = None,
    limit: int = 5,
    min_similarity: Optional[float] = None,
) -> List[Dict]:
    """
    Busca semantica em rotas e templates.

    Args:
        query: Texto de busca ("contas a pagar", "tela de extratos", etc.)
        tipo: Filtro opcional - 'rota_template' ou 'rota_api'
        limit: Maximo de resultados
        min_similarity: Score minimo (0-1). Default: THRESHOLD_ROUTE_TEMPLATE

    Returns:
        Lista de dicts ordenados por similarity (desc):
        {
            'tipo': str,
            'blueprint_name': str,
            'function_name': str,
            'url_path': str,
            'http_methods': str,
            'template_path': str | None,
            'menu_path': str | None,
            'permission_decorator': str | None,
            'source_file': str,
            'docstring': str | None,
            'ajax_endpoints': str | None,
            'similarity': float,
        }
    """
    if not query or not query.strip():
        return []

    if not EMBEDDINGS_ENABLED or not ROUTE_TEMPLATE_SEMANTIC_SEARCH:
        return []

    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()

        return svc.search_routes(
            query=query,
            tipo=tipo,
            limit=limit,
            min_similarity=min_similarity,
        )

    except Exception as e:
        logger.warning(f"[route_template_search] Busca semantica falhou: {e}")
        return []
