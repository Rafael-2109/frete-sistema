"""
Busca semantica de entidades financeiras (fornecedores e clientes).

Funcao reutilizavel que busca entidades por similaridade semantica
em financial_entity_embeddings via pgvector (ou fallback Python).

Uso:
    from app.embeddings.entity_search import buscar_entidade_semantica

    # Buscar fornecedor por nome truncado/abreviado
    results = buscar_entidade_semantica("MEZZANI ALIM", entity_type='supplier')
    # Retorna "MEZZANI ALIMENTOS LTDA" se existir

    # Buscar cliente
    results = buscar_entidade_semantica("ABC FRETES", entity_type='customer')

    # Buscar em ambos
    results = buscar_entidade_semantica("VALE SUL TRANSP", entity_type='all')
"""

import logging
from typing import List, Dict

from app.embeddings.config import EMBEDDINGS_ENABLED

logger = logging.getLogger(__name__)


def buscar_entidade_semantica(
    nome: str,
    entity_type: str = 'supplier',
    limite: int = 5,
    min_similarity: float = 0.40,
) -> List[Dict]:
    """
    Busca semantica de entidades financeiras.

    Args:
        nome: Nome do fornecedor/cliente (pode ser truncado/abreviado)
        entity_type: 'supplier', 'customer', ou 'all'
        limite: Maximo de resultados
        min_similarity: Threshold minimo de similaridade (0-1)

    Returns:
        Lista de dicts ordenados por similarity (desc):
        {
            'cnpj_raiz': str,
            'cnpj_completo': str,
            'nome': str,
            'similarity': float,
            'entity_type': str,
        }
    """
    if not nome or not nome.strip():
        return []

    if not EMBEDDINGS_ENABLED:
        return []

    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()

        return svc.search_entities(
            query=nome,
            entity_type=entity_type,
            limit=limite,
            min_similarity=min_similarity,
        )

    except Exception as e:
        logger.warning(f"[entity_search] Busca semantica falhou: {e}")
        return []
