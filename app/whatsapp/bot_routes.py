"""Endpoints HTTP recebidos do plugin OpenClaw `nacom-bridge`.

Endpoints:
- POST /api/whatsapp/inbound  — recebe mensagem do plugin, cria task async
- GET  /api/whatsapp/health   — health check (status async + threads vivas)

Auth: todos os endpoints (exceto /health) exigem Authorization: Bearer
<OPENCLAW_PLUGIN_TOKEN> via decorator `require_plugin_token`.

Fluxo:
1. Plugin OpenClaw faz POST /inbound com headers de identidade + body com texto
2. require_plugin_token valida shared secret
3. Resolve peer -> Usuario via Usuario.find_by_whatsapp_jid (banco)
4. Cria WhatsAppTask, dispara thread daemon=False (R1 do Teams)
5. Retorna 202 imediatamente — plugin ja respondeu synthetic reply ao usuario
6. Thread processa via Agent SDK e envia resposta via gateway OpenClaw

Veja `app/whatsapp/CLAUDE.md` para regras criticas (R1-R8 espelhadas do Teams).
"""

import logging
import threading

from flask import current_app, jsonify, request

from app import csrf
from app.whatsapp import whatsapp_bp
from app.whatsapp.decorators import require_plugin_token

logger = logging.getLogger(__name__)


# ─── /inbound ────────────────────────────────────────────────────────────

@whatsapp_bp.route('/inbound', methods=['POST'])
@csrf.exempt
@require_plugin_token
def inbound():
    """Recebe mensagem WhatsApp do plugin OpenClaw.

    Headers obrigatorios (injetados pelo plugin nacom-bridge):
        Authorization: Bearer <OPENCLAW_PLUGIN_TOKEN>
        X-OpenClaw-Sender: senderId do evento (E.164 sem '+' em DM, JID em grupo)
        X-OpenClaw-Conversation: conversationId (peer em DM, JID grupo @g.us)
        X-OpenClaw-IsGroup: "True" ou "False"

    Headers opcionais:
        X-OpenClaw-MessageId: messageId do evento (deduplicacao)
        X-OpenClaw-SenderName: nome de exibicao
        X-OpenClaw-SessionKey: sessionKey do plugin

    Body JSON:
        {"text": "mensagem do usuario"}

    Retorna:
        202 + {"task_id": "uuid", "status": "processing"}  — task async criada
        403 + {"error": "sender_not_authorized"}            — peer nao tem opt-in
        400 + {"error": "..."}                              — payload invalido
    """
    sender = request.headers.get("X-OpenClaw-Sender", "").strip()
    conversation = request.headers.get("X-OpenClaw-Conversation", "").strip()
    is_group = request.headers.get("X-OpenClaw-IsGroup", "False").lower() == "true"
    message_id = request.headers.get("X-OpenClaw-MessageId", "").strip() or None
    sender_name = request.headers.get("X-OpenClaw-SenderName", "").strip() or None
    session_key = request.headers.get("X-OpenClaw-SessionKey", "").strip() or None

    if not sender:
        return jsonify({"error": "X-OpenClaw-Sender header obrigatorio"}), 400
    if not conversation:
        return jsonify({"error": "X-OpenClaw-Conversation header obrigatorio"}), 400

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    if not text:
        return jsonify({"error": "campo 'text' obrigatorio"}), 400
    if len(text) > 10000:
        return jsonify({"error": "text excede 10000 caracteres"}), 400

    # ─── Resolve peer -> Usuario (autorizacao de dominio) ────────────────
    from app.auth.models import Usuario
    user = Usuario.find_by_whatsapp_jid(sender)
    if not user:
        logger.warning(
            f"[WHATSAPP] Sender nao autorizado ou nao mapeado: "
            f"sender={_redact_phone(sender)} group={is_group}"
        )
        return jsonify({
            "error": "sender_not_authorized",
            "message": (
                "Telefone nao mapeado ou whatsapp_autorizado=False. "
                "Cadastre o telefone do usuario e marque opt-in."
            ),
        }), 403

    # ─── Cria task async ─────────────────────────────────────────────────
    from app import db
    from app.whatsapp.models import WhatsAppTask
    from app.whatsapp.services import (
        cleanup_stale_whatsapp_tasks,
        process_whatsapp_task_async,
    )

    cleanup_stale_whatsapp_tasks()

    task = WhatsAppTask(
        peer_jid=sender,
        conversation_jid=conversation,
        is_group=is_group,
        sender_name=sender_name,
        user_id=user.id,
        status='pending',
        mensagem=text,
        openclaw_message_id=message_id,
        openclaw_session_key=session_key,
    )
    db.session.add(task)
    db.session.commit()

    logger.info(
        f"[WHATSAPP] Task criada: id={task.id[:8]}... "
        f"sender={_redact_phone(sender)} group={is_group} "
        f"user_id={user.id} text_len={len(text)}"
    )

    # Reutiliza app context do gunicorn worker (Fix 3 do Teams)
    app = current_app._get_current_object()

    # daemon=False: sobrevive a reciclagem do worker (R1 do Teams)
    t = threading.Thread(
        target=process_whatsapp_task_async,
        args=(app, task.id),
        daemon=False,
        name=f"whatsapp-task-{task.id[:8]}",
    )
    t.start()

    return jsonify({"task_id": task.id, "status": "processing"}), 202


# ─── /health ─────────────────────────────────────────────────────────────

@whatsapp_bp.route('/health', methods=['GET'])
def health():
    """Health check do canal WhatsApp.

    NAO requer auth (semelhante a /api/teams/bot/health).
    """
    import os

    from app.utils.whatsapp_notify import is_configured as gateway_configured
    from app.whatsapp.decorators import OPENCLAW_PLUGIN_TOKEN

    threads_ativas = [
        t for t in threading.enumerate()
        if t.name.startswith('whatsapp-task-') and t.is_alive()
    ]

    return jsonify({
        "status": "ok",
        "service": "whatsapp-bot",
        "plugin_token_configured": bool(OPENCLAW_PLUGIN_TOKEN),
        "gateway_configured": gateway_configured(),
        "active_threads": len(threads_ativas),
        "thread_names": [t.name for t in threads_ativas[:10]],
        "pid": os.getpid(),
    })


# ─── Helpers ─────────────────────────────────────────────────────────────

def _redact_phone(s: str) -> str:
    """Mascara telefone preservando 4 ultimos digitos para log."""
    if not s:
        return ""
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) <= 4:
        return s[:8]
    return f"***{digits[-4:]}"
