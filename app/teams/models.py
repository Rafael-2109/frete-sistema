"""
Modelos de dados para o bot do Microsoft Teams.

TeamsTask: Representa uma tarefa assíncrona de processamento de mensagem.
Permite polling de status e suporte a AskUserQuestion via Adaptive Cards.
"""

import uuid

from app import db
from app.utils.timezone import agora_utc_naive


class TeamsTask(db.Model):
    """
    Tarefa assíncrona para processamento de mensagem do Teams.

    Ciclo de vida:
    pending → processing → completed | error | awaiting_user_input | timeout

    Quando o agente chama AskUserQuestion:
    processing → awaiting_user_input → (resposta) → processing → completed

    Campos:
        id: UUID gerado automaticamente
        conversation_id: ID da conversa do Teams (para filtrar por conversa)
        user_name: Nome do usuário do Teams
        user_id: FK para usuarios (auto-cadastrado via _get_or_create_teams_user)
        status: Estado atual da tarefa
        mensagem: Texto da mensagem do usuário
        resposta: Texto da resposta do agente (preenchido ao completar)
        pending_questions: JSON com perguntas do AskUserQuestion
        pending_question_session_id: session_id para submit_answer()
        created_at: Timestamp de criação
        updated_at: Timestamp de última atualização
        completed_at: Timestamp de conclusão
    """

    __tablename__ = 'teams_tasks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(255), nullable=False, index=True)
    user_name = db.Column(db.String(200), nullable=False)
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
        return (
            f"<TeamsTask id={self.id[:8]}... status={self.status} "
            f"user={self.user_name}>"
        )
