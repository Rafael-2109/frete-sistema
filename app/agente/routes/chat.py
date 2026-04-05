"""
Chat SSE core — rotas de streaming do Agente.

Extraido de routes.py durante modularizacao.
Contem o pipeline completo de chat:
  - pagina_chat (GET /)
  - api_chat (POST /api/chat) com SSE streaming
  - _async_stream_sdk_client (orquestrador async)
  - _stream_chat_response (SSE generator)
  - _save_messages_to_db (persistencia)
  - _record_routing_resolution (KG routing)
  - _image_to_base64 (Vision API)
  - api_interrupt (POST /api/interrupt)
  - api_user_answer (POST /api/user-answer)
"""

import logging
import asyncio
import os
import uuid
import time

from typing import Generator, Optional, List

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context, current_app
)
from flask_login import login_required, current_user

from app.agente.routes import agente_bp
from app import db
from app.utils.timezone import agora_utc_naive
from app.agente.routes._constants import (
    HEARTBEAT_INTERVAL_SECONDS,
    MAX_STREAM_DURATION_SECONDS,
    INACTIVITY_TIMEOUT_SECONDS,
)
from app.agente.routes._helpers import (
    _sse_event,
    run_post_session_processing,
    _calculate_cost,
    _track_memory_effectiveness,
)

logger = logging.getLogger('sistema_fretes')


# =============================================================================
# PÁGINA DE CHAT
# =============================================================================

@agente_bp.route('/', methods=['GET'])
@login_required
def pagina_chat():
    """Página de chat com o agente."""
    return render_template('agente/chat.html')


# =============================================================================
# API - CHAT (FEAT-030: Refatorado)
# =============================================================================

