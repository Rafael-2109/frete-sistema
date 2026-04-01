"""
Rotas Flask do Agente.

Implementação conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

FEAT-030: Histórico de Mensagens Persistente
- Mensagens salvas no banco (campo data JSONB)
- Heartbeats para manter conexão viva no Render
- Endpoint para buscar histórico

FEAT-031: Sistema de Hooks para Memória Persistente
- PRE-HOOK: Carrega memórias do usuário antes de enviar ao SDK
- POST-HOOK: Detecta padrões e preferências após resposta
- TOOL HOOKS: Instrumenta tool calls para analytics
- FEEDBACK: Processa feedback do usuário

Arquitetura v2: query() + resume (self-contained, sem estado persistente)
- Cada request HTTP usa query() standalone (spawna CLI, executa, limpa)
- resume=sdk_session_id restaura contexto da conversa anterior
- Sem SessionPool, sem locks, sem connect/disconnect

Endpoints:
- GET  /agente/              - Página de chat
- POST /agente/api/chat      - Chat com streaming (SSE)
- GET  /agente/api/health    - Health check
- GET  /agente/api/sessions  - Lista sessões do usuário
- GET  /agente/api/sessions/<id>/messages - Histórico de mensagens (FEAT-030)
- DELETE /agente/api/sessions/<id> - Excluir sessão
- PUT  /agente/api/sessions/<id>/rename - Renomear sessão
- POST /agente/api/user-answer - Resposta do usuário a AskUserQuestion
- POST /agente/api/upload    - Upload de arquivo
- GET  /agente/api/files/<filename> - Download de arquivo
- GET  /agente/api/files     - Lista arquivos da sessão
- DELETE /agente/api/files/<filename> - Remove arquivo
- POST /agente/api/feedback  - Recebe feedback do usuário (FEAT-031)
"""

import logging
import json
import asyncio
import os
import uuid
import tempfile
import shutil
import time

from typing import Generator, Optional, List
from werkzeug.utils import secure_filename

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context, send_file, current_app
)
from flask_login import login_required, current_user

from . import agente_bp
from app import csrf, db
from app.utils.timezone import agora_utc_naive
# Configuração de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# FEAT-030: Configuração de heartbeat
HEARTBEAT_INTERVAL_SECONDS = 10  # Envia heartbeat a cada 10s (reduzido de 20s)

# Cache de health check (TTL 30s) — evita chamada API real a cada request
_health_cache = {'result': None, 'timestamp': 0}
_HEALTH_CACHE_TTL = 300  # segundos (5 min — models.retrieve não gasta tokens)

