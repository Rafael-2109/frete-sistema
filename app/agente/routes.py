"""
Rotas Flask do Agente.

Implementação conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

FEAT-030: Histórico de Mensagens Persistente
- Mensagens salvas no banco (campo data JSONB)
- Heartbeats para manter conexão viva no Render
- Tratamento de sessão expirada no SDK
- Endpoint para buscar histórico

FEAT-031: Sistema de Hooks para Memória Persistente
- PRE-HOOK: Carrega memórias do usuário antes de enviar ao SDK
- POST-HOOK: Detecta padrões e preferências após resposta
- TOOL HOOKS: Instrumenta tool calls para analytics
- FEEDBACK: Processa feedback do usuário

Endpoints:
- GET  /agente/              - Página de chat
- POST /agente/api/chat      - Chat com streaming (SSE)
- GET  /agente/api/health    - Health check
- GET  /agente/api/sessions  - Lista sessões do usuário
- GET  /agente/api/sessions/<id>/messages - Histórico de mensagens (FEAT-030)
- DELETE /agente/api/sessions/<id> - Excluir sessão
- PUT  /agente/api/sessions/<id>/rename - Renomear sessão
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
from datetime import datetime
from typing import Generator, Optional, List, Dict, Any
from werkzeug.utils import secure_filename

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context, send_file, current_app
)
from flask_login import login_required, current_user

from . import agente_bp
from app import db

# Configuração de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# FEAT-030: Configuração de heartbeat
HEARTBEAT_INTERVAL_SECONDS = 10  # Envia heartbeat a cada 10s (reduzido de 20s)

# Timeout global do stream (9 minutos - deixa 1 min de margem antes do timeout do Render)
MAX_STREAM_DURATION_SECONDS = 540

# FIX: Timeout de inatividade do SDK - se não receber eventos em X segundos, considera travado
# Este é o timeout CURTO para detectar quando o SDK para de emitir eventos
SDK_INACTIVITY_TIMEOUT_SECONDS = 90  # 90 segundos sem eventos reais = travado

# Erros conhecidos de sessão expirada
SDK_SESSION_EXPIRED_ERRORS = [
    'No conversation found',
    'session not found',
    'Session expired',
    'Control request timeout: initialize',
]

logger = logging.getLogger(__name__)


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
        "model": "claude-sonnet-4-5-20250929",
        "thinking_enabled": false,
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
        thinking_enabled = data.get('thinking_enabled', False)
        plan_mode = data.get('plan_mode', False)
        files = data.get('files', [])

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        # Log
        files_info = f" | Arquivos: {len(files)}" if files else ""
        logger.info(
            f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}' | "
            f"Modelo: {model or 'default'} | Thinking: {thinking_enabled} | "
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
                thinking_enabled=thinking_enabled,
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


def _stream_chat_response(
    message: str,
    original_message: str,
    user_id: int,
    user_name: str,
    session_id: str = None,
    model: str = None,
    thinking_enabled: bool = False,
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
        thinking_enabled: Extended Thinking
        plan_mode: Modo somente-leitura
        image_files: Lista de dicts com imagens em base64 para Vision API

    Yields:
        Eventos SSE formatados
    """
    from .sdk import get_client, get_cost_tracker
    from .config.permissions import can_use_tool
    from .models import AgentSession
    from .hooks import get_memory_agent
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
        'context_injection': '',
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
            memory_agent = get_memory_agent(app)
            processed_message_ids = set()

            # FEAT-030: Busca sessão existente para obter sdk_session_id
            sdk_session_id = None
            our_session_id = session_id

            with app.app_context():
                if session_id:
                    session = AgentSession.get_by_session_id(session_id)
                    if session:
                        sdk_session_id = session.get_sdk_session_id()
                        logger.info(f"[AGENTE] Sessão encontrada: {session_id[:8]}... SDK: {sdk_session_id[:8] if sdk_session_id else 'None'}")

            # FEAT-031: Se não temos session_id, criar novo agora para os hooks
            if not our_session_id:
                our_session_id = str(uuid.uuid4())
                response_state['our_session_id'] = our_session_id

            try:
                # =============================================================
                # PRE-HOOK: Subagente Haiku recupera memórias relevantes
                # =============================================================
                context_injection = ""
                try:
                    context_injection = memory_agent.get_relevant_context(user_id, message)
                    response_state['context_injection'] = context_injection

                    if context_injection:
                        logger.info(f"[AGENTE] MEMORIA: Contexto injetado ({len(context_injection)} chars)")

                except Exception as hook_error:
                    logger.warning(f"[AGENTE] PRE-HOOK falhou (continuando sem contexto): {hook_error}")

                # FEAT-030: Prepara prompt com contexto se necessário
                prompt_to_send = message

                # Se não temos sdk_session_id (sessão expirou ou é nova),
                # injeta histórico de mensagens anteriores como contexto
                if not sdk_session_id and session_id:
                    with app.app_context():
                        session = AgentSession.get_by_session_id(session_id)
                        if session:
                            previous_messages = session.get_messages_for_context()
                            if previous_messages:
                                # Formata histórico para injetar no prompt
                                history_text = _format_messages_as_context(previous_messages)
                                # C5: Compactar se contexto exceder threshold
                                history_text = _compact_context_if_needed(history_text)
                                prompt_to_send = f"{history_text}\n\n[NOVA MENSAGEM DO USUÁRIO]\n{message}"
                                logger.info(f"[AGENTE] Injetando {len(previous_messages)} mensagens como contexto")

                # FEAT-031: Injeta contexto de memória do usuário no prompt
                if context_injection:
                    prompt_to_send = f"[CONTEXTO DO USUÁRIO]\n{context_injection}\n\n{prompt_to_send}"

                logger.info(f"[AGENTE] Chamando SDK | sdk_session_id: {sdk_session_id[:8] if sdk_session_id else 'Nova'} | images: {len(image_files) if image_files else 0}")

                async for event in client.stream_response(
                    prompt=prompt_to_send,
                    session_id=sdk_session_id,
                    user_name=user_name,
                    can_use_tool=can_use_tool,
                    model=model,
                    thinking_enabled=thinking_enabled,
                    plan_mode=plan_mode,
                    user_id=user_id,  # Para Memory Tool
                    image_files=image_files,  # FEAT-032: Imagens para Vision API
                ):
                    # Evento de inicialização
                    if event.type == 'init':
                        new_sdk_session_id = event.content.get('session_id')
                        response_state['sdk_session_id'] = new_sdk_session_id

                        # FEAT-030: Se não tínhamos session_id, criar novo
                        if not response_state['our_session_id']:
                            response_state['our_session_id'] = str(uuid.uuid4())

                        event_queue.put(_sse_event('init', {
                            'session_id': response_state['our_session_id'],
                            'sdk_session_id': new_sdk_session_id,
                        }))
                        continue

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

                        # FEAT-031: Registra erros de tools para post-hook
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
                        # FEAT-002: Repassa thinking block para frontend
                        event_queue.put(_sse_event('thinking', {'content': event.content}))

                    elif event.type == 'todos':
                        todos = event.content.get('todos', [])
                        if todos:
                            event_queue.put(_sse_event('todos', {'todos': todos}))

                    elif event.type == 'error':
                        response_state['error_message'] = event.content
                        event_queue.put(_sse_event('error', {'message': event.content}))

                    elif event.type == 'done':
                        message_id = event.metadata.get('message_id', '') or str(datetime.utcnow().timestamp())
                        response_state['input_tokens'] = event.content.get('input_tokens', 0)
                        response_state['output_tokens'] = event.content.get('output_tokens', 0)
                        cost_usd = event.content.get('total_cost_usd', 0)

                        if message_id not in processed_message_ids:
                            processed_message_ids.add(message_id)
                            cost_tracker.record_cost(
                                message_id=message_id,
                                input_tokens=response_state['input_tokens'],
                                output_tokens=response_state['output_tokens'],
                                session_id=response_state['sdk_session_id'],
                                user_id=user_id,
                            )

                        # =============================================================
                        # POST-HOOK: Subagente Haiku analisa e salva padrões/correções
                        # =============================================================
                        try:
                            post_result = memory_agent.analyze_and_save(
                                user_id=user_id,
                                prompt=message,
                                response=response_state['full_text'],
                            )

                            if post_result.get('action') == 'saved':
                                memory_type = post_result.get('type', 'info')
                                memory_category = post_result.get('category', '')
                                logger.info(f"[AGENTE] MEMORIA: Salvo {memory_type} em {post_result.get('path')}")

                                # FEAT-031: Feedback visual discreto para o frontend
                                event_queue.put(_sse_event('memory_saved', {
                                    'type': memory_type,
                                    'category': memory_category,
                                    'message': _get_memory_feedback_message(memory_type, memory_category),
                                }))

                        except Exception as hook_error:
                            logger.warning(f"[AGENTE] POST-HOOK falhou: {hook_error}")

                        # Evento done
                        event_queue.put(_sse_event('done', {
                            'session_id': response_state['our_session_id'],
                            'input_tokens': response_state['input_tokens'],
                            'output_tokens': response_state['output_tokens'],
                            'cost_usd': cost_usd,
                        }))

            except Exception as e:
                error_str = str(e)
                logger.error(f"[AGENTE] Erro no async stream: {error_str}", exc_info=True)

                # FEAT-030: Detecta sessão expirada
                for expired_error in SDK_SESSION_EXPIRED_ERRORS:
                    if expired_error.lower() in error_str.lower():
                        response_state['session_expired'] = True
                        logger.warning(f"[AGENTE] Sessão SDK expirada detectada: {expired_error}")
                        break

                response_state['error_message'] = error_str
                event_queue.put(_sse_event('error', {
                    'message': error_str,
                    'session_expired': response_state['session_expired'],
                }))

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

        except Exception as e:
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
                    yield _sse_event('heartbeat', {'timestamp': datetime.utcnow().isoformat()})
                    last_heartbeat = current_time
                    logger.debug(f"[AGENTE] Heartbeat enviado (empty count: {consecutive_empty})")

        # Aguarda thread finalizar com timeout maior (10s)
        thread.join(timeout=10.0)

        if thread.is_alive():
            logger.warning("[AGENTE] Thread ainda ativa após timeout de 10s")

        # FEAT-030: Salva mensagens no banco após streaming completo
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
        )

        logger.info("[AGENTE] Thread finalizada e mensagens salvas")

    except Exception as e:
        logger.error(f"[AGENTE] Erro no streaming: {e}", exc_info=True)
        yield _sse_event('error', {'message': str(e)})