@agente_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """
    Chat com streaming (Server-Sent Events).

    FEAT-030: Agora salva mensagens no banco e trata sessão expirada.

    POST /agente/api/chat
    {
        "message": "Tem pedido pendente pro Atacadão?",
        "session_id": "uuid-da-nossa-sessao",  // Nosso ID, não do SDK
        "model": "claude-sonnet-4-6",
        "effort_level": "auto",
        "plan_mode": false,
        "files": []
    }

    Response: text/event-stream
    """
    try:
        data = request.get_json()

        if not data or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Campo "message" é obrigatório'
            }), 400

        message = data['message'].strip()
        session_id = data.get('session_id')  # Nosso session_id (não do SDK)
        model = data.get('model')
        effort_level = data.get('effort_level', 'off')
        plan_mode = data.get('plan_mode', False)
        files = data.get('files', [])
        output_format = data.get('output_format')  # JSON Schema para structured output
        if output_format is not None:
            if not isinstance(output_format, dict) or output_format.get('type') != 'json_schema':
                return jsonify({'success': False, 'error': 'output_format deve ter type=json_schema'}), 400
            import json as _json
            if len(_json.dumps(output_format)) > 4096:
                return jsonify({'success': False, 'error': 'output_format excede limite de 4KB'}), 400

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        # Sentry: tags para observabilidade do agente
        try:
            import sentry_sdk as _sentry
            _sentry.set_tag("agent.active", "true")
            _sentry.set_tag("agent.user_id", str(user_id))
            _sentry.set_tag("agent.user_name", user_name)
        except Exception:
            pass

        # Debug Mode: validação determinística server-side
        debug_mode = data.get('debug_mode', False)
        if debug_mode:
            from app.agente.config.feature_flags import USE_DEBUG_MODE
            if not USE_DEBUG_MODE:
                debug_mode = False
            elif current_user.perfil != 'administrador':
                logger.warning(f"[AGENTE] DEBUG MODE rejeitado: user {user_id} nao e admin")
                debug_mode = False
            else:
                logger.warning(f"[AGENTE] DEBUG MODE ativado por {user_name} (ID:{user_id})")

        # Log
        files_info = f" | Arquivos: {len(files)}" if files else ""
        debug_info = " | DEBUG MODE" if debug_mode else ""
        logger.info(
            f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}' | "
            f"Modelo: {model or 'default'} | Effort: {effort_level} | "
            f"Plan: {plan_mode}{files_info}{debug_info}"
        )

        # FEAT-032: Processar arquivos - separar imagens (Vision) dos outros (contexto texto)
        image_files = []
        other_files = []
        enriched_message = message

        if files:
            for f in files:
                file_type = f.get('type', 'file')
                if file_type == 'image':
                    # Converter imagem para base64 (Vision API)
                    # Excecao documentada: import cross-module (deferred, sem risco circular)
                    from app.agente.routes.files import _resolve_file_path
                    file_path = _resolve_file_path(f.get('url', ''))
                    if file_path and os.path.exists(file_path):
                        image_data = _image_to_base64(file_path)
                        if image_data:
                            image_files.append(image_data)
                            logger.info(f"[AGENTE] Imagem preparada para Vision: {f.get('name')}")
                        else:
                            # Fallback: se falhar conversão, adiciona como contexto texto
                            other_files.append(f)
                    else:
                        logger.warning(f"[AGENTE] Arquivo de imagem não encontrado: {f.get('url')}")
                        other_files.append(f)
                else:
                    other_files.append(f)

            # Contexto textual apenas para arquivos não-imagem
            if other_files:
                files_context = "\n\n[Arquivos anexados pelo usuário:]\n"
                for f in other_files:
                    files_context += f"- {f.get('name', 'arquivo')} ({f.get('type', 'file')}, {f.get('size', 0)} bytes)\n"
                    files_context += f"  URL: {f.get('url', 'N/A')}\n"
                enriched_message = message + files_context

            if image_files:
                logger.info(f"[AGENTE] {len(image_files)} imagem(ns) preparada(s) para Vision API")

        return Response(
            stream_with_context(_stream_chat_response(
                message=enriched_message,
                original_message=message,  # FEAT-030: Mensagem original para salvar
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                image_files=image_files,  # FEAT-032: Imagens para Vision API
                debug_mode=debug_mode,
                output_format=output_format,
            )),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except Exception as e:
        logger.error(f"[AGENTE] Erro em /api/chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# HELPERS
# =============================================================================


# =============================================================================
# STREAMING: Função async para ClaudeSDKClient persistente (v3)
# =============================================================================

async def _async_stream_sdk_client(
    client,
    our_session_id: str,
    response_state: dict,
    event_queue,
    _process_stream_event,
    message: str,
    user_id: int,
    user_name: str,
    can_use_tool,
    model: str,
    effort_level: str = "off",
    plan_mode: bool = False,
    image_files: list = None,
    app=None,
    debug_mode: bool = False,
    output_format: dict = None,
):
    """
    Orquestra streaming via ClaudeSDKClient persistente (v3).

    Restaura sdk_session_id do banco para resume + transcript.
    Constroi opcoes, hooks e contexto de memoria antes de chamar stream_response().
    """
    # Buscar sdk_session_id do banco para resume + restaurar transcript
    sdk_session_id_for_resume = None
    resume_messages_fallback = None  # Fallback: mensagens JSONB se resume falhar
    if app and our_session_id:
        try:
            with app.app_context():
                from app.agente.models import AgentSession
                db_session = AgentSession.query.filter_by(
                    session_id=our_session_id
                ).first()
                if db_session:
                    sdk_session_id_for_resume = db_session.get_sdk_session_id()
                    if sdk_session_id_for_resume:
                        logger.info(
                            f"[AGENTE] sdk_session_id para resume: "
                            f"{sdk_session_id_for_resume[:12]}..."
                        )
                        # Restaurar transcript do DB para disco antes do resume.
                        # Sem isso, worker Render reciclado perde o JSONL e
                        # o CLI falha com exit code 1.
                        transcript = db_session.get_transcript()
                        if transcript:
                            from app.agente.sdk.session_persistence import restore_session_transcript
                            restored = restore_session_transcript(
                                sdk_session_id_for_resume, transcript
                            )
                            if restored:
                                logger.info(
                                    f"[AGENTE] Transcript restaurado do DB "
                                    f"({len(transcript) / 1024:.1f} KB)"
                                )
                            else:
                                logger.warning(
                                    "[AGENTE] Falha ao restaurar transcript "
                                    "- resume pode falhar com exit 1"
                                )
                        else:
                            logger.debug(
                                "[AGENTE] Sem transcript no DB para restaurar "
                                "(primeira msg ou sessão antiga)"
                            )

                        # Carregar mensagens JSONB como fallback caso resume falhe.
                        # Se o resume funcionar, este fallback não é usado.
                        try:
                            messages = db_session.get_messages()
                            if messages and len(messages) > 1:
                                recent = messages[-10:]
                                parts = ['<conversation_history_fallback reason="resume_failed">']
                                for msg in recent:
                                    role = msg.get('role', 'unknown')
                                    content = (msg.get('content', '') or '')[:2000]
                                    if content:
                                        parts.append(f'<msg role="{role}">{content}</msg>')
                                parts.append('</conversation_history_fallback>')
                                resume_messages_fallback = '\n'.join(parts)
                                logger.debug(
                                    f"[AGENTE] Fallback JSONB preparado: "
                                    f"{len(messages)} msgs, {len(resume_messages_fallback)} chars"
                                )
                        except Exception as fb_err:
                            logger.debug(f"[AGENTE] Fallback JSONB falhou (ignorado): {fb_err}")
        except Exception as e:
            logger.warning(f"[AGENTE] Erro ao buscar sdk_session_id do DB: {e}")

    # Definir user_id no contexto para as MCP Memory Tools
    try:
        from app.agente.tools.memory_mcp_tool import set_current_user_id
        set_current_user_id(user_id)
    except ImportError:
        pass

    # Debug Mode: setar ContextVar ANTES de qualquer tool ser chamada
    if debug_mode:
        from app.agente.config.permissions import set_debug_mode
        set_debug_mode(True)

    logger.info(
        f"[AGENTE] query()+resume: session={our_session_id[:8]}... "
        f"resume={'sim' if sdk_session_id_for_resume else 'não'} "
        f"images={len(image_files) if image_files else 0}"
    )

    # =================================================================
    # P1-2: Sentiment Detection — ajusta tom se frustração detectada
    # =================================================================
    enriched_prompt = message
    try:
        from app.agente.config.feature_flags import USE_SENTIMENT_DETECTION

        if USE_SENTIMENT_DETECTION:
            from app.agente.services.sentiment_detector import enrich_message_if_frustrated
            enriched_prompt = enrich_message_if_frustrated(
                message=message,
                response_state=response_state,
            )
    except Exception as sentiment_err:
        logger.warning(f"[AGENTE] Erro na detecção de sentimento (ignorado): {sentiment_err}")

    try:
        # ─── STREAMING direto com query() ───
        # Sem pool, sem locks, sem connect/disconnect
        async for event in client.stream_response(
            prompt=enriched_prompt,
            user_name=user_name,
            model=model,
            effort_level=effort_level,
            plan_mode=plan_mode,
            user_id=user_id,
            image_files=image_files,
            sdk_session_id=sdk_session_id_for_resume,
            can_use_tool=can_use_tool,
            our_session_id=our_session_id,
            debug_mode=debug_mode,
            output_format=output_format,
            resume_messages_fallback=resume_messages_fallback,
        ):
            should_continue = _process_stream_event(event)
            if should_continue:
                continue

    except (Exception, BaseExceptionGroup) as e:
        if isinstance(e, BaseExceptionGroup):
            sub_exceptions = list(e.exceptions)
            error_str = (
                f"Erro em ferramentas paralelas ({len(sub_exceptions)} erros): "
                f"{sub_exceptions[0]}" if sub_exceptions else str(e)
            )
            logger.error(
                f"[AGENTE] ExceptionGroup no stream: {len(sub_exceptions)} sub-exceptions",
                exc_info=True
            )
        else:
            error_str = str(e)
            logger.error(f"[AGENTE] Erro no stream: {error_str}", exc_info=True)

        response_state['error_message'] = error_str
        event_queue.put(_sse_event('error', {
            'message': error_str[:200],
        }))


def _stream_chat_response(
    message: str,
    original_message: str,
    user_id: int,
    user_name: str,
    session_id: str = None,
    model: str = None,
    effort_level: str = "off",
    plan_mode: bool = False,
    image_files: List[dict] = None,
    debug_mode: bool = False,
    output_format: dict = None,
) -> Generator[str, None, None]:
    """
    Gera resposta em streaming (SSE).

    FEAT-030: Melhorias:
    - Heartbeats para manter conexão viva
    - Salva mensagens no banco
    - Trata sessão expirada no SDK
    - Acumula texto para salvar resposta completa

    FEAT-032: Suporte a Vision API
    - image_files: Lista de imagens em formato base64 para Vision

    Args:
        message: Mensagem enriquecida (com arquivos não-imagem)
        original_message: Mensagem original do usuário
        user_id: ID do usuário
        user_name: Nome do usuário
        session_id: Nosso session_id (não do SDK)
        model: Modelo a usar
        effort_level: Nível de esforço (off/low/medium/high/max)
        plan_mode: Modo somente-leitura
        image_files: Lista de dicts com imagens em base64 para Vision API
        debug_mode: Admin debug mode (desbloqueia tabelas/memorias cross-user)

    Yields:
        Eventos SSE formatados
    """
    from app.agente.sdk import get_client, get_cost_tracker
    from app.agente.config.permissions import can_use_tool
    from queue import Queue, Empty
    from threading import Thread
    app = current_app._get_current_object()
    event_queue = Queue()

    # Estado para acumular resposta
    response_state = {
        'full_text': '',
        'tools_used': [],
        'tool_errors': [],
        'input_tokens': 0,
        'output_tokens': 0,
        'sdk_session_id': None,
        'our_session_id': session_id,
        'session_expired': False,
        'error_message': None,
    }

    def run_async_stream():
        """
        Executa o stream assíncrono em uma thread separada.

        CRÍTICO: Esta função GARANTE que None sempre será colocado na fila,
        mesmo em caso de exceções não tratadas. Isso evita que o loop principal
        fique esperando eternamente.
        """
        logger.info("[AGENTE] Thread iniciada para async stream")

        async def async_stream():
            logger.info("[AGENTE] Iniciando async_stream()")
            client = get_client()
            cost_tracker = get_cost_tracker()
            processed_message_ids = set()

            our_session_id = session_id

            # Se não temos session_id, criar novo agora para os hooks
            if not our_session_id:
                our_session_id = str(uuid.uuid4())
                response_state['our_session_id'] = our_session_id

            # =============================================================
            # ASKUSERQUESTION: Definir context global thread-safe
            # O can_use_tool callback precisa de session_id e event_queue
            # para emitir SSE e esperar resposta do frontend
            # =============================================================
            from app.agente.config.permissions import set_current_session_id, set_event_queue
            set_current_session_id(our_session_id)
            set_event_queue(our_session_id, event_queue)

            # Garantir que AgentSession existe no DB ANTES do stream iniciar.
            # Sem isso, AskUserQuestion falha porque user-answer valida ownership
            # via DB query, mas a sessão só seria criada em _save_messages_to_db().
            from app.agente.models import AgentSession
            try:
                with app.app_context():
                    _sess, _created = AgentSession.get_or_create(
                        session_id=our_session_id,
                        user_id=user_id,
                    )
                    if _created:
                        db.session.commit()
                        logger.debug(
                            f"[AGENTE] AgentSession pré-criada para AskUserQuestion: "
                            f"{our_session_id[:8]}..."
                        )
            except Exception as e:
                logger.warning(f"[AGENTE] Erro ao pré-criar AgentSession: {e}")

            # =============================================================
            # PROCESSAMENTO DE EVENTOS DO STREAM
            # =============================================================
            def _process_stream_event(event):
                """
                Processa StreamEvent e coloca na fila SSE.

                Retorna True para 'init' (sinaliza continue no loop externo).
                """
                if event.type == 'init':
                    # O init agora pode conter sdk_session_id pendente ou real
                    init_session_id = event.content.get('session_id')
                    if init_session_id and init_session_id != 'pending':
                        response_state['sdk_session_id'] = init_session_id

                    if not response_state['our_session_id']:
                        response_state['our_session_id'] = str(uuid.uuid4())

                    event_queue.put(_sse_event('init', {
                        'session_id': response_state['our_session_id'],
                    }))
                    return True  # continue

                if event.type == 'text':
                    response_state['full_text'] += event.content
                    event_queue.put(_sse_event('text', {'content': event.content}))

                elif event.type == 'tool_call':
                    tool_name = event.content
                    # Enriquecer com nome especifico para Skill/Agent (routing audit)
                    tool_input = event.metadata.get('input') or {}
                    enriched_name = tool_name
                    if tool_name == 'Skill' and isinstance(tool_input, dict):
                        skill_name = tool_input.get('skill', '')
                        if skill_name:
                            enriched_name = f"Skill:{skill_name}"
                    elif tool_name == 'Agent' and isinstance(tool_input, dict):
                        agent_desc = tool_input.get('description', '')[:50]
                        agent_type = tool_input.get('subagent_type', '')
                        if agent_type:
                            enriched_name = f"Agent:{agent_type}"
                        elif agent_desc:
                            enriched_name = f"Agent:{agent_desc}"
                    if enriched_name not in response_state['tools_used']:
                        response_state['tools_used'].append(enriched_name)
                    # Manter nome original tambem para backward compat
                    if tool_name != enriched_name and tool_name not in response_state['tools_used']:
                        response_state['tools_used'].append(tool_name)
                    event_queue.put(_sse_event('tool_call', {
                        'tool_name': tool_name,
                        'tool_id': event.metadata.get('tool_id'),
                        'description': event.metadata.get('description', '')
                    }))

                elif event.type == 'tool_result':
                    tool_name_result = event.metadata.get('tool_name', '')
                    is_error = event.metadata.get('is_error', False)

                    if is_error:
                        response_state['tool_errors'].append({
                            'tool_name': tool_name_result,
                            'error': str(event.content)[:500],
                        })

                    event_queue.put(_sse_event('tool_result', {
                        'tool_name': tool_name_result,
                        'result': event.content
                    }))

                elif event.type == 'thinking':
                    event_queue.put(_sse_event('thinking', {'content': event.content}))

                elif event.type == 'todos':
                    todos = event.content.get('todos', [])
                    if todos:
                        event_queue.put(_sse_event('todos', {'todos': todos}))

                elif event.type == 'warning':
                    # Resume de sessão falhou — notificar frontend
                    event_queue.put(_sse_event('warning', {
                        'content': event.content,
                        'reason': (event.metadata or {}).get('reason', ''),
                    }))

                elif event.type == 'error':
                    response_state['error_message'] = event.content
                    error_data = {'message': event.content}
                    # Propagar error_type para frontend (auto-retry em process_error)
                    if event.metadata.get('error_type'):
                        error_data['error_type'] = event.metadata['error_type']
                    event_queue.put(_sse_event('error', error_data))

                elif event.type == 'interrupt_ack':
                    # FASE 5: Interrupt acknowledgment do ClaudeSDKClient
                    event_queue.put(_sse_event('interrupt_ack', {
                        'message': event.content if isinstance(event.content, str) else 'Operação interrompida',
                    }))

                elif event.type == 'task_started':
                    # SDK 0.1.46+: Subagente iniciou — notificar frontend
                    event_queue.put(_sse_event('task_started', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'task_type': event.metadata.get('task_type', ''),
                    }))

                elif event.type == 'task_progress':
                    # SDK 0.1.46+: Progresso de subagente
                    event_queue.put(_sse_event('task_progress', {
                        'description': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'last_tool_name': event.metadata.get('last_tool_name', ''),
                    }))

                elif event.type == 'task_notification':
                    # SDK 0.1.46+: Subagente concluiu
                    event_queue.put(_sse_event('task_notification', {
                        'summary': event.content or '',
                        'task_id': event.metadata.get('task_id', ''),
                        'status': event.metadata.get('status', ''),
                    }))

                elif event.type == 'rate_limit':
                    # SDK 0.1.50: Rate limit event
                    event_queue.put(_sse_event('rate_limit', event.metadata or {}))

                elif event.type == 'stderr':
                    # SDK stderr callback: debug output do CLI subprocess (admin-only)
                    event_queue.put(_sse_event('stderr', {
                        'line': event.content,
                    }))

                elif event.type == 'done':
                    message_id = event.metadata.get('message_id', '') or str(agora_utc_naive().timestamp())
                    response_state['input_tokens'] = event.content.get('input_tokens', 0)
                    response_state['output_tokens'] = event.content.get('output_tokens', 0)
                    cost_usd = event.content.get('total_cost_usd', 0)

                    # Salvar custo do SDK no response_state para uso em _save_messages_to_db
                    if cost_usd and cost_usd > 0:
                        response_state['sdk_cost_usd'] = cost_usd

                    # CRÍTICO: Capturar session_id REAL do SDK para resume
                    # Este é o ResultMessage.session_id — NÃO nosso UUID
                    sdk_real_session_id = event.content.get('session_id')
                    if sdk_real_session_id and sdk_real_session_id != 'pending':
                        response_state['sdk_session_id'] = sdk_real_session_id
                        logger.info(
                            f"[AGENTE] SDK session_id capturado do done: "
                            f"{sdk_real_session_id[:12]}..."
                        )

                    if message_id not in processed_message_ids:
                        processed_message_ids.add(message_id)
                        cost_tracker.record_cost(
                            message_id=message_id,
                            input_tokens=response_state['input_tokens'],
                            output_tokens=response_state['output_tokens'],
                            session_id=response_state['sdk_session_id'],
                            user_id=user_id,
                        )

                    # Evento done (inclui structured_output se output_format ativo)
                    done_payload = {
                        'session_id': response_state['our_session_id'],
                        'input_tokens': response_state['input_tokens'],
                        'output_tokens': response_state['output_tokens'],
                        'cost_usd': cost_usd,
                    }
                    structured = event.content.get('structured_output')
                    if structured is not None:
                        done_payload['structured_output'] = structured

                    # Sessao A: Context usage — enriquece done payload
                    try:
                        context_usage = client.get_context_usage()
                        if context_usage:
                            done_payload['context_usage'] = context_usage
                    except Exception:
                        pass  # Best-effort: nao quebrar stream por falha de context usage

                    event_queue.put(_sse_event('done', done_payload))

                return False  # Não é init, não precisa continue

            # =============================================================
            # Streaming via ClaudeSDKClient persistente (v3)
            # =============================================================
            await _async_stream_sdk_client(
                client=client,
                our_session_id=our_session_id,
                response_state=response_state,
                event_queue=event_queue,
                _process_stream_event=_process_stream_event,
                message=message,
                user_id=user_id,
                user_name=user_name,
                can_use_tool=can_use_tool,
                model=model,
                effort_level=effort_level,
                plan_mode=plan_mode,
                image_files=image_files,
                app=app,
                debug_mode=debug_mode,
                output_format=output_format,
            )

            # =============================================================
            # P1-1: Prompt Suggestions (best-effort, após done)
            # Gera 2-3 sugestões contextuais via Sonnet (~300-800ms)
            # O evento 'done' já foi emitido — frontend já mostra resposta
            # =============================================================
            try:
                from app.agente.config.feature_flags import USE_PROMPT_SUGGESTIONS

                if USE_PROMPT_SUGGESTIONS and response_state.get('full_text'):
                    from app.agente.services.suggestion_generator import generate_suggestions

                    suggestions = generate_suggestions(
                        user_message=message,
                        assistant_response=response_state['full_text'],
                        tools_used=response_state.get('tools_used', []),
                    )
                    if suggestions:
                        event_queue.put(_sse_event('suggestions', {
                            'suggestions': suggestions,
                        }))
            except Exception as suggestions_error:
                # SILENCIOSO: sugestões falham não devem afetar nada
                logger.warning(
                    f"[AGENTE] Erro ao gerar sugestões (ignorado): {suggestions_error}"
                )

        # =================================================================
        # CRÍTICO: GARANTIA DE FINALIZAÇÃO
        # =================================================================
        # Este bloco GARANTE que None sempre será colocado na fila,
        # independente de qualquer exceção. O finally externo é a última
        # linha de defesa contra travamentos.
        #
        # Camadas de proteção:
        # 1. asyncio.wait_for() - timeout global no async stream
        # 2. try/except interno - captura exceções do SDK
        # 3. try/except externo - captura exceções do asyncio.run()
        # 4. finally - SEMPRE coloca None na fila
        # =================================================================
        none_sent = False  # Flag para evitar duplicação

        try:
            # Timeout global: 30s antes do MAX_STREAM_DURATION para dar margem
            timeout_seconds = MAX_STREAM_DURATION_SECONDS - 30

            async def async_stream_with_timeout():
                """Wrapper com timeout para evitar travamento indefinido."""
                try:
                    await asyncio.wait_for(
                        async_stream(),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    # WARNING (não ERROR): timeout é tratado — erro enviado ao frontend
                    logger.warning(f"[AGENTE] async_stream timeout após {timeout_seconds}s")
                    event_queue.put(_sse_event('error', {
                        'message': 'Tempo limite interno excedido. A operação demorou muito.',
                        'timeout': True
                    }))

            # ClaudeSDKClient persistente (v3) — daemon thread pool.
            # v2 (asyncio.run) desligado em 2026-03-27.
            from app.agente.sdk.client_pool import submit_coroutine
            future = submit_coroutine(async_stream_with_timeout())
            try:
                future.result(timeout=MAX_STREAM_DURATION_SECONDS)
                logger.info("[AGENTE] submit_coroutine() completado com sucesso")
            except TimeoutError:
                # Cancelar task asyncio orphan no daemon thread
                # (evita "Task was destroyed but it is pending" no GC)
                future.cancel()
                logger.warning(
                    f"[AGENTE] future.result() timeout após {MAX_STREAM_DURATION_SECONDS}s "
                    "— task cancelada"
                )
                event_queue.put(_sse_event('error', {
                    'message': 'Tempo limite excedido. Tente novamente.',
                    'timeout': True
                }))

        except (Exception, BaseExceptionGroup) as e:
            if isinstance(e, BaseExceptionGroup):
                sub_exceptions = list(e.exceptions)
                error_msg = (
                    f"ExceptionGroup ({len(sub_exceptions)} erros): "
                    f"{sub_exceptions[0]}" if sub_exceptions else str(e)
                )
                logger.error(
                    f"[AGENTE] ExceptionGroup FATAL na thread: {error_msg}",
                    exc_info=True
                )
            else:
                error_msg = str(e)
                logger.error(f"[AGENTE] ERRO FATAL na thread: {error_msg}", exc_info=True)

            # Tenta enviar erro para o frontend
            try:
                event_queue.put(_sse_event('error', {
                    'message': f'Erro interno: {error_msg[:200]}',
                    'fatal': True
                }))
            except Exception:
                logger.error("[AGENTE] Não foi possível enviar erro para a fila")

        finally:
            # =================================================================
            # GARANTIA ABSOLUTA: None SEMPRE entra na fila
            # =================================================================
            # Este é o ponto mais crítico do código. Sem o None, o loop
            # principal (while True) fica esperando eternamente.
            # =================================================================
            # Cleanup: cancelar perguntas pendentes (AskUserQuestion)
            # Se o stream terminou enquanto uma pergunta estava pendente,
            # o threading.Event.wait() em permissions.py seria desbloqueado
            try:
                from app.agente.sdk.pending_questions import cancel_pending
                from app.agente.config.permissions import cleanup_session_context

                if response_state.get('our_session_id'):
                    cancel_pending(response_state['our_session_id'])
                    cleanup_session_context(response_state['our_session_id'])
            except Exception as e:
                logger.debug(f"[SSE] Cleanup session context falhou (ignorado): {e}")

            if not none_sent:
                try:
                    event_queue.put(None)
                    none_sent = True
                    logger.info("[AGENTE] Thread finalizada - None enviado (finally garantido)")
                except Exception as final_error:
                    # Última tentativa - isso não deveria acontecer
                    logger.critical(f"[AGENTE] CRÍTICO: Falha ao enviar None: {final_error}")

    try:
        logger.info("[AGENTE] _stream_chat_response iniciado")

        # Inicia streaming
        yield _sse_event('start', {'message': 'Iniciando...'})

        # Inicia thread para async stream
        thread = Thread(target=run_async_stream, daemon=True)
        thread.start()

        # Deadline com renewal: inatividade renovável + teto absoluto.
        # Eventos reais renovam o deadline de inatividade. Heartbeats NÃO renovam.
        now = time.time()
        last_heartbeat = now
        inactivity_deadline = now + INACTIVITY_TIMEOUT_SECONDS
        absolute_deadline = now + MAX_STREAM_DURATION_SECONDS
        event_count = 0
        consecutive_empty = 0  # Contador de timeouts consecutivos sem eventos

        while True:
            # Deadline check: menor entre inatividade e teto absoluto
            now = time.time()
            effective_deadline = min(inactivity_deadline, absolute_deadline)
            if now > effective_deadline:
                if now > absolute_deadline:
                    logger.warning(
                        f"[AGENTE] Absolute deadline exceeded "
                        f"({MAX_STREAM_DURATION_SECONDS}s)"
                    )
                    yield _sse_event('error', {
                        'message': 'Tempo limite excedido (9 min)'
                    })
                else:
                    inact_elapsed = INACTIVITY_TIMEOUT_SECONDS
                    logger.warning(
                        f"[AGENTE] Inactivity deadline exceeded "
                        f"({inact_elapsed}s sem eventos reais)"
                    )
                    yield _sse_event('error', {
                        'message': 'O processamento parece ter travado. Tente novamente.',
                        'sdk_stalled': True,
                        'inactivity_seconds': inact_elapsed
                    })
                break

            try:
                # Timeout para permitir heartbeats e deadline checks
                remaining = effective_deadline - now
                queue_timeout = min(HEARTBEAT_INTERVAL_SECONDS, remaining, 30)  # Max 30s
                event = event_queue.get(timeout=queue_timeout)

                if event is None:  # Fim do stream
                    logger.info(f"[AGENTE] Fim do stream, {event_count} eventos processados")
                    break

                event_count += 1
                consecutive_empty = 0  # Reset contador

                # RENEWAL: evento real renova deadline de inatividade
                inactivity_deadline = time.time() + INACTIVITY_TIMEOUT_SECONDS

                yield event

                # FIX-7: Fechar SSE após evento 'done' — não esperar None indefinidamente.
                # O done indica que o agente terminou. Aguarda brevemente por suggestions.
                if isinstance(event, str) and 'event: done\n' in event:
                    # Best-effort: espera até 3s por evento de suggestions
                    try:
                        remaining_evt = event_queue.get(timeout=3)
                        if remaining_evt is not None:
                            yield remaining_evt
                            event_count += 1
                    except Empty:
                        pass
                    logger.info(f"[AGENTE] SSE fechado após done ({event_count} eventos)")
                    break

            except Empty:
                consecutive_empty += 1

                # =================================================================
                # DETECÇÃO DE THREAD MORTA
                # =================================================================
                # Se a thread morreu sem enviar None, precisamos detectar isso
                # e forçar o fim do stream para não travar eternamente.
                # =================================================================
                if not thread.is_alive():
                    logger.warning("[AGENTE] Thread morreu sem sinalizar - forçando fim do stream")
                    yield _sse_event('error', {
                        'message': 'Processamento interrompido inesperadamente. Tente novamente.',
                        'thread_died': True
                    })
                    break

                # Inatividade e deadline absoluto são checados no topo do loop.
                # Heartbeats NÃO renovam o deadline — apenas eventos reais renovam.

                # FEAT-030: Envia heartbeat para manter conexão viva
                current_time = time.time()
                if current_time - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    yield _sse_event('heartbeat', {'timestamp': agora_utc_naive().isoformat()})
                    last_heartbeat = current_time
                    logger.debug(f"[AGENTE] Heartbeat enviado (empty count: {consecutive_empty})")

        # Aguarda thread finalizar com timeout maior (10s)
        thread.join(timeout=10.0)

        if thread.is_alive():
            logger.warning("[AGENTE] Thread ainda ativa após timeout de 10s")

        # query() limpa o CLI process automaticamente — sem pool, sem destroy.
        logger.info("[AGENTE] Thread finalizada com sucesso")

    except Exception as e:
        logger.error(f"[AGENTE] Erro no streaming: {e}", exc_info=True)
        yield _sse_event('error', {'message': str(e)})

    finally:
        # =================================================================
        # GARANTIA: SEMPRE salva mensagens no banco, mesmo em caso de erro
        # =================================================================
        # CRÍTICO: Se o stream falhar (ex: "stream closed" no ExitPlanMode),
        # o sdk_session_id capturado do SystemMessage (init) precisa ser salvo
        # no banco para que o resume funcione na próxima mensagem.
        # Sem isso, o agente perde o contexto da conversa.
        # =================================================================
        try:
            _save_messages_to_db(
                app=app,
                our_session_id=response_state['our_session_id'],
                sdk_session_id=response_state['sdk_session_id'],
                user_id=user_id,
                user_message=original_message,
                assistant_message=response_state['full_text'],
                input_tokens=response_state['input_tokens'],
                output_tokens=response_state['output_tokens'],
                tools_used=response_state['tools_used'],
                model=model,
                session_expired=response_state['session_expired'],
                sdk_cost_usd=response_state.get('sdk_cost_usd', 0),
            )
            logger.info("[AGENTE] Mensagens salvas no banco (finally)")
        except Exception as save_error:
            logger.error(f"[AGENTE] ERRO ao salvar mensagens no finally: {save_error}", exc_info=True)

        # Garantir cleanup do _stream_context mesmo se thread interna não iniciou
        # (complementa cleanup em linha 719 que só roda se thread executou)
        try:
            from app.agente.config.permissions import cleanup_session_context
            if response_state.get('our_session_id'):
                cleanup_session_context(response_state['our_session_id'])
        except Exception:
            pass


def _save_messages_to_db(
    app,
    our_session_id: str,
    sdk_session_id: str,
    user_id: int,
    user_message: str,
    assistant_message: str,
    input_tokens: int,
    output_tokens: int,
    tools_used: List[str],
    model: str,
    session_expired: bool,
    sdk_cost_usd: float = 0,
) -> None:
    """
    FEAT-030: Salva mensagens do usuário e assistente no banco.

    Args:
        app: Flask app
        our_session_id: Nosso session_id
        sdk_session_id: Session ID do SDK
        user_id: ID do usuário
        user_message: Mensagem do usuário
        assistant_message: Resposta do assistente
        input_tokens: Tokens de entrada
        output_tokens: Tokens de saída
        tools_used: Lista de tools usadas
        model: Modelo usado
        session_expired: Se a sessão SDK expirou
        sdk_cost_usd: Custo informado pelo SDK (ResultMessage.total_cost_usd)
    """
    if not our_session_id:
        logger.warning("[AGENTE] Não foi possível salvar: session_id não definido")
        return

    try:
        from app.agente.models import AgentSession

        with app.app_context():
            session, _created = AgentSession.get_or_create(
                session_id=our_session_id,
                user_id=user_id,
            )

            # Salva mensagem do usuário
            if user_message:
                session.add_user_message(user_message)

            # Salva resposta do assistente
            if assistant_message:
                session.add_assistant_message(
                    content=assistant_message,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tools_used=tools_used if tools_used else None,
                )

            # Atualiza sdk_session_id se não expirou
            _sdk_id_valid = False
            if sdk_session_id and not session_expired:
                # Defense-in-depth: só salvar se for UUID válido
                try:
                    import uuid as _uuid_validate
                    _uuid_validate.UUID(sdk_session_id)
                    session.set_sdk_session_id(sdk_session_id)
                    _sdk_id_valid = True
                except (ValueError, AttributeError):
                    logger.warning(
                        f"[AGENTE] sdk_session_id inválido (não UUID), "
                        f"descartado: {sdk_session_id[:20]}..."
                    )

                # Backup do transcript JSONL do disco para o DB.
                # Permite restaurar o JSONL caso o worker Render recicle.
                # Só faz backup se SDK session ID era UUID válido.
                if not _sdk_id_valid:
                    sdk_session_id = None
                try:
                    from app.agente.sdk.session_persistence import backup_session_transcript
                    transcript_content = backup_session_transcript(sdk_session_id)
                    if transcript_content:
                        session.save_transcript(transcript_content)
                        logger.info(
                            f"[AGENTE] Transcript backup salvo no DB "
                            f"({len(transcript_content) / 1024:.1f} KB)"
                        )
                except Exception as backup_err:
                    # Best-effort: falha no backup não deve impedir o save
                    logger.warning(
                        f"[AGENTE] Erro no backup do transcript (ignorado): "
                        f"{backup_err}"
                    )

            elif session_expired:
                # Limpa sdk_session_id para forçar nova sessão no próximo request
                session.set_sdk_session_id(None)
                logger.info(f"[AGENTE] SDK session_id limpo devido à expiração")

            # Atualiza model e custo
            if model:
                session.model = model

            # Priorizar custo do SDK (ResultMessage.total_cost_usd) sobre recálculo local
            sdk_cost = sdk_cost_usd
            calc_cost = _calculate_cost(model, input_tokens, output_tokens)
            if sdk_cost and sdk_cost > 0:
                cost_usd = sdk_cost
            else:
                cost_usd = calc_cost
            session.total_cost_usd = float(session.total_cost_usd or 0) + cost_usd

            logger.info(
                f"[AGENTE] Custo sessão {our_session_id[:8]}: "
                f"sdk_cost={sdk_cost}, calc_cost={calc_cost:.6f}, "
                f"final={cost_usd:.6f}, tokens=({input_tokens},{output_tokens})"
            )

            db.session.commit()
            logger.debug(f"[AGENTE] Mensagens salvas na sessão {our_session_id[:8]}...")

            # =============================================================
            # Post-session processing (reutilizável por web e Teams)
            # =============================================================
            run_post_session_processing(
                app=app,
                session=session,
                session_id=our_session_id,
                user_id=user_id,
                user_message=user_message,
                assistant_message=assistant_message,
            )

            # =============================================================
            # Memory v2: Feedback Loop — rastrear efetividade de memórias
            # Verifica se a resposta do Agent referencia conteúdo de memórias
            # injetadas neste turno. Incrementa effective_count se sim.
            # Roda APÓS tudo — falha não afeta nada.
            # =============================================================
            try:
                if assistant_message and user_id:
                    # Obter IDs das memórias injetadas neste turno (determinístico)
                    from app.agente.sdk import get_client as _get_client
                    _client = _get_client()
                    injected_ids = getattr(_client, '_last_injected_memory_ids', [])
                    _track_memory_effectiveness(user_id, assistant_message, injected_ids)
                    # Limpar para não vazar entre turnos
                    _client._last_injected_memory_ids = []
            except Exception as eff_err:
                logger.warning(f"[AGENTE] Memory effectiveness tracking falhou (ignorado): {eff_err}")

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar mensagens: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass


def _record_routing_resolution(user_id: int, question_text: str, answer_text: str) -> None:
    """
    Registra resolução de ambiguidade de routing no Knowledge Graph.
    Cria relação resolves_to: termo_ambíguo → domínio/skill resolvido.
    Best-effort, nunca propaga exceções.
    """
    try:
        from app.agente.services.knowledge_graph_service import _upsert_entity, _upsert_relation
        from app import db

        with db.engine.connect() as conn:
            # Extrair termo ambíguo da pergunta (heurística: texto entre "Detectei" e ".")
            import re
            term_match = re.search(r'[Dd]etectei\s+(.+?)[.]', question_text)
            term = term_match.group(1).strip() if term_match else question_text[:100]

            # Criar/buscar entidade do termo ambíguo
            source_id = _upsert_entity(conn, user_id, 'conceito', term)

            # Criar/buscar entidade da resolução (resposta do usuário)
            target_id = _upsert_entity(conn, user_id, 'conceito', answer_text[:100])

            if source_id and target_id:
                _upsert_relation(conn, source_id, target_id, 'resolves_to', 1.0, None)
                conn.commit()
                logger.info(
                    f"[ROUTING_RESOLUTION] user_id={user_id} "
                    f"'{term[:40]}' resolves_to '{answer_text[:40]}'"
                )
    except Exception as e:
        logger.debug(f"[ROUTING_RESOLUTION] Failed: {e}")


def _image_to_base64(file_path: str) -> Optional[dict]:
    """
    Converte imagem para formato Vision API do Claude.

    Args:
        file_path: Caminho absoluto da imagem

    Returns:
        Dict com formato Vision Block ou None se erro
    """
    import base64

    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    media_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }

    if ext not in media_types:
        logger.warning(f"[AGENTE] Formato de imagem não suportado para Vision: {ext}")
        return None

    try:
        with open(file_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        logger.info(f"[AGENTE] Imagem convertida para base64: {os.path.basename(file_path)} ({len(image_data)} chars)")

        return {
            'type': 'image',
            'source': {
                'type': 'base64',
                'media_type': media_types[ext],
                'data': image_data
            }
        }
    except Exception as e:
        logger.error(f"[AGENTE] Erro ao converter imagem para base64: {e}")
        return None


# =============================================================================
# API - INTERRUPT
# =============================================================================

@agente_bp.route('/api/interrupt', methods=['POST'])
@login_required
def api_interrupt():
    """Interrompe a geração atual do agente via ClaudeSDKClient.interrupt()."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({
            'success': False,
            'error': 'session_id é obrigatório.',
        }), 400

    from app.agente.sdk.client_pool import get_pooled_client, submit_coroutine

    pooled = get_pooled_client(session_id)
    if not pooled or not pooled.connected:
        return jsonify({
            'success': False,
            'error': 'Sessão não encontrada no pool ou client desconectado.',
        }), 404

    try:
        future = submit_coroutine(pooled.client.interrupt())
        future.result(timeout=10)  # Interrupt é rápido — 10s é generoso
        logger.info(
            f"[AGENTE] Interrupt enviado com sucesso: "
            f"session={session_id[:8]}..."
        )
        return jsonify({
            'success': True,
            'message': 'Interrupt enviado. O stream emitirá interrupt_ack quando processado.',
        }), 200
    except Exception as e:
        logger.warning(
            f"[AGENTE] Erro ao enviar interrupt: "
            f"session={session_id[:8]}... error={e}"
        )
        return jsonify({
            'success': False,
            'error': f'Falha ao enviar interrupt: {str(e)}',
        }), 500


# =============================================================================
# API - USER ANSWER (AskUserQuestion)
# =============================================================================

@agente_bp.route('/api/user-answer', methods=['POST'])
@login_required
def api_user_answer():
    """
    Recebe resposta do usuário para AskUserQuestion.

    Quando o agente chama AskUserQuestion, o callback can_use_tool
    fica bloqueado esperando esta resposta. Este endpoint desbloqueia
    o callback com as respostas do usuário.

    POST /agente/api/user-answer
    {
        "session_id": "uuid-da-sessao",
        "answers": {
            "Qual método prefere?": "OAuth",
            "Quais features ativar?": "Cache, Logs"
        }
    }

    Response:
        200: {"success": true, "message": "Resposta enviada ao agente"}
        400: Body/session_id/answers inválidos
        404: Nenhuma pergunta pendente para a sessão
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatório'}), 400

        answer_session_id = data.get('session_id')
        answers = data.get('answers', {})

        if not answer_session_id:
            return jsonify({'success': False, 'error': 'session_id obrigatório'}), 400

        if not answers or not isinstance(answers, dict):
            return jsonify({
                'success': False,
                'error': 'answers deve ser um dict não-vazio'
            }), 400

        # Validação de ownership: session_id deve pertencer ao usuário autenticado
        from app.agente.models import AgentSession
        session_record = AgentSession.query.filter_by(
            session_id=answer_session_id,
            user_id=current_user.id
        ).first()
        if not session_record:
            logger.warning(
                f"[AGENTE] user-answer: sessão {answer_session_id[:8]}... "
                f"não pertence ao user {current_user.id}"
            )
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 403

        from app.agente.sdk.pending_questions import submit_answer, get_pending_tool_input

        # Capturar tool_input ANTES do submit (para detectar routing questions)
        tool_input = get_pending_tool_input(answer_session_id)

        submitted = submit_answer(answer_session_id, answers)

        if not submitted:
            return jsonify({
                'success': False,
                'error': 'Nenhuma pergunta pendente para esta sessão'
            }), 404

        logger.info(
            f"[AGENTE] Resposta do usuário recebida (AskUserQuestion): "
            f"session={answer_session_id[:8]}... "
            f"keys={list(answers.keys())}"
        )

        # Best-effort: se foi pergunta de routing, registrar resolução no KG
        try:
            if tool_input and isinstance(tool_input, dict):
                questions = tool_input.get('questions', [])
                for q in questions:
                    header = (q.get('header') or '').lower()
                    if header in ('roteamento', 'routing'):
                        question_text = q.get('question', '')
                        answer_text = answers.get(question_text, '')
                        if answer_text:
                            _record_routing_resolution(
                                current_user.id, question_text, answer_text
                            )
        except Exception as resolve_err:
            logger.debug(f"[AGENTE] Routing resolution registro falhou (ignorado): {resolve_err}")

        return jsonify({
            'success': True,
            'message': 'Resposta enviada ao agente'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro em /api/user-answer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
