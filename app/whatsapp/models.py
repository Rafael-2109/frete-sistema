"""Modelos do canal WhatsApp.

WhatsAppTask: tarefa async de processamento de mensagem inbound, espelhando
TeamsTask. Lifecycle: pending -> processing -> completed | error | timeout |
awaiting_user_input.

Migration: scripts/migrations/2026_05_09_whatsapp_module.{py,sql}
"""

import uuid

from app import db
from app.utils.timezone import agora_utc_naive


class WhatsAppTask(db.Model):
    """Tarefa async para mensagem WhatsApp recebida via plugin OpenClaw.

    Identidade da conversa:
        peer_jid: numero E.164 (DM) ou JID Baileys do remetente em grupo
        conversation_jid: peer_jid em DM, JID grupo (@g.us) em grupo
        is_group: True se conversa de grupo

    Vinculo Nacom:
        user_id: FK usuarios resolvido via Usuario.find_by_whatsapp_jid

    Correlacao OpenClaw:
        openclaw_message_id: messageId do plugin (deduplicacao)
        openclaw_session_key: sessionKey do plugin (debugging)
    """

    __tablename__ = 'whatsapp_tasks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    peer_jid = db.Column(db.String(120), nullable=False, index=True)
    conversation_jid = db.Column(db.String(120), nullable=False, index=True)
    is_group = db.Column(db.Boolean, nullable=False, default=False)
    sender_name = db.Column(db.String(200), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    status = db.Column(
        db.String(30),
        nullable=False,
        default='pending',
        index=True,
    )
    mensagem = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.Text, nullable=True)

    pending_questions = db.Column(db.JSON, nullable=True)
    pending_question_session_id = db.Column(db.String(255), nullable=True)

    openclaw_message_id = db.Column(db.String(120), nullable=True)
    openclaw_session_key = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=agora_utc_naive,
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=agora_utc_naive,
        onupdate=agora_utc_naive,
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        peer_safe = (self.peer_jid or '')[:8]
        return (
            f"<WhatsAppTask id={self.id[:8]}... status={self.status} "
            f"peer=***{peer_safe}...>"
        )
