"""
Modelos SQLAlchemy do Agente.

FEAT-011: Lista de Sessões
FEAT-030: Histórico de Mensagens Persistente

Arquitetura:
- Histórico COMPLETO armazenado no campo `data` (JSONB)
- SDK usado apenas como canal de comunicação (pode expirar)
- Quando SDK expira, injeta histórico de mensagens como contexto
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import uuid

from app import db


# Constante para limite de mensagens no contexto
MAX_MESSAGES_IN_CONTEXT = 50  # Últimas N mensagens enviadas ao SDK


class AgentSession(db.Model):
    """
    Sessão do Agente Claude.

    Armazena sessões para persistência e listagem (FEAT-011).
    Armazena histórico completo de mensagens no campo `data` (FEAT-030).

    Estrutura do campo `data`:
    {
        "messages": [
            {
                "id": "msg_uuid",
                "role": "user" | "assistant",
                "content": "texto da mensagem",
                "timestamp": "ISO 8601",
                "tokens": {"input": N, "output": N},  # apenas assistant
                "tools_used": ["tool1", "tool2"]       # apenas assistant
            }
        ],
        "sdk_session_id": "session_id_atual_no_sdk",
        "total_tokens": 15000
    }
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

    # Dados extras em JSONB - HISTÓRICO COMPLETO (FEAT-030)
    data = db.Column(db.JSON, default=dict)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento
    user = db.relationship('Usuario', backref=db.backref('agent_sessions', lazy='dynamic'))

    def __repr__(self):
        return f'<AgentSession {self.session_id[:8]}... user={self.user_id}>'

    # =========================================================================
    # MÉTODOS DE SERIALIZAÇÃO
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
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

    def _generate_title(self) -> str:
        """Gera título a partir da primeira mensagem do usuário."""
        messages = self.get_messages()
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                title = content[:50]
                if len(content) > 50:
                    title += '...'
                return title

        if self.last_message:
            title = self.last_message[:50]
            if len(self.last_message) > 50:
                title += '...'
            return title

        return f'Sessão {self.created_at.strftime("%d/%m %H:%M") if self.created_at else "Nova"}'

    def _truncate_message(self, msg: str, max_len: int = 100) -> Optional[str]:
        """Trunca mensagem para preview."""
        if not msg:
            return None
        if len(msg) <= max_len:
            return msg
        return msg[:max_len] + '...'

    # =========================================================================
    # MÉTODOS DE GERENCIAMENTO DE MENSAGENS (FEAT-030)
    # =========================================================================

    def _ensure_data_structure(self) -> None:
        """Garante que o campo data tem a estrutura correta."""
        if not self.data:
            self.data = {}

        if 'messages' not in self.data:
            self.data['messages'] = []

        if 'total_tokens' not in self.data:
            self.data['total_tokens'] = 0

    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as mensagens da sessão.

        Returns:
            Lista de mensagens ordenadas por timestamp
        """
        self._ensure_data_structure()
        return self.data.get('messages', [])

    def add_user_message(self, content: str) -> Dict[str, Any]:
        """
        Adiciona mensagem do usuário.

        Args:
            content: Conteúdo da mensagem

        Returns:
            Mensagem criada
        """
        self._ensure_data_structure()

        message = {
            'id': f'msg_{uuid.uuid4().hex[:12]}',
            'role': 'user',
            'content': content,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }

        self.data['messages'].append(message)
        self.last_message = content
        self.message_count = (self.message_count or 0) + 1

        # Gera título na primeira mensagem
        if not self.title:
            self.title = self._generate_title()

        self.updated_at = datetime.utcnow()

        # Marca data como modificado para SQLAlchemy detectar
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'data')

        return message

    def add_assistant_message(
        self,
        content: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tools_used: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Adiciona mensagem do assistente.

        Args:
            content: Conteúdo da mensagem
            input_tokens: Tokens de entrada usados
            output_tokens: Tokens de saída usados
            tools_used: Lista de ferramentas usadas

        Returns:
            Mensagem criada
        """
        self._ensure_data_structure()

        message = {
            'id': f'msg_{uuid.uuid4().hex[:12]}',
            'role': 'assistant',
            'content': content,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tokens': {
                'input': input_tokens,
                'output': output_tokens,
            },
        }

        if tools_used:
            message['tools_used'] = tools_used

        self.data['messages'].append(message)

        # Atualiza contadores
        total_new_tokens = input_tokens + output_tokens
        self.data['total_tokens'] = self.data.get('total_tokens', 0) + total_new_tokens
        self.message_count = (self.message_count or 0) + 1
        self.updated_at = datetime.utcnow()

        # Marca data como modificado
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'data')

        return message

    def get_total_tokens(self) -> int:
        """Retorna total de tokens usados na sessão."""
        self._ensure_data_structure()
        return self.data.get('total_tokens', 0)

    def get_sdk_session_id(self) -> Optional[str]:
        """Retorna o session_id atual do SDK."""
        self._ensure_data_structure()
        return self.data.get('sdk_session_id')

    def set_sdk_session_id(self, sdk_session_id: Optional[str]) -> None:
        """
        Define o session_id do SDK.

        Args:
            sdk_session_id: ID da sessão no SDK (ou None para limpar)
        """
        self._ensure_data_structure()
        self.data['sdk_session_id'] = sdk_session_id

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'data')

    def get_messages_for_context(self) -> List[Dict[str, Any]]:
        """
        Retorna últimas N mensagens para injetar como contexto.

        Usado quando a sessão SDK expira e precisamos reconstruir o contexto.

        Returns:
            Lista de mensagens para contexto (máximo MAX_MESSAGES_IN_CONTEXT)
        """
        messages = self.get_messages()
        if len(messages) > MAX_MESSAGES_IN_CONTEXT:
            return messages[-MAX_MESSAGES_IN_CONTEXT:]
        return messages

    # =========================================================================
    # MÉTODOS DE CLASSE
    # =========================================================================

    @classmethod
    def get_or_create(cls, session_id: str, user_id: int = None) -> Tuple['AgentSession', bool]:
        """
        Busca sessão existente ou cria nova.

        Args:
            session_id: ID da sessão (nosso ID, não do SDK)
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
            data={
                'messages': [],
                'total_tokens': 0,
            },
        )
        db.session.add(session)
        return session, True

    @classmethod
    def get_by_session_id(cls, session_id: str) -> Optional['AgentSession']:
        """
        Busca sessão por session_id.

        Args:
            session_id: ID da sessão

        Returns:
            Sessão ou None
        """
        return cls.query.filter_by(session_id=session_id).first()

    @classmethod
    def list_for_user(cls, user_id: int, limit: int = 20) -> List['AgentSession']:
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
