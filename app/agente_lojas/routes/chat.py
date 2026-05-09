"""
Chat do Agente Lojas HORA — SSE real com Claude Agent SDK (M2 SDK).

POST /agente-lojas/api/chat
    { "message": "...", "session_id": "uuid" }
    -> text/event-stream

Implementacao M2:
    - Thread daemon roda async generator do SDK; empurra eventos formatados
      em event_queue.Queue() (cross-thread).
    - SSE generator drena event_queue e yielda strings SSE.
    - can_use_tool (em outra thread do SDK) tambem empurra raw SSE strings
      em event_queue para `ask_user_question` — fluxo cross-thread.
    - AgentSession pre-criada antes do stream (validacao de ownership do
      POST /api/user-answer).
    - Persiste sessao + sdk_session_id + total_cost_usd + message_count.
    - Cleanup robusto: cancel_pending + cleanup_session_context no finally.
"""
import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from typing import Generator, Optional

from flask import request, jsonify, render_template, Response, stream_with_context
from flask_login import current_user

from app.agente_lojas.routes import agente_lojas_bp
from app.agente_lojas.decorators import require_acesso_agente_lojas
from app.agente_lojas.config.settings import AGENTE_ID
from app.agente_lojas.services.scope_injector import build_loja_context_block
from app.agente_lojas.sdk import stream_lojas_chat
from app.agente.models import AgentSession
from app import db

logger = logging.getLogger('sistema_fretes')


HEARTBEAT_INTERVAL_SECONDS = 10
INACTIVITY_TIMEOUT_SECONDS = 240
STREAM_MAX_DURATION_SECONDS = 540
QUEUE_GET_TIMEOUT_SECONDS = 1.0  # poll period para dreno do event_queue


def _sse(event_type: str, payload: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


@agente_lojas_bp.route('/', methods=['GET'])
@require_acesso_agente_lojas
def pagina_chat():
    """Pagina de chat do Agente Lojas HORA."""
    loja_context = build_loja_context_block(
        perfil=current_user.perfil,
        loja_hora_id=getattr(current_user, 'loja_hora_id', None),
    )
    return render_template(
        'agente_lojas/chat.html',
        loja_context_preview=loja_context,
    )


@agente_lojas_bp.route('/api/chat', methods=['POST'])
@require_acesso_agente_lojas
def api_chat():
    """Chat SSE via Claude Agent SDK."""
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        session_id = data.get('session_id') or str(uuid.uuid4())

        if not message:
            return jsonify({
                'success': False,
                'error': 'Campo "message" e obrigatorio',
            }), 400

        if len(message) > 50_000:
            return jsonify({
                'success': False,
                'error': 'Mensagem muito longa (max 50000 chars)',
            }), 400

        user_id = current_user.id
        user_name = current_user.nome or current_user.email or f'user_{user_id}'
        perfil = current_user.perfil
        loja_hora_id = getattr(current_user, 'loja_hora_id', None)

        # Persiste sessao particionada (agente='lojas') ANTES do stream para
        # validacao de ownership do POST /api/user-answer.
        session, created = AgentSession.get_or_create(
            session_id=session_id,
            user_id=user_id,
            channel='web',
        )
        if created or session.agente != AGENTE_ID:
            session.agente = AGENTE_ID
        session.model = None  # sera setado no done
        db.session.commit()

        # sdk_session_id: usa mesmo session_id para nomear JSONL (SDK 0.1.52+)
        sdk_session_id = session.data.get('sdk_session_id') if session.data else None

        return Response(
            stream_with_context(
                _generate_sse(
                    user_message=message,
                    session_id=session_id,
                    sdk_session_id=sdk_session_id,
                    user_id=user_id,
                    user_name=user_name,
                    perfil=perfil,
                    loja_hora_id=loja_hora_id,
                )
            ),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            },
        )

    except Exception as e:
        logger.exception("[AGENTE_LOJAS] Erro em api_chat: %s", e)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