# Deadline com renewal: teto absoluto + inatividade renovável
# MAX_STREAM_DURATION_SECONDS: teto absoluto (540s = 9 min, margem de 1 min antes do Render 600s)
# INACTIVITY_TIMEOUT_SECONDS: deadline renovável — cada evento real renova. Heartbeats NÃO renovam.
MAX_STREAM_DURATION_SECONDS = 540
INACTIVITY_TIMEOUT_SECONDS = 240  # 4 min sem evento real = timeout (mantém valor original)

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
            from .config.feature_flags import USE_DEBUG_MODE
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
# STREAMING: Função async para query() + resume (self-contained)
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
    Streaming via query() + resume — self-contained, sem pool.

    ARQUITETURA v2:
    - Cada chamada usa query() standalone (sem ClaudeSDKClient, sem SessionPool)
    - resume=sdk_session_id restaura contexto da conversa anterior
    - Sem locks, sem connect/disconnect, sem retry de recreate
    """
    # Buscar sdk_session_id do banco para resume + restaurar transcript
    sdk_session_id_for_resume = None
    if app and our_session_id:
        try:
            with app.app_context():
                from .models import AgentSession
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
                            from .sdk.session_persistence import restore_session_transcript
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
        except Exception as e:
            logger.warning(f"[AGENTE] Erro ao buscar sdk_session_id do DB: {e}")

    # Definir user_id no contexto para as MCP Memory Tools
    try:
        from .tools.memory_mcp_tool import set_current_user_id
        set_current_user_id(user_id)
    except ImportError:
        pass

    # Debug Mode: setar ContextVar ANTES de qualquer tool ser chamada
    if debug_mode:
        from .config.permissions import set_debug_mode
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
        from .config.feature_flags import USE_SENTIMENT_DETECTION

        if USE_SENTIMENT_DETECTION:
            from .services.sentiment_detector import enrich_message_if_frustrated
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
    from .sdk import get_client, get_cost_tracker
    from .config.permissions import can_use_tool
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
            from .config.permissions import set_current_session_id, set_event_queue
            set_current_session_id(our_session_id)
            set_event_queue(our_session_id, event_queue)

            # Garantir que AgentSession existe no DB ANTES do stream iniciar.
            # Sem isso, AskUserQuestion falha porque user-answer valida ownership
            # via DB query, mas a sessão só seria criada em _save_messages_to_db().
            from .models import AgentSession
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

                elif event.type == 'error':
                    response_state['error_message'] = event.content
                    event_queue.put(_sse_event('error', {'message': event.content}))

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
                    event_queue.put(_sse_event('done', done_payload))

                return False  # Não é init, não precisa continue

            # =============================================================
            # Streaming via query() + resume (self-contained)
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
                from .config.feature_flags import USE_PROMPT_SUGGESTIONS

                if USE_PROMPT_SUGGESTIONS and response_state.get('full_text'):
                    from .services.suggestion_generator import generate_suggestions

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
            from .sdk.client_pool import submit_coroutine
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
                from .sdk.pending_questions import cancel_pending
                from .config.permissions import cleanup_session_context

                if response_state.get('our_session_id'):
                    cancel_pending(response_state['our_session_id'])
                    cleanup_session_context(response_state['our_session_id'])
            except Exception:
                pass

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
            from .config.permissions import cleanup_session_context
            if response_state.get('our_session_id'):
                cleanup_session_context(response_state['our_session_id'])
        except Exception:
            pass


def _sse_event(event_type: str, data: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def run_post_session_processing(
    app,
    session,
    session_id: str,
    user_id: int,
    user_message: str,
    assistant_message: str,
) -> None:
    """
    Post-session processing: summarization, pattern learning, extraction, embedding.

    Best-effort: cada etapa falha silenciosamente sem afetar as demais.
    DEVE ser chamado com app_context ativo (caller garante).

    Reutilizado por web (routes.py) e Teams (teams/services.py).

    Args:
        app: Flask app
        session: AgentSession (já carregada, com mensagens)
        session_id: Nosso session_id (UUID)
        user_id: ID do usuário
        user_message: Mensagem do usuário (pode ser None)
        assistant_message: Resposta do assistente (pode ser None)
    """
    # =================================================================
    # P0-2: Sumarização Estruturada
    # =================================================================
    try:
        from .config.feature_flags import USE_SESSION_SUMMARY, SESSION_SUMMARY_THRESHOLD

        if USE_SESSION_SUMMARY and session.needs_summarization(SESSION_SUMMARY_THRESHOLD):
            logger.info(
                f"[POST_SESSION] Trigger sumarização para sessão {session_id[:8]}... "
                f"(msgs={session.message_count}, threshold={SESSION_SUMMARY_THRESHOLD})"
            )
            from .services.session_summarizer import summarize_and_save
            summarize_and_save(
                app=app,
                session_id=session_id,
                user_id=user_id,
            )
    except Exception as summary_error:
        logger.warning(f"[POST_SESSION] Erro na sumarização (ignorado): {summary_error}")

    # =================================================================
    # P1-3: Aprendizado de Padrões
    # =================================================================
    patterns_already_ran = False
    try:
        from .config.feature_flags import USE_PATTERN_LEARNING, PATTERN_LEARNING_THRESHOLD

        if USE_PATTERN_LEARNING:
            from .services.pattern_analyzer import should_analyze_patterns, analyze_and_save as analyze_patterns_and_save

            if should_analyze_patterns(user_id, PATTERN_LEARNING_THRESHOLD):
                logger.info(
                    f"[POST_SESSION] Trigger análise de padrões para usuário {user_id} "
                    f"(threshold={PATTERN_LEARNING_THRESHOLD})"
                )
                analyze_patterns_and_save(app=app, user_id=user_id)
                patterns_already_ran = True
    except Exception as pattern_error:
        logger.warning(f"[POST_SESSION] Erro na análise de padrões (ignorado): {pattern_error}")

    # =================================================================
    # Behavioral Profile (user.xml — Tier 1, SEMPRE injetado)
    # analyze_and_save() faz piggyback de user.xml quando patterns roda —
    # skip para evitar double Sonnet call (~$0.006 duplicado)
    # =================================================================
    if not patterns_already_ran:
        try:
            from .config.feature_flags import USE_BEHAVIORAL_PROFILE, BEHAVIORAL_PROFILE_THRESHOLD
            if USE_BEHAVIORAL_PROFILE:
                from .services.pattern_analyzer import should_generate_profile, generate_and_save_profile
                if should_generate_profile(user_id, BEHAVIORAL_PROFILE_THRESHOLD):
                    logger.info(
                        f"[POST_SESSION] Trigger geração de perfil para usuário {user_id} "
                        f"(threshold={BEHAVIORAL_PROFILE_THRESHOLD})"
                    )
                    generate_and_save_profile(app=app, user_id=user_id)
        except Exception as profile_err:
            logger.warning(f"[POST_SESSION] Erro geração perfil (ignorado): {profile_err}")

    # =================================================================
    # PRD v2.1: Extração pós-sessão de conhecimento organizacional
    # =================================================================
    try:
        from .config.feature_flags import (
            USE_POST_SESSION_EXTRACTION,
            POST_SESSION_EXTRACTION_MIN_MESSAGES,
        )

        if USE_POST_SESSION_EXTRACTION and user_message and assistant_message:
            msg_count = session.message_count or 0
            if msg_count >= POST_SESSION_EXTRACTION_MIN_MESSAGES:
                from threading import Thread
                from .services.pattern_analyzer import extrair_conhecimento_sessao

                # Copia mensagens para evitar race condition com a sessão
                messages_for_extraction = list(session.get_messages())

                def _run_extraction_background():
                    nonlocal messages_for_extraction
                    try:
                        with app.app_context():
                            extrair_conhecimento_sessao(
                                app=app,
                                user_id=user_id,
                                session_messages=messages_for_extraction,
                            )
                    except Exception as bg_err:
                        logger.warning(
                            f"[KNOWLEDGE_EXTRACTION] Background error: {bg_err}"
                        )
                    finally:
                        # Liberar referência da closure
                        messages_for_extraction = None
                        # Liberar session do pool em thread manual
                        try:
                            with app.app_context():
                                db.session.remove()
                        except Exception:
                            pass

                thread = Thread(
                    target=_run_extraction_background,
                    daemon=False,
                    name=f"knowledge-extraction-{user_id}",
                )
                thread.start()
                logger.info(
                    f"[POST_SESSION] Trigger extração pós-sessão em background "
                    f"para usuário {user_id} (message_count={msg_count})"
                )
    except Exception as extraction_error:
        logger.warning(f"[POST_SESSION] Erro na extração pós-sessão (ignorado): {extraction_error}")

    # =================================================================
    # Fase 4: Embedding de turn para busca semântica (best-effort)
    # =================================================================
    try:
        from .config.feature_flags import USE_SESSION_SEMANTIC_SEARCH
        if USE_SESSION_SEMANTIC_SEARCH and user_message and assistant_message:
            _embed_session_turn_best_effort(
                app, session_id, user_id,
                user_message, assistant_message, session
            )
    except Exception as emb_err:
        logger.debug(f"[POST_SESSION] Embedding turn falhou (ignorado): {emb_err}")

    # Nota: Improvement Dialogue (D8) roda via APScheduler batch (modulo 25, 07:00 e 10:00)
    # + crontab local (11:03 diario, Claude Code CLI com feature-dev).
    # NAO pos-sessao — garante cobertura de sessoes abandonadas e batch analysis cross-sessao.


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
        from .models import AgentSession

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
            if sdk_session_id and not session_expired:
                session.set_sdk_session_id(sdk_session_id)

                # Backup do transcript JSONL do disco para o DB.
                # Permite restaurar o JSONL caso o worker Render recicle.
                try:
                    from .sdk.session_persistence import backup_session_transcript
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
                    from .sdk import get_client as _get_client
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


# Threshold de cosine similarity para considerar memória efetiva (semântico)
# Configurável via env var. 0.50 é mais alto que retrieval (0.40) porque
# efetividade exige que o agente tenha *usado* a informação, não apenas relevância.
EFFECTIVENESS_COSINE_THRESHOLD = float(
    os.getenv("MEMORY_EFFECTIVENESS_COSINE_THRESHOLD", "0.50")
)

# Threshold de word overlap para fallback heurístico (relaxado de 0.60 para 0.35)
EFFECTIVENESS_WORD_OVERLAP_THRESHOLD = 0.35

# Máximo de chars da resposta do assistente para embedding (evita diluição semântica)
EFFECTIVENESS_RESPONSE_MAX_CHARS = 3000


def _record_routing_resolution(user_id: int, question_text: str, answer_text: str) -> None:
    """
    Registra resolução de ambiguidade de routing no Knowledge Graph.
    Cria relação resolves_to: termo_ambíguo → domínio/skill resolvido.
    Best-effort, nunca propaga exceções.
    """
    try:
        from .services.knowledge_graph_service import _upsert_entity, _upsert_relation
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


def _track_memory_effectiveness(user_id: int, assistant_message: str, injected_memory_ids: list[int] = None) -> None:
    """
    Memory v2 — Feedback Loop: rastreia se memórias injetadas foram usadas.

    Abordagem híbrida:
    - Primária: Voyage AI cosine similarity >= threshold (batch único ~200ms)
    - Fallback: Word overlap relaxado (>= 35%) OU entity overlap (>= 1 entidade em comum)

    Best-effort: falhas silenciosas, não afeta fluxo principal.
    """
    try:
        if not injected_memory_ids:
            return

        from .models import AgentMemory
        from .services.knowledge_graph_service import clean_for_comparison
        from sqlalchemy import text as sql_text

        # Buscar memórias pelos IDs exatos injetados neste turno
        injected_memories = AgentMemory.query.filter(
            AgentMemory.id.in_(injected_memory_ids),
        ).all()

        if not injected_memories:
            return

        # Preparar conteúdos limpos (strip XML tags + decode entities)
        memory_contents = {}  # {mem.id: clean_content}
        for mem in injected_memories:
            content = (mem.content or "").strip()
            if not content or len(content) < 15:
                continue
            clean_content = clean_for_comparison(content)
            if clean_content and len(clean_content) >= 15:
                memory_contents[mem.id] = clean_content

        if not memory_contents:
            return

        # Primária: similaridade semântica via Voyage AI
        effective_ids = _check_effectiveness_semantic(memory_contents, assistant_message)

        # Se semântico falhou (retornou None), usar fallback heurístico
        if effective_ids is None:
            effective_ids = _check_effectiveness_heuristic(memory_contents, assistant_message)
            method = "heuristic"
        else:
            method = "semantic"

        if effective_ids:
            db.session.execute(sql_text("""
                UPDATE agent_memories
                SET effective_count = effective_count + 1
                WHERE id = ANY(:ids)
            """), {"ids": effective_ids})
            db.session.commit()
            logger.debug(
                f"[MEMORY_FEEDBACK] effective_count incremented for "
                f"{len(effective_ids)}/{len(injected_memory_ids)} memories "
                f"(user_id={user_id}, method={method})"
            )
        else:
            logger.debug(
                f"[MEMORY_FEEDBACK] No effective memories detected "
                f"(user_id={user_id}, injected={len(injected_memory_ids)}, method={method})"
            )

    except Exception as e:
        logger.warning(f"[MEMORY_FEEDBACK] Tracking falhou (ignorado): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _check_effectiveness_semantic(
    memory_contents: dict[int, str],
    assistant_message: str,
) -> list[int] | None:
    """
    Verifica efetividade via Voyage AI cosine similarity (primária).

    Faz um batch único de embeddings: N conteúdos de memória + 1 resposta truncada.
    Calcula cosine similarity entre cada memória e a resposta.

    Returns:
        list[int] de IDs efetivos, ou None se embedding falhou (signal para fallback).
    """
    import math

    try:
        from app.embeddings.config import EMBEDDINGS_ENABLED
        if not EMBEDDINGS_ENABLED:
            return None  # Signal fallback

        from app.embeddings.service import EmbeddingService

        # Preparar textos para batch: memórias + resposta truncada
        mem_ids = list(memory_contents.keys())
        mem_texts = list(memory_contents.values())
        response_text = assistant_message[:EFFECTIVENESS_RESPONSE_MAX_CHARS]

        # Batch único: [mem1, mem2, ..., memN, response]
        all_texts = mem_texts + [response_text]

        svc = EmbeddingService()
        embeddings = svc.embed_texts(all_texts, input_type="document")

        if not embeddings or len(embeddings) != len(all_texts):
            return None  # Signal fallback

        # Último embedding é a resposta
        response_embedding = embeddings[-1]
        effective_ids = []

        for i, mem_id in enumerate(mem_ids):
            mem_embedding = embeddings[i]

            # Cosine similarity (Voyage retorna L2-normalized, dot = cosine)
            dot = sum(a * b for a, b in zip(mem_embedding, response_embedding))
            norm_a = math.sqrt(sum(a * a for a in mem_embedding))
            norm_b = math.sqrt(sum(b * b for b in response_embedding))

            if norm_a == 0 or norm_b == 0:
                continue

            cosine = dot / (norm_a * norm_b)

            if cosine >= EFFECTIVENESS_COSINE_THRESHOLD:
                effective_ids.append(mem_id)
                logger.debug(
                    f"[MEMORY_FEEDBACK] Semantic match: mem_id={mem_id}, cosine={cosine:.3f}"
                )

        return effective_ids

    except Exception as e:
        logger.debug(f"[MEMORY_FEEDBACK] Semantic check falhou, usando fallback: {e}")
        return None  # Signal fallback


def _check_effectiveness_heuristic(
    memory_contents: dict[int, str],
    assistant_message: str,
) -> list[int]:
    """
    Verifica efetividade via heurística relaxada (fallback).

    Duas estratégias (OR):
    1. Word overlap >= 35% (relaxado de 60%)
    2. Entity overlap >= 1 entidade em comum (CNPJs, UFs, IDs numéricos, códigos)

    Returns:
        list[int] de IDs efetivos (pode ser vazia).
    """
    import re

    assistant_lower = assistant_message.lower()
    assistant_words = set(assistant_lower.split())
    assistant_entities = _extract_entities_for_matching(assistant_message)
    effective_ids = []

    for mem_id, clean_content in memory_contents.items():
        # Estratégia 1: Word overlap relaxado
        sentences = [
            s.strip() for s in re.split(r'[.!?\n]+', clean_content)
            if len(s.strip()) >= 15
        ][:5]

        word_match = False
        for sentence in sentences:
            words = sentence.lower().split()
            if not words:
                continue
            overlap = sum(1 for w in words if w in assistant_words)
            if overlap / len(words) >= EFFECTIVENESS_WORD_OVERLAP_THRESHOLD:
                word_match = True
                logger.debug(
                    f"[MEMORY_FEEDBACK] Word overlap match: mem_id={mem_id}, "
                    f"overlap={overlap}/{len(words)}={overlap/len(words):.2f}"
                )
                break

        if word_match:
            effective_ids.append(mem_id)
            continue

        # Estratégia 2: Entity overlap
        mem_entities = _extract_entities_for_matching(clean_content)
        common_entities = mem_entities & assistant_entities
        if common_entities:
            effective_ids.append(mem_id)
            logger.debug(
                f"[MEMORY_FEEDBACK] Entity match: mem_id={mem_id}, "
                f"entities={list(common_entities)[:5]}"
            )

    return effective_ids


def _extract_entities_for_matching(text: str) -> set[str]:
    """
    Extrai entidades estruturadas de um texto para matching de efetividade.

    Extrai:
    - CNPJs (14 dígitos, com/sem formatação)
    - UFs brasileiras (26 siglas, case-sensitive, word boundary)
    - IDs numéricos >= 4 dígitos
    - Códigos alfanuméricos (min 3 chars, pelo menos 1 letra + 1 dígito)

    Returns:
        set[str] de entidades normalizadas.
    """
    import re

    entities = set()

    if not text:
        return entities

    # CNPJs: 14 dígitos (com ou sem formatação XX.XXX.XXX/XXXX-XX)
    cnpjs_formatted = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)
    for cnpj in cnpjs_formatted:
        entities.add(re.sub(r'[./-]', '', cnpj))  # Normaliza para só dígitos

    cnpjs_raw = re.findall(r'\b\d{14}\b', text)
    for cnpj in cnpjs_raw:
        entities.add(cnpj)

    # UFs brasileiras (case-sensitive, word boundary)
    UFS_BR = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
    }
    words = re.findall(r'\b[A-Z]{2}\b', text)
    for w in words:
        if w in UFS_BR:
            entities.add(f"UF:{w}")

    # IDs numéricos >= 4 dígitos (pedidos, NFs, etc.)
    ids_numericos = re.findall(r'\b\d{4,}\b', text)
    for id_num in ids_numericos:
        # Ignorar CNPJs já capturados (14 dígitos)
        if len(id_num) != 14:
            entities.add(f"ID:{id_num}")

    # Códigos alfanuméricos (cod_produto, num_pedido): min 3 chars, >= 1 letra + >= 1 dígito
    codigos = re.findall(r'\b[A-Za-z0-9]{3,}\b', text)
    for cod in codigos:
        has_letter = any(c.isalpha() for c in cod)
        has_digit = any(c.isdigit() for c in cod)
        if has_letter and has_digit:
            entities.add(f"COD:{cod.upper()}")

    return entities


def _embed_session_turn_best_effort(app, session_id, user_id, user_message, assistant_message, session):
    """
    Gera embedding de um turn (par user+assistant) para busca semântica.

    Best-effort: falhas são silenciosas e não afetam o fluxo principal.
    O embedding é gerado inline (~150ms) e salvo via upsert.

    Args:
        app: Flask app
        session_id: Nosso session_id (UUID)
        user_id: ID do usuário
        user_message: Mensagem do usuário
        assistant_message: Resposta do assistente
        session: AgentSession (para metadata)
    """
    import hashlib
    from sqlalchemy import text as sql_text

    try:
        from app.embeddings.config import SESSION_SEMANTIC_SEARCH, VOYAGE_DEFAULT_MODEL
        if not SESSION_SEMANTIC_SEARCH:
            return

        from app.embeddings.service import EmbeddingService

        # Calcular turn_index (pares de mensagens na sessão)
        msg_count = session.message_count or 0
        turn_index = max(0, (msg_count - 1) // 2)

        # Build texto embedado
        from app.embeddings.config import ASSISTANT_SUMMARY_MAX_CHARS
        assistant_summary = (assistant_message or '')[:ASSISTANT_SUMMARY_MAX_CHARS]
        texto_embedado = f"[USER]: {user_message}\n[ASSISTANT]: {assistant_summary}"

        # Content hash para stale detection
        c_hash = hashlib.md5(texto_embedado.encode('utf-8')).hexdigest()

        # Verificar se já existe com mesmo hash (skip)
        existing = db.session.execute(sql_text("""
            SELECT content_hash FROM session_turn_embeddings
            WHERE session_id = :session_id AND turn_index = :turn_index
        """), {"session_id": session_id, "turn_index": turn_index}).fetchone()

        if existing and existing[0] == c_hash:
            return  # Conteúdo não mudou

        # Gerar embedding
        svc = EmbeddingService()
        embeddings = svc.embed_texts([texto_embedado], input_type="document")

        if not embeddings:
            return

        import json
        embedding_str = json.dumps(embeddings[0])

        # Upsert
        db.session.execute(sql_text("""
            INSERT INTO session_turn_embeddings
                (session_id, user_id, turn_index,
                 user_content, assistant_summary, texto_embedado,
                 embedding, model_used, content_hash,
                 session_title, session_created_at)
            VALUES
                (:session_id, :user_id, :turn_index,
                 :user_content, :assistant_summary, :texto_embedado,
                 :embedding, :model_used, :content_hash,
                 :session_title, :session_created_at)
            ON CONFLICT ON CONSTRAINT uq_session_turn
            DO UPDATE SET
                user_content = EXCLUDED.user_content,
                assistant_summary = EXCLUDED.assistant_summary,
                texto_embedado = EXCLUDED.texto_embedado,
                embedding = EXCLUDED.embedding,
                model_used = EXCLUDED.model_used,
                content_hash = EXCLUDED.content_hash,
                session_title = EXCLUDED.session_title,
                updated_at = NOW()
        """), {
            "session_id": session_id,
            "user_id": user_id,
            "turn_index": turn_index,
            "user_content": user_message,
            "assistant_summary": assistant_summary if assistant_summary else None,
            "texto_embedado": texto_embedado,
            "embedding": embedding_str,
            "model_used": VOYAGE_DEFAULT_MODEL,
            "content_hash": c_hash,
            "session_title": session.title,
            "session_created_at": session.created_at,
        })
        db.session.commit()

        logger.debug(
            f"[AGENTE] Embedding turn {turn_index} salvo para sessão {session_id[:8]}"
        )

    except Exception as e:
        logger.debug(f"[AGENTE] _embed_session_turn_best_effort falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calcula custo aproximado baseado no modelo (delega para settings)."""
    from .config import get_settings
    settings = get_settings()
    return settings.calculate_cost(input_tokens, output_tokens, model=model)


