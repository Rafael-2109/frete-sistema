"""
Rotas da API para o Bot do Microsoft Teams (Azure Function).

Endpoints:
- POST /api/teams/bot/message  - Recebe mensagem do bot e inicia processamento async
- GET  /api/teams/bot/status/<task_id> - Polling de status de uma task
- POST /api/teams/bot/answer   - Recebe resposta de Adaptive Card (AskUserQuestion)
- POST /api/teams/bot/execute  - Executa tarefa confirmada pelo usuario
- GET  /api/teams/bot/health   - Health check
"""

import os
import logging
import functools
import threading
from flask import request, jsonify
from app.teams import teams_bp
from app import csrf

logger = logging.getLogger(__name__)

# API Key para autenticacao do bot Azure Function
TEAMS_BOT_API_KEY = os.environ.get("TEAMS_BOT_API_KEY", "")


# ═══════════════════════════════════════════════════════════════
# AUTENTICACAO
# ═══════════════════════════════════════════════════════════════

def require_bot_api_key(f):
    """
    Decorator que valida X-API-Key header contra TEAMS_BOT_API_KEY.

    Retorna 401 se a chave estiver ausente ou invalida.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not TEAMS_BOT_API_KEY:
            logger.error("[TEAMS-BOT] TEAMS_BOT_API_KEY nao configurada")
            return jsonify({"error": "API key nao configurada no servidor"}), 500

        api_key = request.headers.get("X-API-Key", "")
        if not api_key or api_key != TEAMS_BOT_API_KEY:
            logger.warning("[TEAMS-BOT] Tentativa com API key invalida")
            return jsonify({"error": "API key invalida"}), 401

        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@teams_bp.route('/bot/message', methods=['POST'])
@csrf.exempt
@require_bot_api_key
def bot_message():
    """
    Recebe mensagem do bot Azure Function.

    Em modo async (TEAMS_ASYNC_MODE=true):
    - Cria TeamsTask no banco
    - Inicia daemon thread para processamento
    - Retorna imediatamente: {"task_id": "uuid", "status": "processing"}
    - Azure Function faz polling em /bot/status/{task_id}

    Em modo sincrono (TEAMS_ASYNC_MODE=false):
    - Processa e retorna resposta na mesma request (legado)

    Input JSON:
    {
        "mensagem": "texto da mensagem do usuario",
        "usuario": "nome do usuario",
        "usuario_id": "id do usuario no Teams",
        "conversation_id": "id da conversa no Teams"
    }
    """
    logger.info("[TEAMS-BOT] POST /bot/message recebido")

    try:
        dados = request.get_json(silent=True) or {}

        mensagem = str(dados.get("mensagem", "")).strip()
        usuario = str(dados.get("usuario", "Usuario")).strip()
        usuario_id = str(dados.get("usuario_id", "")).strip()
        conversation_id = str(dados.get("conversation_id", "")).strip()

        if not mensagem:
            return jsonify({"error": "Campo 'mensagem' e obrigatorio"}), 400

        logger.info(
            f"[TEAMS-BOT] Mensagem de {usuario} ({usuario_id}) "
            f"conv={conversation_id[:30] if conversation_id else 'N/A'}...: "
            f"{mensagem[:100]}"
        )

        from app.agente.config.feature_flags import TEAMS_ASYNC_MODE

        if TEAMS_ASYNC_MODE:
            return _handle_async_message(mensagem, usuario, conversation_id)
        else:
            return _handle_sync_message(mensagem, usuario, conversation_id)

    except ValueError as e:
        logger.warning(f"[TEAMS-BOT] Validacao: {e}")
        return jsonify({"error": str(e)}), 400

    except RuntimeError as e:
        logger.error(f"[TEAMS-BOT] Erro de runtime: {e}")
        return jsonify({"error": str(e)}), 502

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro inesperado: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao processar mensagem"}), 500


def _handle_async_message(mensagem: str, usuario: str, conversation_id: str):
    """
    Cria TeamsTask e inicia daemon thread para processamento.

    Retorna imediatamente com task_id para polling.
    """
    from app.teams.models import TeamsTask
    from app.teams.services import (
        _get_or_create_teams_user, process_teams_task_async,
        cleanup_stale_teams_tasks,
    )
    from app import db

    # Cleanup lazy de tasks stale (> 5 min em pending/processing)
    cleanup_stale_teams_tasks()

    # Controle de concorrência: apenas 1 task ativa por conversa
    if conversation_id:
        active = TeamsTask.query.filter(
            TeamsTask.conversation_id == conversation_id,
            TeamsTask.status.in_(['pending', 'processing', 'awaiting_user_input']),
        ).first()
        if active:
            logger.warning(
                f"[TEAMS-BOT] Task ativa existente para conv={conversation_id[:30]}...: "
                f"task={active.id[:8]}... status={active.status}"
            )
            return jsonify({
                "status": "busy",
                "resposta": "Ainda estou processando a pergunta anterior. Aguarde a resposta.",
                "task_id": active.id,
            })

    # Obter user_id real
    teams_user_id = _get_or_create_teams_user(usuario)

    # Criar task
    task = TeamsTask(
        conversation_id=conversation_id,
        user_name=usuario,
        user_id=teams_user_id,
        status='pending',
        mensagem=mensagem,
    )
    db.session.add(task)
    db.session.commit()

    task_id = task.id
    logger.info(f"[TEAMS-BOT] Task criada: {task_id[:8]}... — iniciando daemon thread")

    # Iniciar daemon thread para processamento
    t = threading.Thread(
        target=process_teams_task_async,
        args=(task_id, mensagem, usuario, conversation_id, teams_user_id),
        daemon=True,
        name=f"teams-task-{task_id[:8]}",
    )
    t.start()

    return jsonify({
        "task_id": task_id,
        "status": "processing",
    })


def _handle_sync_message(mensagem: str, usuario: str, conversation_id: str):
    """
    Fluxo sincrono legado: processa e retorna na mesma request.
    """
    from app.teams.services import processar_mensagem_bot

    resposta = processar_mensagem_bot(
        mensagem=mensagem,
        usuario=usuario,
        conversation_id=conversation_id,
    )
    return jsonify({"resposta": resposta})


@teams_bp.route('/bot/status/<task_id>', methods=['GET'])
@csrf.exempt
@require_bot_api_key
def bot_task_status(task_id: str):
    """
    Polling de status de uma TeamsTask.

    Retorna:
    - processing: {"status": "processing"}
    - completed: {"status": "completed", "resposta": "..."}
    - error: {"status": "error", "resposta": "..."}
    - awaiting_user_input: {"status": "awaiting_user_input", "questions": [...]}
    - timeout: {"status": "timeout"}
    """
    from app.teams.models import TeamsTask

    task = TeamsTask.query.get(task_id)
    if not task:
        return jsonify({"error": "Task nao encontrada"}), 404

    result = {"status": task.status}

    if task.status == 'completed':
        result["resposta"] = task.resposta or "Sem resposta do sistema."

    elif task.status == 'error':
        result["resposta"] = task.resposta or "Erro ao processar mensagem."

    elif task.status == 'awaiting_user_input':
        result["questions"] = task.pending_questions or []
        result["task_id"] = task.id

    elif task.status == 'timeout':
        result["resposta"] = "Tempo limite excedido. Tente novamente."

    return jsonify(result)


@teams_bp.route('/bot/answer', methods=['POST'])
@csrf.exempt
@require_bot_api_key
def bot_answer():
    """
    Recebe resposta de Adaptive Card (AskUserQuestion) do Teams.

    Input JSON:
    {
        "task_id": "uuid-da-task",
        "answers": {"question_text": "selected_label", ...}
    }

    Output JSON:
    {"status": "ok"} ou {"error": "..."}
    """
    logger.info("[TEAMS-BOT] POST /bot/answer recebido")

    try:
        dados = request.get_json(silent=True) or {}
        task_id = str(dados.get("task_id", "")).strip()
        answers = dados.get("answers", {})

        if not task_id:
            return jsonify({"error": "Campo 'task_id' e obrigatorio"}), 400

        if not answers:
            return jsonify({"error": "Campo 'answers' e obrigatorio"}), 400

        from app.teams.models import TeamsTask
        from app.agente.sdk.pending_questions import submit_answer
        from app import db

        task = TeamsTask.query.get(task_id)
        if not task:
            return jsonify({"error": "Task nao encontrada"}), 404

        if task.status != 'awaiting_user_input':
            return jsonify({
                "error": f"Task nao esta aguardando resposta (status={task.status})"
            }), 400

        session_id = task.pending_question_session_id
        if not session_id:
            return jsonify({"error": "session_id nao encontrado na task"}), 500

        # submit_answer() desbloqueia o threading.Event na daemon thread (MESMO processo)
        success = submit_answer(session_id, answers)

        if success:
            # Atualiza status de volta para processing
            task.status = 'processing'
            task.pending_questions = None
            task.pending_question_session_id = None
            db.session.commit()

            logger.info(
                f"[TEAMS-BOT] Resposta submetida para task={task_id[:8]}... "
                f"answers={list(answers.keys())}"
            )
            return jsonify({"status": "ok"})
        else:
            logger.warning(
                f"[TEAMS-BOT] submit_answer falhou: nenhuma pergunta pendente "
                f"para session={session_id[:8]}..."
            )
            return jsonify({
                "error": "Pergunta ja expirou ou foi respondida anteriormente"
            }), 410

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao processar resposta: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao processar resposta"}), 500


@teams_bp.route('/bot/execute', methods=['POST'])
@csrf.exempt
@require_bot_api_key
def bot_execute():
    """
    Executa uma tarefa confirmada pelo usuario.

    Input JSON:
    {
        "task_id": "uuid-da-tarefa"
    }

    Output JSON:
    {
        "resposta": "resultado da execucao"
    }
    """
    logger.info("[TEAMS-BOT] POST /bot/execute recebido")

    try:
        dados = request.get_json(silent=True) or {}
        task_id = str(dados.get("task_id", "")).strip()

        if not task_id:
            return jsonify({"error": "Campo 'task_id' e obrigatorio"}), 400

        logger.info(f"[TEAMS-BOT] Executando tarefa: {task_id}")

        # TODO: Implementar busca e execucao de tarefas pendentes.
        return jsonify({
            "resposta": (
                f"Tarefa {task_id} recebida para execucao. "
                "Esta funcionalidade sera implementada em breve."
            )
        })

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro ao executar: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao executar tarefa"}), 500


@teams_bp.route('/bot/health', methods=['GET'])
def bot_health():
    """Health check para o bot Azure Function."""
    from app.agente.config.feature_flags import TEAMS_ASYNC_MODE
    return jsonify({
        "status": "ok",
        "service": "teams-bot",
        "async_mode": TEAMS_ASYNC_MODE,
    })