def _streaming_worker(
    *,
    user_message: str,
    user_id: int,
    user_name: str,
    perfil: str,
    loja_hora_id: Optional[int],
    sdk_session_id: Optional[str],
    our_session_id: str,
    event_queue: 'queue.Queue',
    state: dict,
):
    """Worker em daemon thread que processa async gen do SDK.

    Empurra strings SSE pre-formatadas em event_queue. Encerra com sentinel
    None para sinalizar fim ao SSE generator.

    `state` e dict mutavel para repassar metadata pos-stream (sdk_session_id,
    total_cost_usd, etc.) ao thread principal.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        try:
            agen = stream_lojas_chat(
                user_message=user_message,
                user_id=user_id,
                user_name=user_name,
                perfil=perfil,
                loja_hora_id=loja_hora_id,
                sdk_session_id=sdk_session_id,
                our_session_id=our_session_id,
                event_queue=event_queue,
            )
            async for event in agen:
                etype = event.get('type')
                meta = event.get('metadata', {}) or {}
                content = event.get('content', '')

                if etype == 'init':
                    sid = meta.get('sdk_session_id')
                    if sid:
                        state['sdk_session_id'] = sid
                    event_queue.put(_sse('init', {'sdk_session_id': sid}))
                elif etype == 'done':
                    state['final_metadata'] = meta
                    event_queue.put(_sse('done', meta))
                else:
                    event_queue.put(_sse(etype, {'content': content, **meta}))
        except Exception as e:
            logger.exception("[AGENTE_LOJAS] worker erro: %s", e)
            event_queue.put(_sse('error', {'content': str(e)}))
        finally:
            event_queue.put(None)  # sentinel

    try:
        loop.run_until_complete(_run())
    except Exception as e:
        logger.exception("[AGENTE_LOJAS] worker outer erro: %s", e)
        try:
            event_queue.put(_sse('error', {'content': str(e)}))
            event_queue.put(None)
        except Exception:
            pass
    finally:
        try:
            loop.close()
        except Exception:
            pass


def _generate_sse(
    user_message: str,
    session_id: str,
    sdk_session_id: Optional[str],
    user_id: int,
    user_name: str,
    perfil: str,
    loja_hora_id,
) -> Generator[str, None, None]:
    """Generator SSE — drena event_queue alimentado pelo worker thread.

    O worker thread roda o async gen do SDK e tambem o callback can_use_tool
    (que pode emitir `ask_user_question` raw SSE). O generator aqui apenas
    consome event_queue cross-thread com timeout para heartbeat/inatividade.
    """
    event_queue: 'queue.Queue[Optional[str]]' = queue.Queue()
    state: dict = {
        'sdk_session_id': sdk_session_id,
        'final_metadata': {},
    }
    t_start = time.time()
    last_event_time = t_start

    worker = threading.Thread(
        target=_streaming_worker,
        kwargs={
            'user_message': user_message,
            'user_id': user_id,
            'user_name': user_name,
            'perfil': perfil,
            'loja_hora_id': loja_hora_id,
            'sdk_session_id': sdk_session_id,
            'our_session_id': session_id,
            'event_queue': event_queue,
            'state': state,
        },
        daemon=True,
        name=f'lojas-stream-{session_id[:8]}',
    )

    try:
        yield _sse('start', {
            'session_id': session_id,
            'agente': AGENTE_ID,
        })

        worker.start()

        while True:
            elapsed = time.time() - t_start
            if elapsed > STREAM_MAX_DURATION_SECONDS:
                yield _sse('error', {'content': 'stream max duration exceeded'})
                break
            if time.time() - last_event_time > INACTIVITY_TIMEOUT_SECONDS:
                yield _sse('error', {'content': 'inactivity timeout'})
                break

            try:
                evt = event_queue.get(timeout=QUEUE_GET_TIMEOUT_SECONDS)
            except queue.Empty:
                # Heartbeat para manter conexao viva (proxy Render mata idle).
                # NAO renova last_event_time — heartbeat nao conta como progresso.
                if time.time() - last_event_time >= HEARTBEAT_INTERVAL_SECONDS:
                    yield _sse('heartbeat', {})
                continue

            if evt is None:
                # sentinel de fim do worker
                break

            last_event_time = time.time()
            yield evt

        # Persistencia pos-stream (sdk_session_id + message_count)
        _persist_session_after_stream(
            session_id=session_id,
            user_message=user_message,
            sdk_session_id=state.get('sdk_session_id'),
            final_metadata=state.get('final_metadata') or {},
        )

    finally:
        # Garante que worker morre se cliente desconectou. cleanup_session_context
        # e cancel_pending sao feitos pelo client.py:stream_response (finally).
        if worker.is_alive():
            try:
                worker.join(timeout=2.0)
            except Exception:
                pass


def _persist_session_after_stream(
    session_id: str,
    user_message: str,
    sdk_session_id: Optional[str],
    final_metadata: dict,
):
    """Atualiza AgentSession com sdk_session_id, message_count, cost, model."""
    try:
        session = AgentSession.query.filter_by(
            session_id=session_id,
            agente=AGENTE_ID,
        ).first()
        if not session:
            return

        data = session.data or {}
        messages = data.get('messages', [])
        messages.append({
            'role': 'user',
            'content': user_message[:2000],  # truncate para nao inflar JSONB
        })
        data['messages'] = messages[-50:]  # cap ultimas 50 msgs
        if sdk_session_id:
            data['sdk_session_id'] = sdk_session_id
        data['channel'] = 'web'

        session.data = data
        session.message_count = (session.message_count or 0) + 1
        session.last_message = user_message[:500]
        if final_metadata.get('total_cost_usd'):
            session.total_cost_usd = (
                (session.total_cost_usd or 0)
                + float(final_metadata['total_cost_usd'])
            )
        if not session.model:
            session.model = 'claude-opus-4-7'

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, 'data')
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.exception("[AGENTE_LOJAS] Falha ao persistir sessao: %s", e)
