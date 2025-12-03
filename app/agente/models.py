"""
Modelos SQLAlchemy do Agente.

FEAT-011: Lista de Sessões
"""

from datetime import datetime
from app import db


class AgentSession(db.Model):
    """
    Sessão do Agente Claude.

    Armazena sessões para persistência e listagem (FEAT-011).
    O SDK usa session_id para retomar conversas (resume).

    Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/sessions
    """
    __tablename__ = 'agent_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)

    # Campos para UI (FEAT-011)
    title = db.Column(db.String(200), nullable=True)
    message_count = db.Column(db.Integer, default=0)
    total_cost_usd = db.Column(db.Numeric(10, 6), default=0)
    last_message = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)

    # Dados extras em JSONB
    data = db.Column(db.JSON, default=dict)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento
    user = db.relationship('Usuario', backref=db.backref('agent_sessions', lazy='dynamic'))

    def __repr__(self):
        return f'<AgentSession {self.session_id[:8]}... user={self.user_id}>'

    def to_dict(self):
        """Converte para dicionário (API response)."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'title': self.title or self._generate_title(),
            'message_count': self.message_count or 0,
            'total_cost_usd': float(self.total_cost_usd or 0),
            'last_message': self._truncate_message(self.last_message),
            'model': self.model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def _generate_title(self):
        """Gera título a partir da última mensagem."""
        if self.last_message:
            # Primeiras 50 chars da última mensagem
            title = self.last_message[:50]
            if len(self.last_message) > 50:
                title += '...'
            return title
        return f'Sessão {self.created_at.strftime("%d/%m %H:%M") if self.created_at else "Nova"}'

    def _truncate_message(self, msg, max_len=100):
        """Trunca mensagem para preview."""
        if not msg:
            return None
        if len(msg) <= max_len:
            return msg
        return msg[:max_len] + '...'

    @classmethod
    def get_or_create(cls, session_id: str, user_id: int = None):
        """
        Busca sessão existente ou cria nova.

        Args:
            session_id: ID da sessão do SDK
            user_id: ID do usuário

        Returns:
            Tupla (session, created)
        """
        session = cls.query.filter_by(session_id=session_id).first()
        if session:
            return session, False

        session = cls(
            session_id=session_id,
            user_id=user_id,
            message_count=0,
            total_cost_usd=0,
        )
        db.session.add(session)
        return session, True

    def update_from_response(
        self,
        message: str = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0,
        model: str = None,
    ):
        """
        Atualiza sessão com dados da resposta.

        Args:
            message: Última mensagem do usuário
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída
            cost_usd: Custo em USD
            model: Modelo usado
        """
        if message:
            self.last_message = message
            # Gera título na primeira mensagem
            if not self.title and self.message_count == 0:
                self.title = self._generate_title()

        self.message_count = (self.message_count or 0) + 1
        self.total_cost_usd = float(self.total_cost_usd or 0) + cost_usd

        if model:
            self.model = model

        self.updated_at = datetime.utcnow()

    @classmethod
    def list_for_user(cls, user_id: int, limit: int = 20):
        """
        Lista sessões de um usuário.

        Args:
            user_id: ID do usuário
            limit: Máximo de sessões

        Returns:
            Lista de sessões ordenadas por updated_at DESC
        """
        return cls.query.filter_by(user_id=user_id)\
            .order_by(cls.updated_at.desc())\
            .limit(limit)\
            .all()
