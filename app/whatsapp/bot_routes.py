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
from app.whatsapp.decorators import require_n8n_token, require_plugin_token

logger = logging.getLogger(__name__)


# ─── Core compartilhado (OpenClaw + N8N) ───────────────────────────────────

def _create_inbound_task(
    *,
    sender: str,
    conversation: str,
    is_group: bool,
    text: str,
    message_id=None,
    sender_name=None,
    session_key=None,
    source: str = "openclaw",
):
    """Resolve peer -> Usuario, cria WhatsAppTask e dispara thread async.

    Logica compartilhada entre os dois transportes inbound:
    - /inbound (plugin OpenClaw, identidade via headers X-OpenClaw-*)
    - /n8n/inbound (workflow N8N, identidade via body JSON)

    Retorna uma tupla (response_json, http_status) pronta para o caller
    devolver. NAO depende de como a identidade chegou — so dos valores ja
    extraidos. `source` entra apenas no log (debug de qual transporte gerou).
    """
    # ─── Resolve peer -> Usuario (autorizacao de dominio, R6) ────────────
    from app.auth.models import Usuario
    user = Usuario.find_by_whatsapp_jid(sender)
    if not user:
        logger.warning(
            f"[WHATSAPP] Sender nao autorizado ou nao mapeado (src={source}): "
            f"sender={_redact_phone(sender)} group={is_group}"
        )
        return {
            "error": "sender_not_authorized",
            "message": (
                "Telefone nao mapeado ou whatsapp_autorizado=False. "
                "Cadastre o telefone do usuario e marque opt-in."
            ),
        }, 403

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
        f"[WHATSAPP] Task criada (src={source}): id={task.id[:8]}... "
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

    return {"task_id": task.id, "status": "processing"}, 202


# ─── /inbound (OpenClaw) ───────────────────────────────────────────────────

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

    body, status = _create_inbound_task(
        sender=sender,
        conversation=conversation,
        is_group=is_group,
        text=text,
        message_id=message_id,
        sender_name=sender_name,
        session_key=session_key,
        source="openclaw",
    )
    return jsonify(body), status


# ─── /n8n/inbound (N8N + Evolution API) ────────────────────────────────────

@whatsapp_bp.route('/n8n/inbound', methods=['POST'])
@csrf.exempt
@require_n8n_token
def n8n_inbound():
    """Recebe mensagem WhatsApp do workflow N8N (transporte Evolution API).

    Diferente do /inbound (OpenClaw), a identidade vem no BODY JSON — o N8N
    monta esse payload normalizando o evento bruto da Evolution. Auth via
    Authorization: Bearer <N8N_INBOUND_TOKEN>.

    Body JSON:
        {
            "sender": "5511991642998",            # obrigatorio — E.164 sem '+'
            "conversation": "5511991642998",       # opcional (default=sender)
                                                   # em grupo: JID "...@g.us"
            "is_group": false,                     # opcional (default false)
            "text": "mensagem do usuario",         # obrigatorio
            "message_id": "ABC123",                # opcional (dedup)
            "sender_name": "Rafael",               # opcional
            "session_key": "..."                   # opcional (debug)
        }

    Retorna:
        202 + {"task_id": "uuid", "status": "processing"}
        403 + {"error": "sender_not_authorized"}
        400 + {"error": "..."}                     payload invalido
    """
    payload = request.get_json(silent=True) or {}

    sender = str(payload.get("sender", "")).strip()
    if not sender:
        return jsonify({"error": "campo 'sender' obrigatorio"}), 400

    text = str(payload.get("text", "")).strip()
    if not text:
        return jsonify({"error": "campo 'text' obrigatorio"}), 400
    if len(text) > 10000:
        return jsonify({"error": "text excede 10000 caracteres"}), 400

    is_group = bool(payload.get("is_group", False))
    # Em DM, conversation == sender; o N8N pode omitir.
    conversation = str(payload.get("conversation", "")).strip() or sender
    message_id = str(payload.get("message_id", "")).strip() or None
    sender_name = str(payload.get("sender_name", "")).strip() or None
    session_key = str(payload.get("session_key", "")).strip() or None

    body, status = _create_inbound_task(
        sender=sender,
        conversation=conversation,
        is_group=is_group,
        text=text,
        message_id=message_id,
        sender_name=sender_name,
        session_key=session_key,
        source="n8n",
    )
    return jsonify(body), status


# ─── /health ─────────────────────────────────────────────────────────────

@whatsapp_bp.route('/health', methods=['GET'])
def health():
    """Health check do canal WhatsApp.

    NAO requer auth (semelhante a /api/teams/bot/health).
    """
    import os

    from app.utils.whatsapp_evolution import is_configured as evolution_configured
    from app.utils.whatsapp_notify import is_configured as gateway_configured
    from app.whatsapp.decorators import (
        N8N_INBOUND_TOKEN,
        OPENCLAW_PLUGIN_TOKEN,
    )

    threads_ativas = [
        t for t in threading.enumerate()
        if t.name.startswith('whatsapp-task-') and t.is_alive()
    ]

    transport = os.environ.get("WHATSAPP_TRANSPORT", "openclaw").lower()

    return jsonify({
        "status": "ok",
        "service": "whatsapp-bot",
        "transport": transport,
        # OpenClaw (transporte legado)
        "plugin_token_configured": bool(OPENCLAW_PLUGIN_TOKEN),
        "gateway_configured": gateway_configured(),
        # N8N + Evolution API
        "n8n_token_configured": bool(N8N_INBOUND_TOKEN),
        "evolution_configured": evolution_configured(),
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
