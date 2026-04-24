"""
SSE generator — stream_chat_events(user_id).

Padrao reutilizado de app/agente/routes/chat.py (linhas 1106+).
Canal: chat_sse:<user_id>. Heartbeat a cada 25s (Render SSL drop 30-40s — ver app/teams/CLAUDE.md R2).

Uso via Flask:
    Response(stream_with_context(stream_chat_events(user_id)), mimetype='text/event-stream', ...)
"""
import json
import os
import time
from typing import Generator, Optional

import redis


HEARTBEAT_INTERVAL = 25  # segundos
CATCHUP_LIMIT = 100  # max mensagens replayed em um Last-Event-ID


def _get_pubsub(user_id: int):
    """Cria pubsub Redis subscrito ao canal do usuario. Retorna None se Redis down."""
    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    try:
        r = redis.from_url(url, decode_responses=True)
        ps = r.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(f'chat_sse:{user_id}')
        return ps
    except Exception:
        return None


def _format_event(event_type: str, data: dict, event_id: Optional[int] = None) -> str:
    """Formata um evento no protocolo SSE (id + event + data + blank line)."""
    lines = []
    if event_id is not None:
        lines.append(f'id: {event_id}')
    lines.append(f'event: {event_type}')
    lines.append(f'data: {json.dumps(data)}')
    lines.append('')  # blank line = end of event
    lines.append('')
    return '\n'.join(lines)


def _catchup_events(user_id: int, last_event_id: int) -> Generator[str, None, None]:
    """Replay de mensagens do DB com id > last_event_id (max 100)."""
    from app import db
    from app.chat.models import ChatMessage, ChatMember

    thread_ids = [
        r.thread_id for r in db.session.query(ChatMember).filter(
            ChatMember.user_id == user_id,
            ChatMember.removido_em.is_(None),
        ).all()
    ]
    if not thread_ids:
        return
    # Filtrar soft-deleted: _message_dict da REST ja esconde content deletado (R8);
    # aqui precisa o mesmo para nao vazar preview via Last-Event-ID catch-up.
    catchup = db.session.query(ChatMessage).filter(
        ChatMessage.thread_id.in_(thread_ids),
        ChatMessage.id > last_event_id,
        ChatMessage.deletado_em.is_(None),
    ).order_by(ChatMessage.id.asc()).limit(CATCHUP_LIMIT).all()
    for m in catchup:
        yield _format_event('message_new', {
            'thread_id': m.thread_id,
            'message_id': m.id,
            'preview': (m.content or '')[:100],
            'sender_type': m.sender_type,
        }, event_id=m.id)


def stream_chat_events(
    user_id: int,
    last_event_id: Optional[int] = None,
    max_iterations: Optional[int] = None,
) -> Generator[str, None, None]:
    """
    Generator para Flask Response com mimetype='text/event-stream'.

    - Envia `: connected` primeiro.
    - Se last_event_id: replay catch-up via DB (max 100 msgs).
    - Subscribe Redis chat_sse:<user_id>; yield eventos publicados.
    - Heartbeat a cada HEARTBEAT_INTERVAL segundos.
    - max_iterations: limite para testes (None = infinito).
    """
    # Hello inicial
    yield ': connected\n\n'

    # Catch-up via DB
    if last_event_id:
        try:
            yield from _catchup_events(user_id, last_event_id)
        except Exception:
            # Catch-up e best-effort; nao interrompe stream principal
            pass

    ps = _get_pubsub(user_id)
    if ps is None:
        # Sem Redis: mantem conexao apenas com heartbeats
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            time.sleep(HEARTBEAT_INTERVAL)
            yield ': heartbeat\n\n'
            iterations += 1
        return

    last_heartbeat = time.time()
    iterations = 0
    try:
        while max_iterations is None or iterations < max_iterations:
            msg = ps.get_message(timeout=1.0)
            if msg and msg.get('type') == 'message':
                try:
                    parsed = json.loads(msg['data'])
                    event_type = parsed.get('event', 'message')
                    data = parsed.get('data', {})
                    event_id = data.get('message_id')
                    yield _format_event(event_type, data, event_id=event_id)
                except (json.JSONDecodeError, KeyError):
                    continue
            else:
                now = time.time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield ': heartbeat\n\n'
                    last_heartbeat = now
            iterations += 1
    finally:
        try:
            ps.close()
        except Exception:
            pass
