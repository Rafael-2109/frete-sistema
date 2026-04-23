"""
Publisher Redis pub/sub para canal chat_sse:<user_id>.

Best-effort: se Redis estiver down, loga e segue (a mensagem ja persiste
no DB antes do publish; o cliente reconecta via SSE e pega via catch-up).
"""
import json
import os
from typing import Optional

import redis

from app.utils.logging_config import logger


def _get_redis() -> Optional[redis.Redis]:
    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    try:
        return redis.from_url(url, decode_responses=True)
    except Exception as e:
        logger.warning(f'[CHAT] Redis unavailable: {e}')
        return None


_redis = _get_redis()


def channel_for(user_id: int) -> str:
    """Nome do canal Redis por usuario."""
    return f'chat_sse:{user_id}'


def publish(user_id: int, event: str, data: dict) -> None:
    """
    Publica evento no canal do usuario. Best-effort.

    Se `_redis` e None (sem conexao), opera como no-op silencioso.
    Se publish lancar, loga warning e segue.
    """
    if _redis is None:
        logger.debug(f'[CHAT] publish skipped (no redis): user={user_id}, event={event}')
        return
    try:
        payload = json.dumps({'event': event, 'data': data})
        _redis.publish(channel_for(user_id), payload)
    except Exception as e:
        logger.warning(f'[CHAT] publish failed (user={user_id}): {e}')
