"""
Singleton do Voyage AI client.

Uso:
    from app.embeddings.client import get_voyage_client
    vo = get_voyage_client()
    result = vo.embed(["texto"], model="voyage-4-lite", input_type="document")
"""

import voyageai

from app.embeddings.config import VOYAGE_API_KEY


# Singleton — inicializado sob demanda
_client = None


def get_voyage_client() -> voyageai.Client:
    """
    Retorna instancia singleton do Voyage AI client.

    Raises:
        ValueError: Se VOYAGE_API_KEY nao estiver configurada
    """
    global _client

    if _client is not None:
        return _client

    if not VOYAGE_API_KEY:
        raise ValueError(
            "VOYAGE_API_KEY nao configurada. "
            "Defina a variavel de ambiente VOYAGE_API_KEY com sua chave da Voyage AI."
        )

    _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def reset_client() -> None:
    """
    Reseta o singleton (util para testes).
    """
    global _client
    _client = None
