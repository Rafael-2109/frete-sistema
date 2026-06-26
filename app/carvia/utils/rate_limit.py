"""Rate-limit leve por IP via Redis para a Cotacao Publica.

A tela publica expoe o upload LLM (custo API) e o calcular a anonimos. Este
helper limita N requisicoes por IP/janela. Degrada ABERTO: sem Redis, erro ou
IP vazio -> permite (nunca derruba a tela por causa do rate-limit)."""
import logging

from app.utils.redis_cache import redis_cache

logger = logging.getLogger(__name__)


def permitir(acao, ip, *, limite, janela_seg):
    """True se (acao, ip) ainda esta dentro do limite na janela. Degrada aberto."""
    if not ip:
        return True
    try:
        client = redis_cache.client
        if client is None:
            return True
        chave = f"carvia:ratelimit:{acao}:{ip}"
        atual = client.incr(chave)
        if atual == 1:
            client.expire(chave, janela_seg)
        return int(atual) <= limite
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[rate_limit] degradando aberto ({acao}): {e}")
        return True
