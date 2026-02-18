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
from app import db
from app.utils.timezone import agora_utc_naive
# Configuração de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# FEAT-030: Configuração de heartbeat
HEARTBEAT_INTERVAL_SECONDS = 10  # Envia heartbeat a cada 10s (reduzido de 20s)

# Cache de health check (TTL 30s) — evita chamada API real a cada request
_health_cache = {'result': None, 'timestamp': 0}
_HEALTH_CACHE_TTL = 30  # segundos

# Timeout global do stream (9 minutos - deixa 1 min de margem antes do timeout do Render)
MAX_STREAM_DURATION_SECONDS = 540

# FIX: Timeout de inatividade do SDK - se não receber eventos em X segundos, considera travado
# Este é o timeout CURTO para detectar quando o SDK para de emitir eventos
# Aumentado para 240s (4 min) — skills complexas (SQL analítico, API Odoo, cotação de frete)
# podem demorar vários minutos sem emitir eventos enquanto processam
SDK_INACTIVITY_TIMEOUT_SECONDS = 240

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
        # Effort level com backward compat para clients antigos
        effort_level = data.get('effort_level', None)
        if effort_level is None:
            # Backward compat: clients antigos enviam thinking_enabled
            thinking_enabled = data.get('thinking_enabled', False)
            effort_level = 'high' if thinking_enabled else 'off'
        plan_mode = data.get('plan_mode', False)
        files = data.get('files', [])

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        # Log
        files_info = f" | Arquivos: {len(files)}" if files else ""
        logger.info(
            f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}' | "
            f"Modelo: {model or 'default'} | Effort: {effort_level} | "
            f"Plan: {plan_mode}{files_info}"
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
):
    """
    Streaming via query() + resume — self-contained, sem pool.

    ARQUITETURA v2:
    - Cada chamada usa query() standalone (sem ClaudeSDKClient, sem SessionPool)
    - resume=sdk_session_id restaura contexto da conversa anterior
    - Sem locks, sem connect/disconnect, sem retry de recreate
    """
    # Buscar sdk_session_id do banco para resume
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
        except Exception as e:
            logger.warning(f"[AGENTE] Erro ao buscar sdk_session_id do DB: {e}")

    # Definir user_id no contexto para as MCP Memory Tools
    try:
        from .tools.memory_mcp_tool import set_current_user_id
        set_current_user_id(user_id)
    except ImportError:
        pass

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
                    if tool_name not in response_state['tools_used']:
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

                    # Evento done
                    event_queue.put(_sse_event('done', {
                        'session_id': response_state['our_session_id'],
                        'input_tokens': response_state['input_tokens'],
                        'output_tokens': response_state['output_tokens'],
                        'cost_usd': cost_usd,
                    }))

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
            )

            # =============================================================
            # P1-1: Prompt Suggestions (best-effort, após done)
            # Gera 2-3 sugestões contextuais via Haiku (~300-800ms)
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
                    logger.error(f"[AGENTE] async_stream timeout após {timeout_seconds}s")
                    event_queue.put(_sse_event('error', {
                        'message': 'Tempo limite interno excedido. A operação demorou muito.',
                        'timeout': True
                    }))

            asyncio.run(async_stream_with_timeout())
            logger.info("[AGENTE] asyncio.run() completado com sucesso")

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

        # FEAT-030: Loop com heartbeats + timeout global + detecção de thread morta
        last_heartbeat = time.time()
        last_event_time = time.time()  # Rastrear último evento recebido
        stream_start_time = time.time()
        event_count = 0
        consecutive_empty = 0  # Contador de timeouts consecutivos sem eventos

        while True:
            # SEGURANÇA: Timeout global para evitar travamento indefinido
            elapsed = time.time() - stream_start_time
            if elapsed > MAX_STREAM_DURATION_SECONDS:
                logger.warning(f"[AGENTE] Stream timeout após {elapsed:.1f}s")
                yield _sse_event('error', {'message': 'Tempo limite excedido (9 min)'})
                break

            try:
                # Timeout para permitir heartbeats (usa o menor entre heartbeat e tempo restante)
                remaining_time = MAX_STREAM_DURATION_SECONDS - elapsed
                queue_timeout = min(HEARTBEAT_INTERVAL_SECONDS, remaining_time, 30)  # Max 30s
                event = event_queue.get(timeout=queue_timeout)

                if event is None:  # Fim do stream
                    logger.info(f"[AGENTE] Fim do stream, {event_count} eventos processados")
                    break

                event_count += 1
                last_event_time = time.time()
                consecutive_empty = 0  # Reset contador
                yield event

                # FIX-7: Fechar SSE após evento 'done' — não esperar None indefinidamente.
                # O done indica que o agente terminou. Aguarda brevemente por suggestions.
                if isinstance(event, str) and 'event: done\n' in event:
                    # Best-effort: espera até 3s por evento de suggestions
                    try:
                        remaining = event_queue.get(timeout=3)
                        if remaining is not None:
                            yield remaining
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

                # =================================================================
                # DETECÇÃO DE SDK TRAVADO (INATIVIDADE)
                # =================================================================
                # Se ficou muito tempo sem eventos REAIS da fila, o SDK está
                # travado. Nota: heartbeats NÃO atualizam last_event_time porque
                # são gerados aqui no except Empty, não vêm da fila.
                # =================================================================
                time_since_last_event = time.time() - last_event_time
                if time_since_last_event > SDK_INACTIVITY_TIMEOUT_SECONDS:
                    logger.warning(
                        f"[AGENTE] SDK inativo há {time_since_last_event:.0f}s - "
                        f"forçando timeout (thread viva mas sem progresso)"
                    )
                    yield _sse_event('error', {
                        'message': 'O processamento parece ter travado. Tente novamente.',
                        'sdk_stalled': True,
                        'inactivity_seconds': int(time_since_last_event)
                    })
                    break

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