def _format_messages_for_correction(messages: list, max_chars: int = 6000) -> str:
    """
    Formata mensagens de sessao para o prompt de correcao.

    Itera de tras para frente e inclui mensagens ate atingir max_chars.
    Cada mensagem individual e truncada em 500 chars.

    Args:
        messages: Lista de mensagens da sessao
        max_chars: Limite de caracteres total

    Returns:
        Texto formatado com [USUARIO]/[AGENTE] prefixos
    """
    formatted_parts = []
    total_chars = 0

    for msg in reversed(messages):
        role = 'USUARIO' if msg.get('role') == 'user' else 'AGENTE'
        content = (msg.get('content') or '')[:500]
        part = f"[{role}]: {content}"

        if total_chars + len(part) > max_chars:
            break

        formatted_parts.insert(0, part)
        total_chars += len(part) + 1

    return '\n'.join(formatted_parts)


# =============================================================================
# API - SESSIONS
# =============================================================================

@agente_bp.route('/api/sessions', methods=['GET'])
@login_required
def api_list_sessions():
    """
    Lista sessões do usuário.

    GET /agente/api/sessions?limit=20
    """
    try:
        from .models import AgentSession

        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)

        sessions = AgentSession.list_for_user(
            user_id=current_user.id,
            limit=limit,
        )

        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao listar sessões: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<session_id>/messages', methods=['GET'])
