"""
Rotas Flask do Agente.

Implementação conforme documentação oficial Anthropic:
- https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
- https://platform.claude.com/docs/pt-BR/agent-sdk/streaming-vs-single-mode
- https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking

O SDK gerencia sessions automaticamente. Não é necessário session manager customizado.

Endpoints:
- GET  /agente/              - Página de chat
- POST /agente/api/chat      - Chat com streaming (SSE)
- GET  /agente/api/health    - Health check
- GET  /agente/api/sessions  - Lista sessões do usuário (FEAT-011)
- DELETE /agente/api/sessions/<id> - Excluir sessão (FEAT-011)
- PUT  /agente/api/sessions/<id>/rename - Renomear sessão (FEAT-011)
- POST /agente/api/upload    - Upload de arquivo (FEAT-028)
- GET  /agente/api/files/<filename> - Download de arquivo (FEAT-028)
- GET  /agente/api/files     - Lista arquivos da sessão (FEAT-028)
- DELETE /agente/api/files/<filename> - Remove arquivo (FEAT-028)
"""

import logging
import json
import asyncio
import os
import uuid
import base64
import tempfile
import shutil
from datetime import datetime
from typing import Generator
from werkzeug.utils import secure_filename

from flask import (
    request, jsonify, render_template,
    Response, stream_with_context, send_file, current_app
)
from flask_login import login_required, current_user

from . import agente_bp
from app import db

