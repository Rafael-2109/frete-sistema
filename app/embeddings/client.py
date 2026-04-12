"""
Singleton do Voyage AI client com retry e normalizacao.

Uso:
    from app.embeddings.client import get_voyage_client, normalize_for_embedding
    vo = get_voyage_client()
    result = vo.embed(["texto"], model="voyage-4-lite", input_type="document")
"""

import logging
import time
import unicodedata
from typing import List, Optional

import voyageai

from app.embeddings.config import VOYAGE_API_KEY


logger = logging.getLogger(__name__)

# Singleton — inicializado sob demanda
_client = None

# Retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]  # Backoff exponencial
REQUEST_TIMEOUT = 30  # segundos


class EmbeddingUnavailableError(RuntimeError):
    """
    Raised when Voyage AI is unreachable due to external blocking (WAF/CDN 403,
    network partition, rate limit from edge) — NOT when auth or payload is wrong.

    Herda de RuntimeError para manter compatibilidade com callers antigos que
    fazem `except RuntimeError`. Callers no hot-path (chat/bot) devem capturar
    essa exceção e pular a busca semantica, caindo em fallback ILIKE/regex.
    """
    pass


def _is_edge_block(err: Exception) -> bool:
    """
    Detecta se o erro veio de bloqueio de edge (Cloudflare/WAF na frente da
    Voyage) em vez de um erro legitimo da API (auth, payload, rate legit).

    Heuristica: mensagem de erro contem HTML (`<!doctype`, `<html`) ou
    `403`/`Forbidden` textual. API Voyage legitima sempre retorna JSON.
    """
    msg = str(err).lower()
    html_markers = ('<!doctype', '<html', '<title>', '403 forbidden')
    return any(m in msg for m in html_markers) or (
        '403' in msg and 'forbidden' in msg
    )


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

    _client = voyageai.Client(
        api_key=VOYAGE_API_KEY,
        max_retries=MAX_RETRIES,
        timeout=REQUEST_TIMEOUT,
    )
    return _client


def reset_client() -> None:
    """
    Reseta o singleton (util para testes).
    """
    global _client
    _client = None


def embed_with_retry(
    texts: List[str],
    model: str,
    input_type: str = "document",
    output_dimension: Optional[int] = None,
) -> List[List[float]]:
    """
    Wrapper de embed() com retry manual e backoff exponencial.

    O client Voyage AI ja tem retry interno, mas este wrapper
    adiciona tratamento extra para falhas de rede/timeout.

    Args:
        texts: Lista de textos para embeddar
        model: Modelo Voyage AI
        input_type: "document" ou "query"
        output_dimension: Dimensao do embedding (Matryoshka)

    Returns:
        Lista de embeddings

    Raises:
        EmbeddingUnavailableError: Se o erro indicar bloqueio externo
            (WAF/CDN 403 HTML) — callers no hot-path devem capturar e pular
            a busca semantica.
        RuntimeError: Outros erros (auth, payload invalido, server 5xx).
    """
    vo = get_voyage_client()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            kwargs = {
                "model": model,
                "input_type": input_type,
            }
            if output_dimension is not None:
                kwargs["output_dimension"] = output_dimension

            result = vo.embed(texts, **kwargs)
            return result.embeddings

        except Exception as e:
            last_error = e
            # Bloqueio de edge nao se resolve com retry — fail fast
            if _is_edge_block(e):
                logger.error(
                    f"[VoyageClient] Bloqueio externo detectado (WAF/CDN 403): {str(e)[:200]}"
                )
                raise EmbeddingUnavailableError(
                    f"Voyage AI bloqueada por edge/WAF (retry futil): {str(e)[:200]}"
                ) from e

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f"[VoyageClient] Tentativa {attempt + 1}/{MAX_RETRIES} falhou: {e}. "
                    f"Retentando em {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[VoyageClient] Todas as {MAX_RETRIES} tentativas falharam: {e}"
                )

    # Apos exhaustion: reclassifica se a ultima falha parecer bloqueio
    if last_error is not None and _is_edge_block(last_error):
        raise EmbeddingUnavailableError(
            f"Voyage AI bloqueada apos {MAX_RETRIES} tentativas: {str(last_error)[:200]}"
        ) from last_error

    raise RuntimeError(
        f"Voyage AI embed falhou apos {MAX_RETRIES} tentativas: {last_error}"
    )


def normalize_for_embedding(text: str) -> str:
    """
    Normaliza texto antes de gerar embedding.

    Voyage AI NAO e case-invariant — "Hello" e "hello" geram
    embeddings ligeiramente diferentes. Normalizamos para consistencia
    entre indexacao e busca.

    Regras:
    - Strip whitespace
    - Unicode NFKC (normaliza caracteres compostos)
    - NAO faz lowercase (case tem valor semantico em nomes proprios)
    - NAO remove acentos (acentos tem valor semantico em portugues)

    Args:
        text: Texto original

    Returns:
        Texto normalizado
    """
    if not text:
        return ""

    # Strip + NFKC normalize
    normalized = unicodedata.normalize('NFKC', text.strip())

    # Colapsar whitespace multiplo
    normalized = ' '.join(normalized.split())

    return normalized
