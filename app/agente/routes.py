"""
Rotas Flask do Agente.

Implementação conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

O SDK gerencia sessions automaticamente. Não é necessário session manager customizado.

Endpoints:
- GET  /agente/           - Página de chat
- POST /agente/api/chat   - Chat com streaming (SSE)
- GET  /agente/api/health - Health check
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Generator

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context
)
from flask_login import login_required, current_user

from . import agente_bp

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
# API - CHAT
# =============================================================================

@agente_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """
    Chat com streaming (Server-Sent Events).

    POST /agente/api/chat
    {
        "message": "Tem pedido pendente pro Atacadão?",
        "session_id": "uuid-opcional"  // Para retomar sessão
    }

    Response: text/event-stream

    O SDK gerencia sessions automaticamente:
    - Se session_id não fornecido: cria nova sessão
    - Se session_id fornecido: retoma sessão existente (resume)
    """
    try:
        data = request.get_json()

        if not data or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Campo "message" é obrigatório'
            }), 400

        message = data['message'].strip()
        session_id = data.get('session_id')  # Opcional - SDK cria se não existir

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        logger.info(f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}'")

        return Response(
            stream_with_context(_stream_chat_response(
                message=message,
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
            )),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
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
    user_id: int,
    user_name: str,
    session_id: str = None,
) -> Generator[str, None, None]:
    """
    Gera resposta em streaming (SSE).

    Conforme documentação oficial Anthropic:
    - https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
    - https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
    - https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

    O SDK gerencia sessions automaticamente:
    - Captura session_id no evento 'init'
    - Usa 'resume' para retomar sessions

    Cost tracking usa message.id para deduplicação.

    Yields:
        Eventos SSE formatados
    """
    from .sdk import get_client, get_cost_tracker
    from .config.permissions import can_use_tool
    from queue import Queue
    from threading import Thread

    # Queue para comunicação thread-safe entre async e sync
    event_queue = Queue()

    def run_async_stream():
        """Executa o stream assíncrono em uma thread separada."""
        logger.info("[AGENTE] Thread iniciada para async stream")

        async def async_stream():
            logger.info("[AGENTE] Iniciando async_stream()")
            client = get_client()
            cost_tracker = get_cost_tracker()
            sdk_session_id = session_id
            processed_message_ids = set()

            try:
                logger.info(f"[AGENTE] Chamando client.stream_response com prompt: {message[:50]}...")
                async for event in client.stream_response(
                    prompt=message,
                    session_id=sdk_session_id,
                    user_name=user_name,
                    can_use_tool=can_use_tool,
                ):
                    logger.info(f"[AGENTE] Evento recebido: {event.type}")
                    # Evento de inicialização - captura session_id do SDK
                    if event.type == 'init':
                        sdk_session_id = event.content.get('session_id')
                        event_queue.put(_sse_event('init', {'session_id': sdk_session_id}))
                        continue

                    if event.type == 'text':
                        event_queue.put(_sse_event('text', {'content': event.content}))

                    elif event.type == 'tool_call':
                        event_queue.put(_sse_event('tool_call', {
                            'tool_name': event.content,
                            'tool_id': event.metadata.get('tool_id')
                        }))

                    elif event.type == 'tool_result':
                        event_queue.put(_sse_event('tool_result', {
                            'tool_name': event.metadata.get('tool_name'),
                            'result': event.content
                        }))

                    elif event.type == 'error':
                        event_queue.put(_sse_event('error', {'message': event.content}))

                    elif event.type == 'done':
                        # Cost Tracking com deduplicação por message.id
                        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking
                        message_id = event.metadata.get('message_id', '') or str(datetime.utcnow().timestamp())

                        if message_id not in processed_message_ids:
                            processed_message_ids.add(message_id)

                            cost_tracker.record_cost(
                                message_id=message_id,
                                input_tokens=event.content.get('input_tokens', 0),
                                output_tokens=event.content.get('output_tokens', 0),
                                session_id=sdk_session_id,
                                user_id=user_id,
                            )

                        event_queue.put(_sse_event('done', {
                            'session_id': sdk_session_id,
                            'input_tokens': event.content.get('input_tokens', 0),
                            'output_tokens': event.content.get('output_tokens', 0),
                            'cost_usd': event.content.get('total_cost_usd', 0),
                        }))

            except Exception as e:
                logger.error(f"[AGENTE] Erro no async stream: {e}", exc_info=True)
                event_queue.put(_sse_event('error', {'message': str(e)}))
            finally:
                logger.info("[AGENTE] async_stream() finalizado, sinalizando fim")
                event_queue.put(None)  # Sinaliza fim

        # Executa o async stream em um novo event loop
        logger.info("[AGENTE] Executando asyncio.run(async_stream())")
        asyncio.run(async_stream())
        logger.info("[AGENTE] asyncio.run() completado")

    try:
        logger.info("[AGENTE] _stream_chat_response iniciado")

        # Inicia streaming
        yield _sse_event('start', {'message': 'Iniciando...'})
        logger.info("[AGENTE] Evento 'start' emitido")

        # Inicia thread para executar async stream
        thread = Thread(target=run_async_stream, daemon=True)
        thread.start()
        logger.info("[AGENTE] Thread iniciada")

        # Consome eventos da queue
        event_count = 0
        while True:
            event = event_queue.get()
            if event is None:  # Fim do stream
                logger.info(f"[AGENTE] Fim do stream, {event_count} eventos processados")
                break
            event_count += 1
            yield event

        thread.join(timeout=1.0)
        logger.info("[AGENTE] Thread finalizada")

    except Exception as e:
        logger.error(f"[AGENTE] Erro no streaming: {e}", exc_info=True)
        yield _sse_event('error', {'message': str(e)})


def _sse_event(event_type: str, data: dict) -> str:
    """Formata evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# =============================================================================
# API - HEALTH
# =============================================================================

@agente_bp.route('/api/health', methods=['GET'])
def api_health():
    """
    Health check do serviço.

    GET /agente/api/health
    """
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
