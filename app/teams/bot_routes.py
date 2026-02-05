"""
Rotas da API para o Bot do Microsoft Teams (Azure Function).

Endpoints:
- POST /api/teams/bot/message  - Recebe mensagem do bot e envia ao Agent SDK
- POST /api/teams/bot/execute  - Executa tarefa confirmada pelo usuario
- GET  /api/teams/bot/health   - Health check
"""

import os
import logging
import functools
from flask import request, jsonify
from app.teams import teams_bp
from app.teams.services import processar_mensagem_bot
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
    Recebe mensagem do bot Azure Function e envia ao Agent SDK.

    Input JSON:
    {
        "mensagem": "texto da mensagem do usuario",
        "usuario": "nome do usuario",
        "usuario_id": "id do usuario no Teams",
        "conversation_id": "id da conversa no Teams (para sessao persistente)"
    }

    Output JSON (resposta direta):
    {
        "resposta": "texto da resposta do agente"
    }

    Output JSON (confirmacao necessaria):
    {
        "requer_confirmacao": true,
        "task_id": "uuid-da-tarefa",
        "descricao": "descricao do que sera executado"
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

        # Processa mensagem via Agent SDK COM sessao persistente
        resposta = processar_mensagem_bot(
            mensagem=mensagem,
            usuario=usuario,
            conversation_id=conversation_id,
        )

        return jsonify({"resposta": resposta})

    except ValueError as e:
        logger.warning(f"[TEAMS-BOT] Validacao: {e}")
        return jsonify({"error": str(e)}), 400

    except RuntimeError as e:
        logger.error(f"[TEAMS-BOT] Erro de runtime: {e}")
        return jsonify({"error": str(e)}), 502

    except Exception as e:
        logger.error(f"[TEAMS-BOT] Erro inesperado: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao processar mensagem"}), 500


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
        # Por enquanto, retorna mensagem de que a feature sera implementada.
        # O fluxo completo seria:
        # 1. Buscar tarefa pendente por task_id (Redis ou dict em memoria)
        # 2. Executar a acao confirmada
        # 3. Retornar resultado

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
    return jsonify({
        "status": "ok",
        "service": "teams-bot",
    })
