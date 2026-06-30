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
import concurrent.futures
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
from app.agente.models import AgentSession
from app import db

logger = logging.getLogger('sistema_fretes')


# CUTOVER FEITO (FASE B, 2026-06-30): o fork AgentLojasClient foi aposentado. A
# rota /agente-lojas usa SEMPRE o motor web por perfil (get_client('lojas').
# stream_response) — ver _drain_via_motor. A antiga flag AGENT_LOJAS_USA_MOTOR_UNICO
# (canary) foi removida apos validacao em PROD.


HEARTBEAT_INTERVAL_SECONDS = 10
# Timeouts alinhados ao agente web (app/agente/routes/_constants.py) apos 3
# timeouts reais em prod (2026-05): inatividade renovada a cada evento real
# (heartbeat NAO renova), teto absoluto folgado vs gunicorn (1800s). Antes
# 240s/540s cortavam skill SQL pesada e o subagente orientador-loja.
INACTIVITY_TIMEOUT_SECONDS = 300
STREAM_MAX_DURATION_SECONDS = 1740
QUEUE_GET_TIMEOUT_SECONDS = 1.0  # poll period para dreno do event_queue


def _sse(event_type: str, payload: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


def _motor_event_to_sse(event, state: dict) -> Optional[str]:
    """Converte um StreamEvent do motor web (app/agente/sdk) no SSE que o
    frontend lojas espera — mesmo SHAPE que o fork `_drain_async_gen` produzia.

    CUTOVER E3.8b passo 3: o frontend (templates/agente_lojas/chat.html) trata
    text/thinking/tool_call/tool_result/todos/task_event/error/init/done. Os
    campos DIVERGEM do agente web: `tool_call` usa tool_name+tool_input e
    `tool_result` usa content+is_error (o motor web serializa tool_result como
    {tool_name, result}). Por isso espelhamos o FORK, nao a serializacao do web.

    Efeito colateral: acumula em `state` o assistant_text (persistencia), o
    sdk_session_id (resume) e o final_metadata (custo/tokens). Retorna None para
    eventos que o frontend lojas NAO consome (nao vira SSE).
    """
    etype = event.type
    meta = event.metadata or {}
    content = event.content

    if etype == 'init':
        sid = content.get('session_id') if isinstance(content, dict) else None
        if sid and sid != 'pending':
            state['sdk_session_id'] = sid
        return _sse('init', {'sdk_session_id': sid})

    if etype == 'text':
        state['assistant_text'] = (state.get('assistant_text') or '') + (content or '')
        return _sse('text', {'content': content})

    if etype == 'thinking':
        return _sse('thinking', {'content': content})

    if etype == 'tool_call':
        # Motor: content=tool_name, metadata['input']=tool_input.
        return _sse('tool_call', {
            'content': '',
            'tool_name': content,
            'tool_id': meta.get('tool_id'),
            'tool_input': meta.get('input'),
        })

    if etype == 'tool_result':
        # Motor: content=result, metadata['is_error']/['tool_name']. Frontend lojas
        # le payload.content + payload.is_error.
        _is_error = bool(meta.get('is_error', False))
        # Task* (TaskCreate/TaskUpdate/TaskList): o motor emite tool_result E
        # task_event (client.py:1239 + :1280). O fork suprimia o tool_result
        # generico — replicamos para nao duplicar no UI. Excecao: com erro o motor
        # NAO emite task_event, entao o tool_result (carregando o erro) deve passar.
        if (meta.get('tool_name') or '') in ('TaskCreate', 'TaskUpdate', 'TaskList') and not _is_error:
            return None
        return _sse('tool_result', {
            'content': str(content if content is not None else ''),
            'tool_use_id': meta.get('tool_use_id'),
            'is_error': _is_error,
        })

    if etype == 'todos':
        todos = (content or {}).get('todos', []) if isinstance(content, dict) else []
        if todos:
            return _sse('todos', {'todos': todos})
        return None

    if etype == 'task_event':
        # Motor: content = dict {action, task_id?, subject?, tasks?, status?}.
        if isinstance(content, dict) and content.get('action'):
            return _sse('task_event', content)
        return None

    if etype == 'done':
        c = content if isinstance(content, dict) else {}
        sdk_sid = c.get('session_id')
        if sdk_sid and sdk_sid != 'pending':
            state['sdk_session_id'] = sdk_sid
        final_meta = {
            'total_cost_usd': c.get('total_cost_usd', 0),
            'input_tokens': c.get('input_tokens', 0),
            'output_tokens': c.get('output_tokens', 0),
        }
        state['final_metadata'] = final_meta
        return _sse('done', final_meta)

    if etype == 'error':
        payload = {'content': content}
        if meta.get('error_type'):
            payload['error_type'] = meta['error_type']
        return _sse('error', payload)

    # Tipos do motor web que o frontend lojas NAO consome (warning/queued/
    # task_started/task_progress/task_notification/rate_limit/stderr/
    # subagent_summary/interrupt_ack): nao emitir SSE.
    return None


@agente_lojas_bp.route('/', methods=['GET'])
@require_acesso_agente_lojas
def pagina_chat():
    """Pagina de chat do Agente Lojas HORA."""
    # FIX S2 (2026-06-26): NAO renderizar o bloco interno <loja_context> na UI
    # (andaime de prompt). O escopo de loja chega ao modelo via hook
    # UserPromptSubmit (sdk/hooks.py); a tela do operador nao precisa exibi-lo.
    return render_template('agente_lojas/chat.html')


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


async def _drain_via_motor(
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
    """Drena o stream do MOTOR UNICO (get_client('lojas')) para o frontend lojas.

    Reusa o AgentClient web do perfil 'lojas' — `get_client('lojas')` ja produz
    settings/skills(allow-list)/agents({orientador-loja})/hooks isolados por
    agente='lojas' (memoria + skill-reminders + enforce), injeta <loja_context> e
    suprime hints SQL Nacom (ETAPA 1+2+3a). Esta coroutine apenas:
      (a) seta os ContextVars do registry WEB para o motor/hooks/can_use_tool
          lerem o perfil 'lojas' e o escopo de loja;
      (b) serializa cada StreamEvent no SSE que o frontend lojas espera (formato
          do fork, via _motor_event_to_sse) + acumula state p/ persistencia;
      (c) limpa os ContextVars no finally. Encerra com sentinel None.
    """
    from app.agente.config.permissions import (
        set_current_session_id,
        set_current_user_id,
        set_current_agent_id,
        set_loja_scope,
        set_event_queue,
        clear_current_agent_id,
        clear_loja_scope,
        clear_current_user_id,
        cleanup_session_context,
    )
    from app.agente.sdk.client import get_client
    from app.agente_lojas.config.permissions import can_use_tool as lojas_can_use_tool

    # Wiring do registry WEB: o motor (stream_response) e os hooks (build_hooks
    # agente_id='lojas') leem destes ContextVars; o can_use_tool do agente_lojas
    # (config/permissions) le session_id/event_queue do MESMO registro (C4).
    # set_current_agent_id ANTES de set_loja_scope — o hook so injeta
    # <loja_context> quando agente='lojas'.
    set_current_session_id(our_session_id)
    set_current_user_id(user_id)
    # memory_mcp_tool tem ContextVar proprio de user_id (espelha o web route).
    try:
        from app.agente.tools.memory_mcp_tool import set_current_user_id as _set_mem_uid
        _set_mem_uid(user_id)
    except Exception as _mem_uid_err:
        logger.debug(
            "[AGENTE_LOJAS] set_current_user_id(memory) ignorado: %s", _mem_uid_err,
        )
    set_current_agent_id(AGENTE_ID)  # 'lojas'
    set_loja_scope(perfil, loja_hora_id)
    if event_queue is not None:
        set_event_queue(our_session_id, event_queue)

    try:
        client = get_client(AGENTE_ID)  # AgentClient do perfil 'lojas' (E1.2)
        agen = client.stream_response(
            prompt=user_message,
            user_name=user_name,
            user_id=user_id,
            sdk_session_id=sdk_session_id,
            our_session_id=our_session_id,
            # R4 (MAPA_A5): can_use_tool do agente_lojas (config/permissions) preserva
            # os _DANGEROUS_BASH_PATTERNS HORA (delete from hora_*) + guard /tmp. E param
            # de stream_response — fica no perfil, nao migra para o motor.
            can_use_tool=lojas_can_use_tool,
        )
        async for event in agen:
            sse = _motor_event_to_sse(event, state)
            if sse is not None:
                event_queue.put(sse)
    except Exception as e:
        logger.exception("[AGENTE_LOJAS] drain motor erro: %s", e)
        # 'error' reseta o modal no frontend; 'done' destrava o stream.
        event_queue.put(_sse('error', {'content': str(e)}))
        event_queue.put(_sse('done', {'error_recovery': True}))
    finally:
        clear_current_agent_id()
        clear_loja_scope()
        clear_current_user_id()
        cleanup_session_context(our_session_id)
        event_queue.put(None)  # sentinel


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
    """Worker em daemon thread: roda o motor unico (get_client('lojas')) no loop
    do client_pool do agente WEB (stream_response do motor usa esse pool) e drena
    o stream para event_queue. Sinaliza fim com sentinel None."""
    # A coroutine roda no loop do MOTOR (client_pool do agente web); submeter a
    # outro loop cruzaria event loops e o can_use_tool nao veria os ContextVars.
    from app.agente.sdk.client_pool import submit_coroutine as _submit_motor
    coro = _drain_via_motor(
        user_message=user_message,
        user_id=user_id,
        user_name=user_name,
        perfil=perfil,
        loja_hora_id=loja_hora_id,
        sdk_session_id=sdk_session_id,
        our_session_id=our_session_id,
        event_queue=event_queue,
        state=state,
    )
    try:
        fut = _submit_motor(coro)
    except Exception as e:
        # submit_coroutine do motor LEVANTA RuntimeError se o pool web estiver off
        # (USE_PERSISTENT_SDK_CLIENT=false) ou o loop fechado. Sem este guard a
        # thread daemon morreria ANTES do sentinel None e o SSE generator travaria
        # ate o timeout de inatividade (~300s). Destrava o frontend com error+sentinel.
        logger.exception("[AGENTE_LOJAS] submit ao loop do motor falhou: %s", e)
        try:
            coro.close()  # evita 'coroutine never awaited'
        except Exception:
            pass
        event_queue.put(_sse('error', {
            'content': 'Servico do agente temporariamente indisponivel. Tente novamente.',
        }))
        event_queue.put(None)  # sentinel — destrava o SSE generator
        return

    # Expor fut em state para que _generate_sse possa cancelar no disconnect
    # (cliente desconectou o SSE) — sem isso a coroutine fica viva no pool ate
    # STREAM_MAX_DURATION_SECONDS, vazando subprocess SDK + entry em pending_questions.
    state['_fut'] = fut
    try:
        fut.result(timeout=STREAM_MAX_DURATION_SECONDS + 30)
    except concurrent.futures.CancelledError:
        # Cancelamento esperado quando cliente desconectou (fut.cancel em _generate_sse).
        logger.info("[AGENTE_LOJAS] worker cancelado (cliente desconectou)")
    except Exception as e:
        logger.exception("[AGENTE_LOJAS] worker erro: %s", e)
        try:
            event_queue.put(_sse('error', {'content': str(e)}))
            event_queue.put(None)
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
            assistant_text=state.get('assistant_text'),
        )

    finally:
        # Cancela coroutine no loop persistente se cliente desconectou.
        # Sem isso, async gen continua rodando ate STREAM_MAX_DURATION_SECONDS,
        # vazando subprocess SDK + entry em pending_questions ate timeout.
        # Fix code-reviewer (2026-05-09).
        fut = state.get('_fut')
        if fut is not None and not fut.done():
            try:
                fut.cancel()
                logger.info(
                    "[AGENTE_LOJAS] fut.cancel() acionado (cliente desconectou). "
                    "session=%s", session_id[:8],
                )
            except Exception:
                pass

        # Cleanup de pending_questions e stream_context tambem aqui (defesa
        # em profundidade). client.py:stream_response.finally faz o mesmo,
        # mas se a coroutine foi cancelada antes do `async with` exit, este
        # cleanup garante que registry global nao acumula entries orfaos.
        try:
            from app.agente.sdk.pending_questions import cancel_pending
            cancel_pending(session_id)
        except Exception:
            pass
        try:
            from app.agente_lojas.config.permissions import cleanup_session_context
            cleanup_session_context(session_id)
        except Exception:
            pass

        # Aguarda worker morrer (best-effort)
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
    assistant_text: Optional[str] = None,
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
        # FIX S1 (P0.2): persistir TAMBEM a resposta do assistant. Antes so o
        # turno do usuario era gravado -> historico pela metade (dropdown so
        # mostrava perguntas) e impossivel reconstruir contexto do DB. Espelha
        # add_assistant_message do agente web (app/agente/routes/chat.py).
        _assistant = (assistant_text or '').strip()
        if _assistant:
            messages.append({
                'role': 'assistant',
                'content': _assistant[:4000],
            })
        data['messages'] = messages[-50:]  # cap ultimas 50 msgs
        if sdk_session_id:
            data['sdk_session_id'] = sdk_session_id
        data['channel'] = 'web'

        # Custo do TURNO a partir do acumulado do SDK (FIX P1.3 2026-06-26).
        # ResultMessage.total_cost_usd e ACUMULADO da sessao SDK; com o resume
        # ligado (FIX S1) ele cresce a cada turno, entao somar o acumulado
        # por-turno inflaria ~Nx (bug 2026-06-19 do agente web). turn_cost_from_
        # cumulative devolve o DELTA; o acumulado anterior fica em data['_sdk_cost_*']
        # e um reset de sessao SDK zera o baseline. Espelha app/agente/routes/chat.py.
        _sdk_cumulative = float(final_metadata.get('total_cost_usd') or 0)
        if _sdk_cumulative > 0:
            from app.agente.sdk.pricing import turn_cost_from_cumulative
            _prev_cumulative = float(data.get('_sdk_cost_cumulative', 0) or 0)
            _prev_sid = data.get('_sdk_cost_session_id')
            _curr_sid = sdk_session_id or _prev_sid
            _turn_cost = turn_cost_from_cumulative(
                _sdk_cumulative, _prev_cumulative, _prev_sid, _curr_sid,
            )
            data['_sdk_cost_cumulative'] = _sdk_cumulative
            data['_sdk_cost_session_id'] = _curr_sid
            session.total_cost_usd = float(session.total_cost_usd or 0) + _turn_cost

        session.data = data
        session.message_count = (session.message_count or 0) + (2 if _assistant else 1)
        session.last_message = user_message[:500]
        if not session.model:
            session.model = 'claude-opus-4-8'

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, 'data')
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.exception("[AGENTE_LOJAS] Falha ao persistir sessao: %s", e)