@login_required
def api_get_session_messages(session_id: str):
    """
    FEAT-030: Retorna histórico de mensagens de uma sessão.

    GET /agente/api/sessions/{session_id}/messages

    Response:
    {
        "success": true,
        "session_id": "abc123",
        "messages": [
            {
                "id": "msg_xxx",
                "role": "user",
                "content": "...",
                "timestamp": "2025-12-05T10:00:00Z"
            },
            {
                "id": "msg_yyy",
                "role": "assistant",
                "content": "...",
                "timestamp": "2025-12-05T10:00:15Z",
                "tokens": {"input": 150, "output": 320}
            }
        ]
    }
    """
    try:
        from .models import AgentSession

        # Busca por session_id (string UUID)
        session = AgentSession.query.filter_by(
            session_id=session_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        messages = session.get_messages()

        response_data = {
            'success': True,
            'session_id': session_id,
            'title': session.title,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        }

        # P0-2: Inclui summary se disponível
        if session.summary:
            response_data['summary'] = session.summary
            response_data['summary_updated_at'] = (
                session.summary_updated_at.isoformat()
                if session.summary_updated_at else None
            )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao buscar mensagens: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/admin/sessions/<session_id>/messages', methods=['GET'])
@login_required
def api_admin_session_messages(session_id: str):
    """
    Endpoint admin: retorna mensagens de QUALQUER sessao (sem filtro user_id).

    GET /agente/api/admin/sessions/{session_id}/messages

    Requer perfil administrador. Usado pelo dashboard de insights para
    drill-down em sessoes de qualquer usuario.

    Response:
    {
        "success": true,
        "session_id": "abc123",
        "title": "...",
        "user_name": "...",
        "model": "...",
        "cost_usd": 0.1234,
        "status": "resolved",
        "created_at": "...",
        "messages": [...],
        "total_tokens": 15000,
        "summary": {...}
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        from .models import AgentSession
        from app.auth.models import Usuario

        session = AgentSession.query.filter_by(session_id=session_id).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessao nao encontrada'
            }), 404

        messages = session.get_messages()

        # Buscar nome do usuario
        user_name = 'N/A'
        if session.user_id:
            user = Usuario.query.get(session.user_id)
            if user:
                user_name = user.nome or f'Usuario #{session.user_id}'

        # Computar status (mesma logica do insights_service._calc_sessions)
        msg_count = session.message_count or 0
        has_tools = False
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('tools_used'):
                has_tools = True
                break

        if msg_count >= 4 and has_tools:
            status = 'resolved'
        elif msg_count <= 3 and msg_count > 0:
            status = 'abandoned'
        elif msg_count >= 5 and not has_tools:
            status = 'no_tools'
        else:
            status = 'normal'

        response_data = {
            'success': True,
            'session_id': session_id,
            'title': session.title or '(sem titulo)',
            'user_name': user_name,
            'user_id': session.user_id,
            'model': session.model or 'N/A',
            'cost_usd': round(float(session.total_cost_usd or 0), 4),
            'status': status,
            'message_count': msg_count,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        }

        if session.summary:
            response_data['summary'] = session.summary

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao buscar mensagens admin: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - ADMIN: Ciclo de Aprendizado (Instruir Agente)
# =============================================================================

@agente_bp.route('/api/admin/generate-correction', methods=['POST'])
@login_required
def api_admin_generate_correction():
    """
    Gera correcao a partir de orientacao do admin sobre uma sessao.

    O admin revisa uma sessao no modal de insights e escreve uma orientacao.
    Sonnet recebe a conversa + orientacao e gera uma correcao na voz do agente,
    pronta para ser salva na memoria persistente.

    POST /agente/api/admin/generate-correction
    {
        "session_id": "abc123",
        "guidance": "Voce deveria ter usado a skill cotando-frete..."
    }

    Response:
    {
        "success": true,
        "correction": "Quando o usuario perguntar sobre preco de frete...",
        "suggested_path": "/memories/corrections/usar-cotando-frete-para-precos.xml",
        "session_id": "abc123",
        "model_used": "claude-sonnet-4-6"
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatorio'}), 400

        session_id = data.get('session_id')
        guidance = data.get('guidance', '').strip()

        if not session_id:
            return jsonify({'success': False, 'error': 'session_id obrigatorio'}), 400
        if not guidance:
            return jsonify({'success': False, 'error': 'guidance obrigatorio'}), 400

        from .models import AgentSession

        # Busca sessao sem filtro user_id (admin pode ver qualquer sessao)
        session = AgentSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'success': False, 'error': 'Sessao nao encontrada'}), 404

        # Formatar conversa (max 6000 chars, ultimas N mensagens)
        messages = session.get_messages()
        formatted = _format_messages_for_correction(messages, max_chars=6000)

        if not formatted:
            return jsonify({'success': False, 'error': 'Sessao sem mensagens'}), 400

        # Chamar Sonnet para gerar correcao
        import anthropic
        import re as _re

        SONNET_MODEL = 'claude-sonnet-4-6'

        prompt = (
            "Voce e um agente logistico que cometeu um erro numa conversa.\n"
            "Um administrador revisou e deu esta orientacao:\n\n"
            "<orientacao>\n"
            f"{guidance}\n"
            "</orientacao>\n\n"
            "<conversa>\n"
            f"{formatted}\n"
            "</conversa>\n\n"
            "Gere uma correcao que voce salvaria na sua memoria para nao repetir o erro.\n\n"
            "Regras:\n"
            "- Primeira pessoa (\"Quando perguntarem sobre X, devo usar...\")\n"
            "- Acionavel (O QUE fazer, nao apenas o que NAO fazer)\n"
            "- Concisa (max 150 palavras)\n"
            "- Inclua contexto do erro para match semantico futuro\n\n"
            "Responda EXATAMENTE neste formato:\n"
            "<correction>\n"
            "[sua correcao]\n"
            "</correction>\n"
            "<path>/memories/corrections/[slug-descritivo].xml</path>"
        )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text if response.content else ''

        # Parsear resposta (regex para extrair <correction> e <path>)
        correction_match = _re.search(
            r'<correction>\s*(.*?)\s*</correction>', response_text, _re.DOTALL
        )
        path_match = _re.search(
            r'<path>\s*(.*?)\s*</path>', response_text, _re.DOTALL
        )

        correction = (
            correction_match.group(1).strip()
            if correction_match
            else response_text.strip()
        )
        suggested_path = (
            path_match.group(1).strip()
            if path_match
            else f'/memories/corrections/correcao-{session_id[:8]}.xml'
        )

        # Garantir que path comeca com /memories/corrections/
        if not suggested_path.startswith('/memories/corrections/'):
            slug = suggested_path.split('/')[-1] or f'correcao-{session_id[:8]}.xml'
            suggested_path = f'/memories/corrections/{slug}'

        # Garantir extensao .xml
        if not suggested_path.endswith('.xml'):
            suggested_path += '.xml'

        logger.info(
            f"[AGENTE] Correcao gerada: session={session_id[:8]}... "
            f"path={suggested_path}"
        )

        return jsonify({
            'success': True,
            'correction': correction,
            'suggested_path': suggested_path,
            'session_id': session_id,
            'model_used': SONNET_MODEL,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao gerar correcao: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/admin/save-correction', methods=['POST'])
@login_required
def api_admin_save_correction():
    """
    Salva correcao aprovada pelo admin como memoria empresa (user_id=0).

    Antes: broadcast para TODOS os usuarios (N copias identicas).
    Agora: salva 1 vez com user_id=0, escopo='empresa', visivel para todos.

    POST /agente/api/admin/save-correction
    {
        "correction": "Quando o usuario perguntar sobre preco de frete...",
        "path": "/memories/corrections/usar-cotando-frete.xml",
        "session_id": "abc123"
    }

    Response:
    {
        "success": true,
        "saved_for": "empresa (user_id=0)",
        "path": "/memories/corrections/usar-cotando-frete.xml"
    }
    """
    if current_user.perfil != 'administrador':
        return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Body obrigatorio'}), 400

        correction = data.get('correction', '').strip()
        path = data.get('path', '').strip()
        session_id = data.get('session_id', '')

        if not correction:
            return jsonify({'success': False, 'error': 'correction obrigatorio'}), 400
        if not path:
            return jsonify({'success': False, 'error': 'path obrigatorio'}), 400
        if not path.startswith('/memories/corrections/'):
            return jsonify({
                'success': False,
                'error': 'path deve comecar com /memories/corrections/'
            }), 400

        from .models import AgentMemory
        from .tools.memory_mcp_tool import (
            _check_memory_duplicate,
            _embed_memory_best_effort,
            _sanitize_content,
        )

        # Sanitizar conteudo contra prompt injection
        correction = _sanitize_content(correction)

        # Verificar duplicata semantica (escopo empresa, user_id=0)
        dup_path = _check_memory_duplicate(0, correction, current_path=path)
        if dup_path:
            return jsonify({
                'success': False,
                'error': f'Correcao similar ja existe: {dup_path}',
            }), 409

        # Wrap em XML estruturado
        admin_name = getattr(current_user, 'nome', None) or str(current_user.id)
        content = (
            f"<admin_correction>\n"
            f"<text>{correction}</text>\n"
            f"<source>admin_instruction</source>\n"
            f"<session_id>{session_id}</session_id>\n"
            f"<admin>{admin_name}</admin>\n"
            f"<created_at>{agora_utc_naive().isoformat()}</created_at>\n"
            f"</admin_correction>"
        )

        # Salvar como memoria empresa (user_id=0) em vez de broadcast
        existing = AgentMemory.get_by_path(0, path)
        if existing:
            existing.content = content
            existing.updated_at = agora_utc_naive()
        else:
            mem = AgentMemory.create_file(0, path, content)
            mem.escopo = 'empresa'
            mem.created_by = current_user.id
            mem.importance_score = 0.9  # Correcoes admin = alta prioridade
            mem.category = 'permanent'

        db.session.commit()

        # Incrementar correction_count nas memórias recentemente injetadas de TODOS os usuários
        # (correção empresa afeta todos)
        try:
            from .tools.memory_mcp_tool import _track_correction_feedback
            # Para correções empresa, aplicar ao admin que criou (user_id do contexto)
            _track_correction_feedback(current_user.id, path, correction)
        except Exception as fb_err:
            logger.debug(f"[AGENTE] Correction tracking admin falhou (ignorado): {fb_err}")

        # Embedding (best-effort, nao bloqueia)
        try:
            _embed_memory_best_effort(0, path, content)
        except Exception:
            pass

        logger.info(
            f"[AGENTE] Correcao admin salva como empresa: path={path}, "
            f"admin={admin_name}"
        )

        return jsonify({
            'success': True,
            'saved_for': 'empresa (user_id=0)',
            'path': path,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar correcao: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agente_bp.route('/api/sessions/<int:session_db_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_db_id: int):
    """
    Exclui uma sessão.

    DELETE /agente/api/sessions/123  (ID do banco, não session_id)
    """
    try:
        from .models import AgentSession

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        db.session.delete(session)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Sessão excluída'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao excluir sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/sessions/<int:session_db_id>/rename', methods=['PUT'])
@login_required
def api_rename_session(session_db_id: int):
    """
    Renomeia uma sessão.

    PUT /agente/api/sessions/123/rename
    {"title": "Novo título"}
    """
    try:
        from .models import AgentSession

        data = request.get_json()
        new_title = data.get('title', '').strip()

        if not new_title:
            return jsonify({
                'success': False,
                'error': 'Título é obrigatório'
            }), 400

        session = AgentSession.query.filter_by(
            id=session_db_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        session.title = new_title[:200]
        db.session.commit()

        return jsonify({
            'success': True,
            'session': session.to_dict()
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao renomear sessão: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - SDK CLIENT (Interrupt)
#
# Com USE_PERSISTENT_SDK_CLIENT=true: interrupt real via ClaudeSDKClient.
# Com flag=false (query()): retorna 501 (sem processo persistente).
#
# O interrupt envia sinal ao subprocess CLI. O SDK emite ResultMessage com
# subtype='interrupted', que _parse_sdk_message() converte em interrupt_ack
# SSE event (já tratado pelo frontend em chat.js:919).
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

    from .sdk.client_pool import get_pooled_client, submit_coroutine

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
# API - FILES
# =============================================================================

def _allowed_file(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_session_folder(session_id: str) -> str:
    """Retorna o caminho da pasta da sessão, criando se necessário."""
    folder = os.path.join(UPLOAD_FOLDER, str(current_user.id), session_id or 'default')
    os.makedirs(folder, exist_ok=True)
    return folder


def _get_file_type(filename: str) -> str:
    """Retorna o tipo do arquivo baseado na extensão."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ('png', 'jpg', 'jpeg', 'gif'):
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in ('xlsx', 'xls'):
        return 'excel'
    elif ext == 'csv':
        return 'csv'
    return 'file'


def _get_mimetype(filename: str) -> str:
    """Retorna o MIME type correto para o arquivo (prioriza Excel e PDF)."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mimetypes = {
        # Excel - CRÍTICO para abrir corretamente
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        # PDF - CRÍTICO para abrir corretamente
        'pdf': 'application/pdf',
        # CSV
        'csv': 'text/csv; charset=utf-8',
        # Imagens
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
    }
    return mimetypes.get(ext, 'application/octet-stream')


def _resolve_file_path(url: str) -> Optional[str]:
    """
    Resolve URL de arquivo para caminho local.

    Args:
        url: URL do arquivo (ex: /agente/api/files/session/uuid_file.png)

    Returns:
        Caminho absoluto do arquivo ou None se não encontrado
    """
    if not url:
        return None

    # Extrair partes da URL: /agente/api/files/{session_id}/{filename}
    parts = url.split('/')
    if len(parts) < 5:
        return None

    try:
        # Formato: ['', 'agente', 'api', 'files', 'session_id', 'filename']
        session_id = parts[-2]
        filename = parts[-1]

        # Tentar caminho com user_id primeiro
        if hasattr(current_user, 'id'):
            user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id), session_id)
            user_path = os.path.join(user_folder, filename)
            if os.path.exists(user_path):
                return user_path

        # Fallback: caminho sem user_id
        fallback_folder = os.path.join(UPLOAD_FOLDER, session_id)
        fallback_path = os.path.join(fallback_folder, filename)
        if os.path.exists(fallback_path):
            return fallback_path

        return None
    except Exception as e:
        logger.error(f"[AGENTE] Erro ao resolver caminho do arquivo: {e}")
        return None


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


@agente_bp.route('/api/upload', methods=['POST'])
@login_required
def api_upload_file():
    """Upload de arquivo para a sessão."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nome do arquivo vazio'
            }), 400

        if not _allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Permitidos: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        session_id = request.form.get('session_id', 'default')
        folder = _get_session_folder(session_id)

        original_name = secure_filename(file.filename)
        file_id = str(uuid.uuid4())[:8]
        safe_name = f"{file_id}_{original_name}"
        file_path = os.path.join(folder, safe_name)

        file.save(file_path)

        logger.info(f"[AGENTE] Arquivo uploaded: {safe_name} ({file_size} bytes)")

        return jsonify({
            'success': True,
            'file': {
                'id': file_id,
                'name': safe_name,
                'original_name': original_name,
                'size': file_size,
                'type': _get_file_type(original_name),
                'url': f'/agente/api/files/{session_id}/{safe_name}'
            }
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro no upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files/<session_id>/<filename>', methods=['GET'])
@login_required
def api_download_file(session_id: str, filename: str):
    """
    Download de arquivo (Excel, PDF, CSV, imagens).

    Suporta dois caminhos:
    1. /tmp/agente_files/{user_id}/{session_id}/ (uploads do chat)
    2. /tmp/agente_files/{session_id}/ (arquivos gerados por skills CLI)
    """
    try:
        safe_filename = secure_filename(filename)
        logger.info(f"[AGENTE] Download solicitado: session={session_id}, file={safe_filename}")

        # Tentar caminho com user_id primeiro (uploads do chat)
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, safe_filename)
        logger.debug(f"[AGENTE] Tentando path 1: {file_path}")

        # Fallback: caminho sem user_id (arquivos gerados por skills/scripts CLI)
        if not os.path.exists(file_path):
            fallback_folder = os.path.join(UPLOAD_FOLDER, session_id or 'default')
            fallback_path = os.path.join(fallback_folder, safe_filename)
            logger.debug(f"[AGENTE] Tentando path 2 (fallback): {fallback_path}")
            if os.path.exists(fallback_path):
                file_path = fallback_path

        if not os.path.exists(file_path):
            logger.warning(f"[AGENTE] Arquivo não encontrado: {safe_filename}")
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        # Extrai nome original (remove prefixo UUID se existir: "abc12345_nome.xlsx" -> "nome.xlsx")
        # UUID[:8] é sempre hexadecimal (0-9, a-f)
        original_name = safe_filename
        if '_' in safe_filename:
            prefix = safe_filename.split('_')[0]
            # Verifica se é um prefixo UUID válido (8 caracteres hexadecimais)
            if len(prefix) == 8 and all(c in '0123456789abcdef' for c in prefix.lower()):
                original_name = safe_filename.split('_', 1)[1]

        # Obtém MIME type correto (CRÍTICO para Excel e PDF)
        mimetype = _get_mimetype(safe_filename)
        logger.info(f"[AGENTE] Enviando arquivo: {original_name} ({mimetype})")

        # Imagens: exibir inline (no navegador)
        # Outros arquivos: forçar download
        ext = safe_filename.rsplit('.', 1)[-1].lower() if '.' in safe_filename else ''
        is_image = ext in ('png', 'jpg', 'jpeg', 'gif')

        # Parâmetro ?download=1 força download mesmo para imagens
        force_download = request.args.get('download', '0') == '1'

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=(not is_image) or force_download,
            download_name=original_name
        )

    except Exception as e:
        logger.error(f"[AGENTE] Erro no download: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files', methods=['GET'])
@login_required
def api_list_files():
    """Lista arquivos da sessão."""
    try:
        session_id = request.args.get('session_id', 'default')
        folder = _get_session_folder(session_id)

        files = []
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'name': filename,
                        'original_name': filename.split('_', 1)[1] if '_' in filename else filename,
                        'size': os.path.getsize(file_path),
                        'type': _get_file_type(filename),
                        'url': f'/agente/api/files/{session_id}/{filename}'
                    })

        return jsonify({
            'success': True,
            'files': files
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao listar arquivos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files/<session_id>/<filename>', methods=['DELETE'])
@login_required
def api_delete_file(session_id: str, filename: str):
    """Remove arquivo da sessão."""
    try:
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, secure_filename(filename))

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        os.remove(file_path)
        logger.info(f"[AGENTE] Arquivo removido: {filename}")

        return jsonify({
            'success': True,
            'message': 'Arquivo removido'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao remover arquivo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files/cleanup', methods=['POST'])
@login_required
def api_cleanup_files():
    """Limpa todos os arquivos da sessão."""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', 'default')
        folder = _get_session_folder(session_id)

        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
            logger.info(f"[AGENTE] Arquivos da sessão {session_id} limpos")

        return jsonify({
            'success': True,
            'message': 'Arquivos limpos'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao limpar arquivos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - HEALTH
# =============================================================================

@agente_bp.route('/api/health', methods=['GET'])
def api_health():
    """
    Health check do servico (com cache TTL 30s).

    Evita chamada API real ao Anthropic a cada request (~2s cada).
    Cache de 30s e aceitavel — health check nao e critico para funcionalidade.
    """
    now = time.time()

    # Retornar cache se ainda valido
    if (_health_cache['result'] is not None
            and now - _health_cache['timestamp'] < _HEALTH_CACHE_TTL):
        return jsonify(_health_cache['result'])

    try:
        from .sdk import get_client
        from .config import get_settings

        settings = get_settings()
        client = get_client()
        health = client.health_check()

        # Verificar disponibilidade dos MCP servers (import check)
        mcp_status = {}
        for mcp_name, mcp_module_path in [
            ('sql', 'app.agente.tools.text_to_sql_tool'),
            ('memory', 'app.agente.tools.memory_mcp_tool'),
            ('schema', 'app.agente.tools.schema_mcp_tool'),
            ('sessions', 'app.agente.tools.session_search_tool'),
            ('render', 'app.agente.tools.render_logs_tool'),
        ]:
            try:
                import importlib
                mod = importlib.import_module(mcp_module_path)
                server_attr = f"{mcp_name}_server" if mcp_name != 'sql' else 'sql_server'
                if mcp_name == 'memory':
                    server_attr = 'memory_server'
                elif mcp_name == 'schema':
                    server_attr = 'schema_server'
                elif mcp_name == 'sessions':
                    server_attr = 'sessions_server'
                elif mcp_name == 'render':
                    server_attr = 'render_server'
                server = getattr(mod, server_attr, None)
                mcp_status[mcp_name] = 'ok' if server is not None else 'unavailable'
            except Exception:
                mcp_status[mcp_name] = 'error'

        # Pool status (quando USE_PERSISTENT_SDK_CLIENT=true)
        pool_status = None
        try:
            from .sdk.client_pool import get_pool_status
            pool_status = get_pool_status()
        except Exception:
            pass

        result = {
            'success': True,
            'status': health.get('status', 'unknown'),
            'model': settings.model,
            'api_connected': health.get('api_connected', False),
            'sdk': 'claude-agent-sdk',
            'mcp_servers': mcp_status,
            'timestamp': agora_utc_naive().isoformat(),
        }

        # Incluir pool status se disponível
        if pool_status is not None:
            result['sdk_client_pool'] = pool_status

        # Atualizar cache
        _health_cache['result'] = result
        _health_cache['timestamp'] = now

        return jsonify(result)

    except Exception as e:
        logger.error(f"[AGENTE] Erro no health check: {e}")
        # Limpar cache em caso de erro para forcar nova tentativa
        _health_cache['result'] = None
        _health_cache['timestamp'] = 0
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# =============================================================================
# API - FEEDBACK (FEAT-031)
# =============================================================================

@agente_bp.route('/api/feedback', methods=['POST'])
@login_required
def api_feedback():
    """
    Recebe feedback do usuário sobre a resposta.

    POST /agente/api/feedback
    {
        "session_id": "uuid-da-sessao",
        "type": "positive" | "negative" | "correction" | "preference",
        "data": {
            "correction": "texto da correção",  // para type=correction
            "key": "communication",              // para type=preference
            "value": "direto"                    // para type=preference
        }
    }

    Apenas correction e preference salvam memórias.
    positive/negative são apenas logados (analytics futuro).
    """
    try:
        from .models import AgentMemory

        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Body é obrigatório'
            }), 400

        session_id = data.get('session_id')
        feedback_type = data.get('type')
        feedback_data = data.get('data', {})

        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id é obrigatório'
            }), 400

        if feedback_type not in ['positive', 'negative', 'correction', 'preference']:
            return jsonify({
                'success': False,
                'error': 'type deve ser: positive, negative, correction ou preference'
            }), 400

        user_id = current_user.id
        result = {'processed': True, 'action': feedback_type, 'memory_path': None}

        # Feedback negativo enriquecido: persistir no session data + incrementar correction_count
        if feedback_type == 'negative':
            try:
                from .models import AgentSession
                session_record = AgentSession.query.filter_by(
                    session_id=session_id, user_id=user_id
                ).first()
                if session_record and session_record.data:
                    # Registrar feedback estruturado no session data
                    feedbacks = session_record.data.get('feedbacks', [])
                    feedbacks.append({
                        'type': 'negative',
                        'context': feedback_data.get('context', '')[:500],
                        'error_category': feedback_data.get('error_category', ''),
                        'correction': feedback_data.get('correction', ''),
                        'source': feedback_data.get('source', 'thumbs_down'),
                        'timestamp': agora_utc_naive().isoformat(),
                    })
                    session_record.data['feedbacks'] = feedbacks
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(session_record, 'data')
                    db.session.commit()
                    logger.info(
                        f"[FEEDBACK] Negativo estruturado registrado: "
                        f"session={session_id[:8]}... category={feedback_data.get('error_category', 'none')}"
                    )
            except Exception as neg_err:
                logger.debug(f"[FEEDBACK] Erro ao persistir negativo (ignorado): {neg_err}")

        # Salva correções e preferências diretamente
        if feedback_type == 'correction':
            correction_text = feedback_data.get('correction', '')
            if correction_text:
                path = f"/memories/corrections/feedback_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xml"
                content = f"""<correction>
<text>{correction_text}</text>
<context>{feedback_data.get('context', '')}</context>
<source>user_feedback</source>
<created_at>{agora_utc_naive().isoformat()}</created_at>
</correction>"""
                AgentMemory.create_file(user_id, path, content)
                db.session.commit()
                result['memory_path'] = path

                # Incrementar correction_count nas memórias recentemente injetadas
                try:
                    from .tools.memory_mcp_tool import _track_correction_feedback
                    _track_correction_feedback(user_id, path, correction_text)
                except Exception as fb_err:
                    logger.debug(f"[FEEDBACK] Correction tracking falhou (ignorado): {fb_err}")

        elif feedback_type == 'preference':
            pref_key = feedback_data.get('key', 'general')
            pref_value = feedback_data.get('value', '')
            if pref_value:
                path = '/memories/preferences.xml'
                content = f"""<preferences>
<{pref_key}>{pref_value}</{pref_key}>
<source>user_feedback</source>
<updated_at>{agora_utc_naive().isoformat()}</updated_at>
</preferences>"""
                existing = AgentMemory.get_by_path(user_id, path)
                if existing:
                    existing.content = content
                else:
                    AgentMemory.create_file(user_id, path, content)
                db.session.commit()
                result['memory_path'] = path

        logger.info(
            f"[AGENTE] Feedback recebido | user={user_id} "
            f"session={session_id[:8]}... type={feedback_type}"
        )

        return jsonify({
            'success': True,
            'processed': result.get('processed', False),
            'action': result.get('action'),
            'memory_path': result.get('memory_path'),
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao processar feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - ASKUSERQUESTION (Resposta do usuário a perguntas interativas)
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
        from .models import AgentSession
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

        from .sdk.pending_questions import submit_answer, get_pending_tool_input

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


# =============================================================================
# P2-2: INSIGHTS DASHBOARD (Admin Only)
# =============================================================================

@agente_bp.route('/insights', methods=['GET'])
@login_required
def pagina_insights():
    """
    P2-2: Página de analytics do agente (admin only).

    GET /agente/insights

    Requer:
    - Perfil 'administrador'
    - Flag USE_AGENT_INSIGHTS ativa
    """
    from .config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    return render_template('agente/insights.html')


@agente_bp.route('/api/insights/data', methods=['GET'])
@login_required
def api_insights_data():
    """
    API unificada de dados de insights (inclui friccao e recomendacoes).

    GET /agente/api/insights/data?days=30&compare=true&user_id=123

    Params:
        days: Periodo em dias (default 30, max 90)
        compare: Se 'true', inclui deltas vs periodo anterior (default true)
        user_id: Filtrar por usuario especifico (opcional)

    Response:
        JSON com secoes: overview, costs, tools, users, sessions, daily,
        friction, recommendations, deltas, health_score, resolution_rate,
        model_distribution, topics, adoption_rate
    """
    from .config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)

        compare = request.args.get('compare', 'true').lower() == 'true'
        filter_user_id = request.args.get('user_id', None, type=int)

        from .services.insights_service import get_insights_data

        data = get_insights_data(
            days=days,
            user_id=filter_user_id,
            compare=compare,
        )

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao gerar insights: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/insights/friction', methods=['GET'])
@login_required
def api_insights_friction():
    """
    Alias de compatibilidade — friccao agora esta integrada em /api/insights/data.

    GET /agente/api/insights/friction?days=30

    Retorna apenas a secao de friccao extraida do endpoint unificado.
    """
    from .config.feature_flags import USE_AGENT_INSIGHTS, USE_FRICTION_ANALYSIS

    if not USE_AGENT_INSIGHTS or not USE_FRICTION_ANALYSIS:
        return jsonify({'error': 'Analise de friccao desabilitada'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)

        from .services.friction_analyzer import analyze_friction

        data = analyze_friction(days=days)

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro na analise de friccao: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/insights/memory', methods=['GET'])
@login_required
def api_insights_memory():
    """
    Métricas de qualidade do sistema de memória (T2-5).

    GET /agente/api/insights/memory?days=30&user_id=123

    Returns:
        JSON com métricas: utilization_rate, corrections_count,
        avg_importance_score, decay_distribution, orphan_embeddings, categories
    """
    from .config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)
        user_id = request.args.get('user_id', None, type=int)

        from .services.insights_service import get_memory_metrics

        data = get_memory_metrics(days=days, user_id=user_id)

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro nas metricas de memoria: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - INSIGHTS: ROUTING HEALTH
# =============================================================================

@agente_bp.route('/api/insights/routing', methods=['GET'])
@login_required
def api_insights_routing():
    """
    Métricas de saúde do roteamento — custo $0.

    GET /agente/api/insights/routing?days=30&user_id=123
    """
    from .config.feature_flags import USE_AGENT_INSIGHTS

    if not USE_AGENT_INSIGHTS:
        return jsonify({'error': 'Insights desabilitado'}), 404

    if current_user.perfil != 'administrador':
        return jsonify({'error': 'Acesso restrito a administradores'}), 403

    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 90)
        user_id = request.args.get('user_id', None, type=int)

        from .services.insights_service import get_routing_metrics

        data = get_routing_metrics(days=days, user_id=user_id)

        return jsonify({
            'success': True,
            'data': data,
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro nas metricas de routing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - ASYNC MIGRATION (Fases 0-3: Validação de viabilidade)
# =============================================================================

@agente_bp.route('/api/async-health', methods=['GET'])
@login_required
async def async_health():
    """
    Fase 0: Valida que Flask executa async routes corretamente neste ambiente.

    Se retornar {"async": true}, Flask 3.1 + Gunicorn gthread aceita async views.
    Se falhar: async routes NÃO funcionam → Fase 3 inviável.
    """
    import asyncio as _asyncio
    await _asyncio.sleep(0.01)  # Confirma que await funciona
    return jsonify({
        'async': True,
        'event_loop': str(_asyncio.get_running_loop()),
        'timestamp': agora_utc_naive().isoformat(),
    })


@agente_bp.route('/api/contextvar-test', methods=['GET'])
@login_required
def contextvar_test():
    """
    Fase 0: Valida que ContextVar funciona no MESMO fluxo de threading/asyncio usado pelo SDK.

    Simula EXATAMENTE o padrão atual:
    1. Thread daemon + asyncio.run() (como _stream_chat_response faz)
    2. Seta ContextVar DENTRO do async (como set_current_session_id faz)
    3. Lê ContextVar de um callback async (como can_use_tool faz)
    4. Compara com threading.local para confirmar equivalência
    """
    import threading
    from contextvars import ContextVar
    from queue import Queue

    result_queue = Queue()
    test_cv: ContextVar[str] = ContextVar('_test_cv', default='NOT_SET')
    test_tl = threading.local()

    def run_in_daemon():
        async def async_test():
            # Simula set_current_session_id (como routes.py:442)
            test_cv.set('CV_VALUE_123')
            test_tl.value = 'TL_VALUE_123'

            # Simula can_use_tool sendo chamado como callback
            async def simulated_callback():
                cv_read = test_cv.get()
                tl_read = getattr(test_tl, 'value', 'NOT_SET')
                return cv_read, tl_read

            # Teste 1: await direto (como SDK provavelmente faz)
            cv1, tl1 = await simulated_callback()

            # Teste 2: via asyncio.create_task (se SDK criar task)
            task = asyncio.create_task(simulated_callback())
            cv2, tl2 = await task

            # Teste 3: via loop.run_in_executor (se SDK usar thread pool)
            loop = asyncio.get_running_loop()

            def sync_callback():
                cv_r = test_cv.get()
                tl_r = getattr(test_tl, 'value', 'NOT_SET')
                return cv_r, tl_r

            cv3, tl3 = await loop.run_in_executor(None, sync_callback)

            result_queue.put({
                'await_direct': {'contextvar': cv1, 'threading_local': tl1},
                'create_task': {'contextvar': cv2, 'threading_local': tl2},
                'run_in_executor': {'contextvar': cv3, 'threading_local': tl3},
                'thread_name': threading.current_thread().name,
                'thread_id': threading.get_ident(),
            })

        asyncio.run(async_test())

    thread = threading.Thread(target=run_in_daemon, daemon=True)
    thread.start()
    thread.join(timeout=5.0)

    if result_queue.empty():
        return jsonify({'error': 'Thread timeout — teste falhou'}), 500

    results = result_queue.get()

    # Análise
    # NOTA: run_in_executor usa OUTRA thread — ContextVar NÃO propaga para threads filhas
    # (comportamento documentado em PEP 567). O SDK NÃO usa run_in_executor para can_use_tool.
    # Os cenários relevantes são await_direct e create_task.
    cv_await = results['await_direct']['contextvar'] == 'CV_VALUE_123'
    cv_task = results['create_task']['contextvar'] == 'CV_VALUE_123'
    cv_executor = results['run_in_executor']['contextvar'] == 'CV_VALUE_123'

    all_cv_ok = cv_await and cv_task  # Cenários relevantes para o SDK
    all_tl_ok = all(
        results[k]['threading_local'] == 'TL_VALUE_123'
        for k in ['await_direct', 'create_task']
    )

    return jsonify({
        'contextvar_works_everywhere': all_cv_ok,
        'contextvar_executor_propagates': cv_executor,  # Informativo (não bloqueia)
        'threading_local_works_same_thread': all_tl_ok,
        'details': results,
        'conclusion': (
            'ContextVar é seguro para substituir threading.local'
            if all_cv_ok else
            'ATENÇÃO: ContextVar NÃO funciona em algum cenário — NÃO migrar'
        ),
        'nota': (
            'run_in_executor usa thread separada — ContextVar NÃO propaga '
            '(PEP 567). SDK usa await direto, não executor.'
        ),
    })


@agente_bp.route('/api/async-stream-test', methods=['GET'])
@login_required
async def async_stream_test():
    """
    Fase 3 (Protótipo): Testa async generator SSE com Flask 3.1 + Gunicorn gthread.

    Simula o padrão da Fase 3 completa com heartbeats + delay + eventos.
    NÃO modifica a rota /api/chat — endpoint isolado para validação.
    """
    from .config.feature_flags import USE_ASYNC_STREAMING
    if not USE_ASYNC_STREAMING:
        return jsonify({'error': 'ASYNC_STREAMING não habilitado'}), 400

    async def generate():
        import asyncio as _asyncio
        yield _sse_event('start', {'message': 'Protótipo async SSE'})

        for i in range(5):
            await _asyncio.sleep(2)  # Simula SDK event delay
            yield _sse_event('text', {'content': f'Evento {i+1}/5'})

            # Heartbeat inline
            yield _sse_event('heartbeat', {'timestamp': agora_utc_naive().isoformat()})

        yield _sse_event('done', {'message': 'Protótipo concluído'})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


# =============================================================================
# D7: AGENT INTELLIGENCE REPORT — Bridge Agent SDK <-> Claude Code
# =============================================================================

@agente_bp.route('/api/intelligence-report', methods=['POST'])
def save_intelligence_report():
    """
    Persiste relatorio de inteligencia do agente (D7 do cron semanal).

    POST /agente/api/intelligence-report
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Body (JSON):
        {
            "report_date": "2026-03-28",
            "health_score": 78.0,
            "friction_score": 23.0,
            "recommendation_count": 3,
            "sessions_analyzed": 45,
            "report_json": {...},
            "report_markdown": "# Agent Intelligence Report...",
            "backlog_json": [...]
        }

    Autenticacao via CRON_API_KEY (env var no Render).
    Upsert: se ja existe relatorio para a data, atualiza.
    Backlog: o cron D7 faz o merge completo antes de enviar — server persiste como esta.
    """
    import hmac

    # ── Autenticacao ──
    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        logger.error("[D7] CRON_API_KEY nao configurada no servidor")
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        logger.warning("[D7] Tentativa com chave invalida")
        return jsonify({'error': 'Nao autorizado'}), 401

    # ── Parse body ──
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Body JSON obrigatorio'}), 400

    required = ['report_date', 'report_json', 'report_markdown']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Campos obrigatorios ausentes: {missing}'}), 400

    try:
        from datetime import date as date_type
        report_date = date_type.fromisoformat(data['report_date'])
    except (ValueError, TypeError):
        return jsonify({'error': 'report_date deve ser formato YYYY-MM-DD'}), 400

    # ── Validar campos numericos ──
    try:
        health_score = float(data.get('health_score', 0))
        friction_score = float(data.get('friction_score', 0))
        recommendation_count = int(data.get('recommendation_count', 0))
        sessions_analyzed = int(data.get('sessions_analyzed', 0))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Campos numericos invalidos: {e}'}), 400

    # Backlog: cron D7 ja fez merge + auto-escalate — server persiste como esta
    backlog = data.get('backlog_json', [])
    if not isinstance(backlog, list):
        backlog = []

    # ── Upsert ──
    try:
        from .models import AgentIntelligenceReport

        report = AgentIntelligenceReport.upsert(
            report_date=report_date,
            health_score=health_score,
            friction_score=friction_score,
            recommendation_count=recommendation_count,
            sessions_analyzed=sessions_analyzed,
            report_json=data['report_json'],
            report_markdown=data['report_markdown'],
            backlog_json=backlog,
        )

        db.session.flush()
        db.session.commit()

        logger.info(
            f"[D7] Relatorio {report_date} salvo: "
            f"score={report.health_score}, recs={report.recommendation_count}, "
            f"sessoes={report.sessions_analyzed}, backlog={len(backlog)}"
        )

        return jsonify({
            'status': 'ok',
            'report_id': report.id,
            'report_date': str(report.report_date),
            'backlog_items': len(backlog),
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[D7] Erro ao salvar relatorio: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@agente_bp.route('/api/intelligence-report/latest', methods=['GET'])
@login_required
def get_latest_intelligence_report():
    """
    Retorna o relatorio de inteligencia mais recente.

    GET /agente/api/intelligence-report/latest
    Query params:
        format: json (default) | markdown

    Usado pelo dashboard de insights e para consulta direta.
    """
    try:
        from .models import AgentIntelligenceReport

        report = AgentIntelligenceReport.get_latest()
        if not report:
            return jsonify({'error': 'Nenhum relatorio disponivel'}), 404

        fmt = request.args.get('format', 'json')
        if fmt == 'markdown':
            return Response(report.report_markdown, mimetype='text/markdown')

        return jsonify({
            'report_date': str(report.report_date),
            'health_score': float(report.health_score or 0),
            'friction_score': float(report.friction_score or 0),
            'recommendation_count': report.recommendation_count,
            'sessions_analyzed': report.sessions_analyzed,
            'report_json': report.report_json,
            'backlog_json': report.backlog_json,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'updated_at': report.updated_at.isoformat() if report.updated_at else None,
        })

    except Exception as e:
        logger.error(f"[D7] Erro ao buscar relatorio: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


# =========================================================================
# D8: IMPROVEMENT DIALOGUE (Agent SDK <-> Claude Code)
# =========================================================================

@agente_bp.route('/api/improvement-dialogue', methods=['POST'])
@csrf.exempt
def save_improvement_dialogue():
    """
    Persiste resposta do Claude Code ao dialogo de melhoria (D8 cron diario).

    POST /agente/api/improvement-dialogue
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Body (JSON):
        {
            "suggestion_key": "IMP-2026-03-31-001",
            "version": 2,
            "author": "claude_code",
            "status": "responded|rejected",
            "description": "Avaliacao/justificativa",
            "implementation_notes": "O que foi feito ou por que rejeitou",
            "affected_files": ["app/agente/prompts/system_prompt.md"],
            "auto_implemented": false
        }

    Autenticacao via CRON_API_KEY (mesma do D7).
    """
    import hmac

    # ── Autenticacao ──
    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        logger.error("[D8] CRON_API_KEY nao configurada no servidor")
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        logger.warning("[D8] Tentativa com chave invalida")
        return jsonify({'error': 'Nao autorizado'}), 401

    # ── Parse body ──
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Body JSON obrigatorio'}), 400

    required = ['suggestion_key', 'version', 'author', 'status', 'description']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Campos obrigatorios ausentes: {missing}'}), 400

    # Validacoes
    suggestion_key = data['suggestion_key']
    version = int(data.get('version', 2))
    author = data['author']
    status = data['status']

    if author not in ('claude_code', 'agent_sdk'):
        return jsonify({'error': f'author invalido: {author}'}), 400

    valid_statuses = ('responded', 'rejected', 'verified', 'needs_revision', 'closed')
    if status not in valid_statuses:
        return jsonify({'error': f'status invalido: {status}'}), 400

    if version < 2 or version > 3:
        return jsonify({'error': 'version deve ser 2 ou 3'}), 400

    # ── Upsert ──
    try:
        from .models import AgentImprovementDialogue

        response_entry = AgentImprovementDialogue.upsert_response(
            suggestion_key=suggestion_key,
            version=version,
            author=author,
            status=status,
            description=data['description'],
            implementation_notes=data.get('implementation_notes'),
            affected_files=data.get('affected_files'),
            auto_implemented=data.get('auto_implemented', False),
        )

        db.session.flush()
        db.session.commit()

        logger.info(
            f"[D8] Resposta salva: {suggestion_key} v{version} "
            f"status={status} auto={data.get('auto_implemented', False)}"
        )

        return jsonify({
            'status': 'ok',
            'id': response_entry.id,
            'suggestion_key': suggestion_key,
            'version': version,
        }), 200

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 404

    except Exception as e:
        db.session.rollback()
        logger.error(f"[D8] Erro ao salvar resposta: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@agente_bp.route('/api/improvement-dialogue/pending', methods=['GET'])
def get_pending_improvements():
    """
    Retorna sugestoes pendentes para avaliacao.

    GET /agente/api/improvement-dialogue/pending
    Headers:
        X-Cron-Key: <CRON_API_KEY>
    Query params:
        limit: max itens (default 10)
    """
    import hmac

    cron_key = os.environ.get('CRON_API_KEY', '')
    if not cron_key:
        return jsonify({'error': 'Servico nao configurado'}), 500

    request_key = request.headers.get('X-Cron-Key', '')
    if not hmac.compare_digest(request_key, cron_key):
        return jsonify({'error': 'Nao autorizado'}), 401

    try:
        from .models import AgentImprovementDialogue

        limit = int(request.args.get('limit', 10))
        pending = AgentImprovementDialogue.get_pending_suggestions(limit=limit)

        items = []
        for p in pending:
            items.append({
                'id': p.id,
                'suggestion_key': p.suggestion_key,
                'version': p.version,
                'category': p.category,
                'severity': p.severity,
                'title': p.title,
                'description': p.description,
                'evidence_json': p.evidence_json,
                'source_session_ids': p.source_session_ids,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            })

        return jsonify({
            'count': len(items),
            'items': items,
        })

    except Exception as e:
        logger.error(f"[D8] Erro ao buscar pendentes: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