def _sse_event(event_type: str, data: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
            # P0-2: Sumarização Estruturada (best-effort, após commit)
            # Roda APÓS mensagens salvas — falha não afeta salvamento
            # =============================================================
            try:
                from .config.feature_flags import USE_SESSION_SUMMARY, SESSION_SUMMARY_THRESHOLD

                if USE_SESSION_SUMMARY and session.needs_summarization(SESSION_SUMMARY_THRESHOLD):
                    logger.info(
                        f"[AGENTE] Trigger sumarização para sessão {our_session_id[:8]}... "
                        f"(msgs={session.message_count}, threshold={SESSION_SUMMARY_THRESHOLD})"
                    )
                    from .services.session_summarizer import summarize_and_save
                    summarize_and_save(
                        app=app,
                        session_id=our_session_id,
                        user_id=user_id,
                    )
            except Exception as summary_error:
                # SILENCIOSO: sumarização falha não deve afetar nada
                logger.warning(f"[AGENTE] Erro na sumarização (ignorado): {summary_error}")

            # =============================================================
            # P1-3: Aprendizado de Padrões (best-effort, após commit)
            # Analisa sessões históricas a cada N sessões do usuário
            # =============================================================
            try:
                from .config.feature_flags import USE_PATTERN_LEARNING, PATTERN_LEARNING_THRESHOLD

                if USE_PATTERN_LEARNING:
                    from .services.pattern_analyzer import should_analyze_patterns, analyze_and_save as analyze_patterns_and_save

                    if should_analyze_patterns(user_id, PATTERN_LEARNING_THRESHOLD):
                        logger.info(
                            f"[AGENTE] Trigger análise de padrões para usuário {user_id} "
                            f"(threshold={PATTERN_LEARNING_THRESHOLD})"
                        )
                        analyze_patterns_and_save(app=app, user_id=user_id)
            except Exception as pattern_error:
                # SILENCIOSO: análise de padrões falha não deve afetar nada
                logger.warning(f"[AGENTE] Erro na análise de padrões (ignorado): {pattern_error}")

            # =============================================================
            # Fase 4: Embedding de turn para busca semântica (best-effort)
            # Roda APÓS padrões — falha não afeta nada anterior
            # =============================================================
            try:
                from .config.feature_flags import USE_SESSION_SEMANTIC_SEARCH
                if USE_SESSION_SEMANTIC_SEARCH and user_message and assistant_message:
                    _embed_session_turn_best_effort(
                        app, our_session_id, user_id,
                        user_message, assistant_message, session
                    )
            except Exception as emb_err:
                logger.debug(f"[AGENTE] Embedding turn falhou (ignorado): {emb_err}")

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar mensagens: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass


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
        assistant_summary = (assistant_message or '')[:500]
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
# API - SDK CLIENT (Interrupt não suportado com query() — mantém endpoint para
# compatibilidade com frontend, retornando resposta informativa)
# =============================================================================

@agente_bp.route('/api/interrupt', methods=['POST'])
@login_required
def api_interrupt():
    """
    Interrupt não suportado na arquitetura query() + resume.

    query() é self-contained (spawna CLI, executa, limpa).
    Não mantém processo persistente para interromper.

    O próximo turno com resume continua de onde parou.
    """
    return jsonify({
        'success': False,
        'error': 'Interrupt não disponível nesta versão. O processamento será concluído automaticamente.',
        'info': 'Arquitetura query() + resume não suporta interrupt. Aguarde a conclusão ou envie nova mensagem.',
    }), 501  # 501 Not Implemented


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

        result = {
            'success': True,
            'status': health.get('status', 'unknown'),
            'model': settings.model,
            'api_connected': health.get('api_connected', False),
            'sdk': 'claude-agent-sdk',
            'mcp_servers': mcp_status,
            'timestamp': agora_utc_naive().isoformat(),
        }

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

        from .sdk.pending_questions import submit_answer

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
