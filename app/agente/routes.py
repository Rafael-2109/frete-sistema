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
HEARTBEAT_INTERVAL_SECONDS = 20  # Envia heartbeat a cada 20s

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

        # Enriquece mensagem com arquivos
        enriched_message = message
        if files:
            files_context = "\n\n[Arquivos anexados pelo usuário:]\n"
            for f in files:
                files_context += f"- {f.get('name', 'arquivo')} ({f.get('type', 'file')}, {f.get('size', 0)} bytes)\n"
                files_context += f"  URL: {f.get('url', 'N/A')}\n"
            enriched_message = message + files_context

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
) -> Generator[str, None, None]:
    """
    Gera resposta em streaming (SSE).

    FEAT-030: Melhorias:
    - Heartbeats para manter conexão viva
    - Salva mensagens no banco
    - Trata sessão expirada no SDK
    - Acumula texto para salvar resposta completa

    Args:
        message: Mensagem enriquecida (com arquivos)
        original_message: Mensagem original do usuário
        user_id: ID do usuário
        user_name: Nome do usuário
        session_id: Nosso session_id (não do SDK)
        model: Modelo a usar
        thinking_enabled: Extended Thinking
        plan_mode: Modo somente-leitura

    Yields:
        Eventos SSE formatados
    """
    from .sdk import get_client, get_cost_tracker
    from .config.permissions import can_use_tool
    from .models import AgentSession
    from queue import Queue, Empty
    from threading import Thread

    app = current_app._get_current_object()
    event_queue = Queue()

    # FEAT-030: Estado para acumular resposta
    response_state = {
        'full_text': '',
        'tools_used': [],
        'input_tokens': 0,
        'output_tokens': 0,
        'sdk_session_id': None,
        'our_session_id': session_id,
        'session_expired': False,
        'error_message': None,
    }

    def run_async_stream():
        """Executa o stream assíncrono em uma thread separada."""
        logger.info("[AGENTE] Thread iniciada para async stream")

        async def async_stream():
            logger.info("[AGENTE] Iniciando async_stream()")
            client = get_client()
            cost_tracker = get_cost_tracker()
            processed_message_ids = set()

            # FEAT-030: Busca sessão existente para obter sdk_session_id
            sdk_session_id = None

            with app.app_context():
                if session_id:
                    session = AgentSession.get_by_session_id(session_id)
                    if session:
                        sdk_session_id = session.get_sdk_session_id()
                        logger.info(f"[AGENTE] Sessão encontrada: {session_id[:8]}... SDK: {sdk_session_id[:8] if sdk_session_id else 'None'}")

            try:
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
                                prompt_to_send = f"{history_text}\n\n[NOVA MENSAGEM DO USUÁRIO]\n{message}"
                                logger.info(f"[AGENTE] Injetando {len(previous_messages)} mensagens como contexto")

                logger.info(f"[AGENTE] Chamando SDK | sdk_session_id: {sdk_session_id[:8] if sdk_session_id else 'Nova'}")

                async for event in client.stream_response(
                    prompt=prompt_to_send,
                    session_id=sdk_session_id,
                    user_name=user_name,
                    can_use_tool=can_use_tool,
                    model=model,
                    thinking_enabled=thinking_enabled,
                    plan_mode=plan_mode,
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
                        event_queue.put(_sse_event('tool_result', {
                            'tool_name': event.metadata.get('tool_name'),
                            'result': event.content
                        }))

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

            finally:
                logger.info("[AGENTE] async_stream() finalizado")
                event_queue.put(None)  # Sinaliza fim

        asyncio.run(async_stream())
        logger.info("[AGENTE] asyncio.run() completado")

    try:
        logger.info("[AGENTE] _stream_chat_response iniciado")

        # Inicia streaming
        yield _sse_event('start', {'message': 'Iniciando...'})

        # Inicia thread para async stream
        thread = Thread(target=run_async_stream, daemon=True)
        thread.start()

        # FEAT-030: Loop com heartbeats
        last_heartbeat = time.time()
        event_count = 0

        while True:
            try:
                # Timeout para permitir heartbeats
                event = event_queue.get(timeout=HEARTBEAT_INTERVAL_SECONDS)

                if event is None:  # Fim do stream
                    logger.info(f"[AGENTE] Fim do stream, {event_count} eventos processados")
                    break

                event_count += 1
                yield event

            except Empty:
                # FEAT-030: Envia heartbeat para manter conexão viva
                current_time = time.time()
                if current_time - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    yield _sse_event('heartbeat', {'timestamp': datetime.utcnow().isoformat()})
                    last_heartbeat = current_time
                    logger.debug("[AGENTE] Heartbeat enviado")

        thread.join(timeout=2.0)

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
        except:
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
    """Download de arquivo."""
    try:
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, secure_filename(filename))

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename.split('_', 1)[1] if '_' in filename else filename
        )

    except Exception as e:
        logger.error(f"[AGENTE] Erro no download: {e}")
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