# FEAT-028: Configuração de uploads
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'agente_files')
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

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
        "session_id": "uuid-opcional",
        "model": "claude-sonnet-4-5-20250929",  // FEAT-001: Modelo selecionado
        "thinking_enabled": false               // FEAT-002: Extended Thinking
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

        # FEAT-001: Modelo selecionado pelo usuário
        model = data.get('model')

        # FEAT-002: Extended Thinking
        thinking_enabled = data.get('thinking_enabled', False)

        # FEAT-010: Plan Mode (modo somente-leitura)
        plan_mode = data.get('plan_mode', False)

        # FEAT-028: Arquivos anexados
        files = data.get('files', [])

        user_id = current_user.id
        user_name = getattr(current_user, 'nome', 'Usuário')

        # FEAT-028: Adiciona info de arquivos ao log
        files_info = f" | Arquivos: {len(files)}" if files else ""
        logger.info(f"[AGENTE] {user_name} (ID:{user_id}): '{message[:100]}' | Modelo: {model or 'default'} | Thinking: {thinking_enabled} | Plan: {plan_mode}{files_info}")

        # FEAT-028: Se houver arquivos, enriquece a mensagem
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
    model: str = None,
    thinking_enabled: bool = False,
    plan_mode: bool = False,
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

    Args:
        message: Mensagem do usuário
        user_id: ID do usuário
        user_name: Nome do usuário
        session_id: ID da sessão (opcional)
        model: Modelo a usar (opcional, FEAT-001)
        thinking_enabled: Ativar Extended Thinking (FEAT-002)
        plan_mode: Ativar modo somente-leitura (FEAT-010)

    Yields:
        Eventos SSE formatados
    """
    from flask import current_app
    from .sdk import get_client, get_cost_tracker
    from .config.permissions import can_use_tool
    from queue import Queue
    from threading import Thread

    # FEAT-011: Captura referência ao app ANTES de criar a thread
    # Threads não herdam o contexto Flask, então precisamos passar explicitamente
    app = current_app._get_current_object()

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
                    model=model,                          # FEAT-001: Modelo selecionado
                    thinking_enabled=thinking_enabled,    # FEAT-002: Extended Thinking
                    plan_mode=plan_mode,                  # FEAT-010: Plan Mode
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
                        # FEAT-024: Passa descrição amigável do tool
                        event_queue.put(_sse_event('tool_call', {
                            'tool_name': event.content,
                            'tool_id': event.metadata.get('tool_id'),
                            'description': event.metadata.get('description', '')  # FEAT-024
                        }))

                    elif event.type == 'tool_result':
                        event_queue.put(_sse_event('tool_result', {
                            'tool_name': event.metadata.get('tool_name'),
                            'result': event.content
                        }))

                    # FEAT-024: Evento de todos (TodoWrite)
                    elif event.type == 'todos':
                        todos = event.content.get('todos', [])
                        if todos:
                            event_queue.put(_sse_event('todos', {'todos': todos}))

                    elif event.type == 'error':
                        event_queue.put(_sse_event('error', {'message': event.content}))

                    elif event.type == 'done':
                        # Cost Tracking com deduplicação por message.id
                        # Ref: https://platform.claude.com/docs/pt-BR/agent-sdk/cost-tracking
                        message_id = event.metadata.get('message_id', '') or str(datetime.utcnow().timestamp())
                        input_tokens = event.content.get('input_tokens', 0)
                        output_tokens = event.content.get('output_tokens', 0)
                        cost_usd = event.content.get('total_cost_usd', 0)

                        if message_id not in processed_message_ids:
                            processed_message_ids.add(message_id)

                            cost_tracker.record_cost(
                                message_id=message_id,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                session_id=sdk_session_id,
                                user_id=user_id,
                            )

                        # FEAT-011: Persistir sessão no banco
                        if sdk_session_id:
                            _save_session(
                                app=app,  # Passa o app para usar o context
                                session_id=sdk_session_id,
                                user_id=user_id,
                                message=message,
                                model=model,
                                cost_usd=cost_usd,
                            )

                        event_queue.put(_sse_event('done', {
                            'session_id': sdk_session_id,
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'cost_usd': cost_usd,
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


def _save_session(
    app,
    session_id: str,
    user_id: int,
    message: str = None,
    model: str = None,
    cost_usd: float = 0,
) -> None:
    """
    Salva ou atualiza sessão no banco (FEAT-011).

    Args:
        app: Instância do Flask app (necessário para context em threads)
        session_id: ID da sessão do SDK
        user_id: ID do usuário
        message: Última mensagem
        model: Modelo usado
        cost_usd: Custo em USD
    """
    try:
        from .models import AgentSession

        # FEAT-011: Usa o app passado para criar context (threads não herdam)
        with app.app_context():
            session, created = AgentSession.get_or_create(
                session_id=session_id,
                user_id=user_id,
            )

            session.update_from_response(
                message=message,
                cost_usd=cost_usd,
                model=model,
            )

            db.session.commit()
            logger.debug(f"[AGENTE] Sessão {'criada' if created else 'atualizada'}: {session_id[:8]}...")

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao salvar sessão: {e}")
        try:
            with app.app_context():
                db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"[AGENTE] Erro ao fazer rollback: {rollback_error}")


# =============================================================================
# API - SESSIONS (FEAT-011)
# =============================================================================

@agente_bp.route('/api/sessions', methods=['GET'])
@login_required
def api_list_sessions():
    """
    Lista sessões do usuário.

    GET /agente/api/sessions?limit=20

    Response:
    {
        "success": true,
        "sessions": [
            {
                "id": 1,
                "session_id": "abc123...",
                "title": "Consulta de estoque",
                "message_count": 5,
                "total_cost_usd": 0.0045,
                "last_message": "Qual o estoque...",
                "model": "claude-sonnet-4-5-20250929",
                "created_at": "2025-12-03T10:00:00",
                "updated_at": "2025-12-03T10:05:00"
            }
        ]
    }
    """
    try:
        from .models import AgentSession

        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)  # Máximo 50

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


@agente_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_id: int):
    """
    Exclui uma sessão.

    DELETE /agente/api/sessions/123
    """
    try:
        from .models import AgentSession

        session = AgentSession.query.filter_by(
            id=session_id,
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


@agente_bp.route('/api/sessions/<int:session_id>/rename', methods=['PUT'])
@login_required
def api_rename_session(session_id: int):
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
            id=session_id,
            user_id=current_user.id,
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404

        session.title = new_title[:200]  # Limite de 200 chars
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
# API - FILES (FEAT-028)
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
    """
    Upload de arquivo para a sessão.

    POST /agente/api/upload
    Content-Type: multipart/form-data

    Form fields:
        file: arquivo
        session_id: ID da sessão (opcional)

    Response:
    {
        "success": true,
        "file": {
            "id": "abc123",
            "name": "relatorio.pdf",
            "original_name": "relatorio.pdf",
            "size": 123456,
            "type": "pdf",
            "url": "/agente/api/files/abc123_relatorio.pdf"
        }
    }
    """
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

        # Verifica tamanho
        file.seek(0, 2)  # Vai para o final
        file_size = file.tell()
        file.seek(0)  # Volta para o início

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        session_id = request.form.get('session_id', 'default')
        folder = _get_session_folder(session_id)

        # Gera nome único para evitar conflitos
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
    Download de arquivo.

    GET /agente/api/files/{session_id}/{filename}
    """
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
    """
    Lista arquivos da sessão.

    GET /agente/api/files?session_id=xxx

    Response:
    {
        "success": true,
        "files": [
            {"name": "abc123_file.pdf", "size": 123, "type": "pdf", "url": "..."}
        ]
    }
    """
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
    """
    Remove arquivo da sessão.

    DELETE /agente/api/files/{session_id}/{filename}
    """
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
    """
    Limpa todos os arquivos da sessão.

    POST /agente/api/files/cleanup
    {"session_id": "xxx"}
    """
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