def _sse_event(event_type: str, data: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_memory_feedback_message(memory_type: str, category: str) -> str:
    """
    FEAT-031: Gera mensagem de feedback amigável quando memória é salva.

    Args:
        memory_type: Tipo da memória (comando, correcao, preferencia, regra, padrao, fato)
        category: Categoria (explicito, comunicacao, negocio, workflow, usuario)

    Returns:
        Mensagem amigável para exibir ao usuário
    """
    # Mensagens baseadas no tipo
    type_messages = {
        'comando': '💾 Anotado!',
        'correcao': '💾 Correção anotada',
        'preferencia': '💾 Preferência salva',
        'regra': '💾 Regra registrada',
        'padrao': '💾 Padrão aprendido',
        'fato': '💾 Informação salva',
    }

    # Fallback por categoria se tipo não mapeado
    category_messages = {
        'explicito': '💾 Anotado!',
        'comunicacao': '💾 Preferência salva',
        'negocio': '💾 Regra registrada',
        'workflow': '💾 Padrão aprendido',
        'usuario': '💾 Informação salva',
    }

    message = type_messages.get(memory_type)
    if not message:
        message = category_messages.get(category, '💾 Lembrei disso')

    return message


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
    """
    if not our_session_id:
        logger.warning("[AGENTE] Não foi possível salvar: session_id não definido")
        return

    try:
        from .models import AgentSession

        with app.app_context():
            session, created = AgentSession.get_or_create(
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

            # Calcula custo aproximado (valores do Claude)
            cost_usd = _calculate_cost(model, input_tokens, output_tokens)
            session.total_cost_usd = float(session.total_cost_usd or 0) + cost_usd

            db.session.commit()
            logger.debug(f"[AGENTE] Mensagens salvas na sessão {our_session_id[:8]}...")

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar mensagens: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception:
            pass


def _format_messages_as_context(messages: List[Dict[str, Any]]) -> str:
    """
    FEAT-030: Formata mensagens anteriores como contexto para injetar no prompt.

    Quando a sessão SDK expira, precisamos injetar o histórico manualmente
    para que o Claude tenha contexto da conversa anterior.

    Args:
        messages: Lista de mensagens do histórico

    Returns:
        String formatada com o histórico
    """
    if not messages:
        return ""

    lines = ["[HISTÓRICO DA CONVERSA ANTERIOR]", ""]

    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        # Trunca mensagens muito longas para não estourar contexto
        if len(content) > 2000:
            content = content[:2000] + "... [truncado]"

        if role == 'user':
            lines.append(f"USUÁRIO: {content}")
        else:
            lines.append(f"ASSISTENTE: {content}")
        lines.append("")

    lines.append("[FIM DO HISTÓRICO]")
    lines.append("")

    return "\n".join(lines)


def _compact_context_if_needed(messages_context: str) -> str:
    """
    C5: Compaction manual de contexto via Haiku.

    Quando o contexto injetado excede o threshold de tokens,
    usa Claude Haiku (20x mais barato) para sumarizar preservando
    informações críticas de logística.

    FONTE: Memory Cookbook Anthropic — threshold produção 30-40k tokens.

    Args:
        messages_context: Texto do contexto formatado

    Returns:
        Contexto original ou compactado
    """
    from .config.feature_flags import USE_MANUAL_COMPACTION, COMPACTION_TOKEN_THRESHOLD

    if not USE_MANUAL_COMPACTION:
        return messages_context

    # Estimativa de tokens (4 chars ~= 1 token)
    estimated_tokens = len(messages_context) // 4
    if estimated_tokens < COMPACTION_TOKEN_THRESHOLD:
        return messages_context

    logger.info(
        f"[COMPACTION] Contexto com ~{estimated_tokens} tokens excede "
        f"threshold {COMPACTION_TOKEN_THRESHOLD}. Compactando..."
    )

    try:
        import anthropic
        client = anthropic.Anthropic()
        summary_response = client.messages.create(
            model="claude-haiku-4-5-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": (
                    "Resuma a conversa abaixo preservando OBRIGATORIAMENTE:\n"
                    "1. Números de pedido/NF consultados e seus status atuais\n"
                    "2. Resultados de consultas (estoque, separações, entregas, valores)\n"
                    "3. Decisões tomadas pelo usuário\n"
                    "4. Memórias carregadas e preferências aplicadas\n"
                    "5. Próximas ações pendentes\n\n"
                    "DESCARTE: detalhes de tool calls intermediárias, outputs completos "
                    "de scripts, dados tabulares já apresentados ao usuário.\n\n"
                    f"Conversa:\n{messages_context}"
                )
            }]
        )

        compacted = summary_response.content[0].text
        compacted_tokens = len(compacted) // 4
        savings = estimated_tokens - compacted_tokens
        logger.info(
            f"[COMPACTION] Reduzido de ~{estimated_tokens} para "
            f"~{compacted_tokens} tokens (economia: {savings})"
        )

        return f"[CONTEXTO COMPACTADO]\n{compacted}\n[FIM DO CONTEXTO COMPACTADO]"

    except Exception as e:
        logger.warning(f"[COMPACTION] Falha na compactação: {e}. Usando contexto original.")
        return messages_context


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calcula custo aproximado baseado no modelo."""
    # Preços aproximados por 1M tokens (dezembro 2025)
    pricing = {
        'claude-sonnet-4-5-20250929': {'input': 3.0, 'output': 15.0},
        'claude-opus-4-5-20251101': {'input': 5.0, 'output': 25.0},
        'claude-haiku-4-5-20251001': {'input': 0.25, 'output': 1.25},
    }

    model_pricing = pricing.get(model, pricing['claude-sonnet-4-5-20250929'])
    cost = (input_tokens * model_pricing['input'] / 1_000_000) + \
           (output_tokens * model_pricing['output'] / 1_000_000)
    return cost


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

        return jsonify({
            'success': True,
            'session_id': session_id,
            'title': session.title,
            'messages': messages,
            'total_tokens': session.get_total_tokens(),
        })

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
    """Health check do serviço."""
    try:
        from .sdk import get_client
        from .config import get_settings

        settings = get_settings()
        client = get_client()
        health = client.health_check()

        return jsonify({
            'success': True,
            'status': health.get('status', 'unknown'),
            'model': settings.model,
            'api_connected': health.get('api_connected', False),
            'sdk': 'claude-agent-sdk',
            'timestamp': datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro no health check: {e}")
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
        from datetime import datetime, timezone

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
                path = f"/memories/corrections/feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                content = f"""<correction>
<text>{correction_text}</text>
<context>{feedback_data.get('context', '')}</context>
<source>user_feedback</source>
<created_at>{datetime.now(timezone.utc).isoformat()}</created_at>
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
<updated_at>{datetime.now(timezone.utc).isoformat()}</updated_at>
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
