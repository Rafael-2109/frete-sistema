"""
Modelos SQLAlchemy do Agente.

FEAT-011: Lista de Sessões
FEAT-030: Histórico de Mensagens Persistente

Arquitetura:
- Histórico COMPLETO armazenado no campo `data` (JSONB)
- SDK usado apenas como canal de comunicação (pode expirar)
- Quando SDK expira, injeta histórico de mensagens como contexto
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import uuid

from app import db
from app.utils.timezone import agora_utc_naive
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
    session_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)

    # Campos para UI (FEAT-011)
    title = db.Column(db.String(200), nullable=True)
    message_count = db.Column(db.Integer, default=0)
    total_cost_usd = db.Column(db.Numeric(10, 6), default=0)
    last_message = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)

    # Dados extras em JSONB - HISTÓRICO COMPLETO (FEAT-030)
    data = db.Column(db.JSON, default=dict)

    # P0-2: Sumarização Estruturada de Sessões
    summary = db.Column(db.JSON, nullable=True)  # Resumo estruturado (JSONB)
    summary_updated_at = db.Column(db.DateTime, nullable=True)  # Quando foi gerado
    summary_message_count = db.Column(db.Integer, default=0)  # message_count quando gerado

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    # Relacionamento - cascade delete quando usuário é deletado
    user = db.relationship(
        'Usuario',
        backref=db.backref('agent_sessions', lazy='dynamic', cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f'<AgentSession {self.session_id[:8]}... user={self.user_id}>'

    # =========================================================================
    # MÉTODOS DE SERIALIZAÇÃO
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (API response)."""
        result = {
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

        # P0-2: Inclui summary se disponível
        if self.summary:
            result['summary'] = self.summary
            result['summary_updated_at'] = (
                self.summary_updated_at.isoformat()
                if self.summary_updated_at else None
            )

        return result

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
            'timestamp': agora_utc_naive().isoformat() + 'Z',
        }

        self.data['messages'].append(message)
        self.last_message = content
        self.message_count = (self.message_count or 0) + 1

        # Gera título na primeira mensagem
        if not self.title:
            self.title = self._generate_title()

        self.updated_at = agora_utc_naive()

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
            'timestamp': agora_utc_naive().isoformat() + 'Z',
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
        self.updated_at = agora_utc_naive()

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
    # MÉTODOS DE SUMARIZAÇÃO (P0-2)
    # =========================================================================

    def get_summary(self) -> Optional[Dict[str, Any]]:
        """Retorna summary estruturado da sessão."""
        return self.summary

    def set_summary(self, summary_data: Dict[str, Any]) -> None:
        """
        Define summary estruturado.

        Args:
            summary_data: Dicionário com resumo estruturado
        """
        self.summary = summary_data
        self.summary_updated_at = agora_utc_naive()
        self.summary_message_count = self.message_count or 0

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'summary')

    def needs_summarization(self, threshold: int = 5) -> bool:
        """
        Verifica se a sessão precisa de (re)sumarização.

        Critérios:
        1. message_count >= threshold
        2. Não tem summary OU summary está stale
           (stale = message_count cresceu >= threshold desde último summary)

        Args:
            threshold: Número mínimo de mensagens para trigger

        Returns:
            True se precisa sumarizar
        """
        current_count = self.message_count or 0

        # Muito poucas mensagens
        if current_count < threshold:
            return False

        # Nunca foi sumarizada
        if not self.summary:
            return True

        # Summary stale: cresceu N+ mensagens desde última sumarização
        messages_since_summary = current_count - (self.summary_message_count or 0)
        return messages_since_summary >= threshold

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


class AgentMemory(db.Model):
    """
    Memória persistente do agente por usuário.

    Implementa armazenamento para a Memory Tool da Anthropic.
    Simula um filesystem virtual onde cada "arquivo" é um registro no banco.

    Referência: https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool

    Estrutura de paths:
        /memories/                      # Raiz (diretório virtual)
        /memories/preferences.xml       # Preferências do usuário
        /memories/context/company.xml   # Informações da empresa
        /memories/learned/terms.xml     # Termos aprendidos

    Uso:
        - Claude usa a Memory Tool para criar/ler/editar arquivos
        - Cada usuário tem sua própria árvore de memórias
        - Memórias persistem entre sessões (cross-session)
    """
    __tablename__ = 'agent_memories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)

    # Path do arquivo virtual (ex: /memories/preferences.xml)
    path = db.Column(db.String(500), nullable=False)

    # Conteúdo do arquivo (None para diretórios)
    content = db.Column(db.Text, nullable=True)

    # Flag para indicar se é diretório
    is_directory = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    # Relacionamento - cascade delete quando usuário é deletado
    user = db.relationship(
        'Usuario',
        backref=db.backref('agent_memories', lazy='dynamic', cascade='all, delete-orphan')
    )

    # Constraint única: um usuário não pode ter dois arquivos com mesmo path
    __table_args__ = (
        db.UniqueConstraint('user_id', 'path', name='uq_user_memory_path'),
    )

    def __repr__(self):
        tipo = 'DIR' if self.is_directory else 'FILE'
        return f'<AgentMemory {tipo} {self.path} user={self.user_id}>'

    # =========================================================================
    # MÉTODOS DE CLASSE PARA OPERAÇÕES CRUD
    # =========================================================================

    @classmethod
    def get_by_path(cls, user_id: int, path: str) -> Optional['AgentMemory']:
        """Busca memória por path."""
        return cls.query.filter_by(user_id=user_id, path=path).first()

    @classmethod
    def list_directory(cls, user_id: int, dir_path: str) -> List['AgentMemory']:
        """
        Lista conteúdo de um diretório.

        Args:
            user_id: ID do usuário
            dir_path: Path do diretório (ex: /memories/context)

        Returns:
            Lista de arquivos/diretórios filhos diretos
        """
        # Normaliza path
        if not dir_path.endswith('/'):
            dir_path = dir_path + '/'

        # Busca todos que começam com o path do diretório
        all_children = cls.query.filter(
            cls.user_id == user_id,
            cls.path.like(f'{dir_path}%'),
            cls.path != dir_path.rstrip('/')
        ).all()

        # Filtra apenas filhos diretos (sem subdiretórios)
        direct_children = []
        for item in all_children:
            # Remove o prefixo do diretório
            relative = item.path[len(dir_path):]
            # Se não tem '/', é filho direto
            if '/' not in relative:
                direct_children.append(item)

        return direct_children

    @classmethod
    def create_file(cls, user_id: int, path: str, content: str) -> 'AgentMemory':
        """
        Cria arquivo de memória.

        Args:
            user_id: ID do usuário
            path: Path do arquivo
            content: Conteúdo

        Returns:
            AgentMemory criado
        """
        # Cria diretórios pai se necessário
        cls._ensure_parent_dirs(user_id, path)

        memory = cls(
            user_id=user_id,
            path=path,
            content=content,
            is_directory=False
        )
        db.session.add(memory)
        return memory

    @classmethod
    def create_directory(cls, user_id: int, path: str) -> 'AgentMemory':
        """Cria diretório de memória."""
        existing = cls.get_by_path(user_id, path)
        if existing:
            return existing

        # Cria diretórios pai se necessário
        cls._ensure_parent_dirs(user_id, path)

        memory = cls(
            user_id=user_id,
            path=path,
            content=None,
            is_directory=True
        )
        db.session.add(memory)
        return memory

    @classmethod
    def _ensure_parent_dirs(cls, user_id: int, path: str) -> None:
        """Cria diretórios pai se não existirem."""
        parts = path.split('/')
        # Remove o último elemento (arquivo) e elementos vazios
        parts = [p for p in parts[:-1] if p]

        current_path = ''
        for part in parts:
            current_path = f'{current_path}/{part}'
            existing = cls.get_by_path(user_id, current_path)
            if not existing:
                dir_memory = cls(
                    user_id=user_id,
                    path=current_path,
                    content=None,
                    is_directory=True
                )
                db.session.add(dir_memory)

    @classmethod
    def delete_by_path(cls, user_id: int, path: str) -> int:
        """
        Deleta memória por path (e filhos se for diretório).

        Returns:
            Número de registros deletados
        """
        # Se for diretório, deleta todos os filhos também
        count = cls.query.filter(
            cls.user_id == user_id,
            db.or_(
                cls.path == path,
                cls.path.like(f'{path}/%')
            )
        ).delete(synchronize_session=False)

        return count

    @classmethod
    def clear_all_for_user(cls, user_id: int) -> int:
        """Limpa todas as memórias de um usuário."""
        count = cls.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        return count

    @classmethod
    def rename(cls, user_id: int, old_path: str, new_path: str) -> bool:
        """
        Renomeia arquivo ou diretório.

        Returns:
            True se sucesso, False se não encontrado
        """
        memory = cls.get_by_path(user_id, old_path)
        if not memory:
            return False

        # Cria diretórios pai do novo path
        cls._ensure_parent_dirs(user_id, new_path)

        # Se for diretório, renomeia todos os filhos também
        if memory.is_directory:
            children = cls.query.filter(
                cls.user_id == user_id,
                cls.path.like(f'{old_path}/%')
            ).all()

            for child in children:
                child.path = child.path.replace(old_path, new_path, 1)

        memory.path = new_path
        return True


class AgentMemoryVersion(db.Model):
    """
    Histórico de versões de memórias.

    Rastreia mudanças em memórias para auditoria e permite reverter para versões anteriores.
    Implementado conforme spec: specs/memoria-persistente-agent-sdk.md

    Cada vez que uma memória é atualizada (str_replace, create com overwrite, insert),
    a versão anterior é salva nesta tabela antes da modificação.

    Uso:
        - Auditoria de mudanças
        - Recuperação de versões anteriores
        - Análise de padrões de uso

    Campos:
        memory_id: FK para agent_memories.id (com cascade delete)
        content: Conteúdo da versão anterior
        version: Número da versão (1, 2, 3...)
        changed_at: Timestamp da mudança
        changed_by: Quem fez a mudança ('user', 'haiku', 'claude')
    """
    __tablename__ = 'agent_memory_versions'

    id = db.Column(db.Integer, primary_key=True)
    memory_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memories.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Conteúdo da versão anterior
    content = db.Column(db.Text, nullable=True)

    # Número da versão (incrementa a cada update)
    version = db.Column(db.Integer, nullable=False)

    # Timestamp da mudança
    changed_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())

    # Quem fez a mudança
    changed_by = db.Column(db.String(50), nullable=True)  # 'user', 'haiku', 'claude'

    # Relacionamento com AgentMemory (cascade delete via FK)
    memory = db.relationship(
        'AgentMemory',
        backref=db.backref('versions', lazy='dynamic', cascade='all, delete-orphan')
    )

    # Constraint única: uma memória não pode ter duas versões com mesmo número
    __table_args__ = (
        db.UniqueConstraint('memory_id', 'version', name='uq_memory_version'),
    )

    def __repr__(self):
        return f'<AgentMemoryVersion memory={self.memory_id} v{self.version} by={self.changed_by}>'

    # =========================================================================
    # MÉTODOS DE CLASSE
    # =========================================================================

    @classmethod
    def get_latest_version_number(cls, memory_id: int) -> int:
        """
        Retorna o número da última versão para uma memória.

        Args:
            memory_id: ID da memória

        Returns:
            Número da última versão (0 se não houver versões)
        """
        latest = cls.query.filter_by(memory_id=memory_id)\
            .order_by(cls.version.desc())\
            .first()
        return latest.version if latest else 0

    @classmethod
    def save_version(cls, memory_id: int, content: str, changed_by: str = 'claude') -> 'AgentMemoryVersion':
        """
        Salva uma nova versão de uma memória.

        Args:
            memory_id: ID da memória
            content: Conteúdo a ser versionado
            changed_by: Quem fez a mudança ('user', 'haiku', 'claude')

        Returns:
            Instância de AgentMemoryVersion criada
        """
        version_number = cls.get_latest_version_number(memory_id) + 1

        version = cls(
            memory_id=memory_id,
            content=content,
            version=version_number,
            changed_by=changed_by
        )
        db.session.add(version)
        return version

    @classmethod
    def get_versions(cls, memory_id: int, limit: int = 10) -> List['AgentMemoryVersion']:
        """
        Lista versões de uma memória (mais recentes primeiro).

        Args:
            memory_id: ID da memória
            limit: Limite de versões a retornar

        Returns:
            Lista de versões ordenadas por versão DESC
        """
        return cls.query.filter_by(memory_id=memory_id)\
            .order_by(cls.version.desc())\
            .limit(limit)\
            .all()

    @classmethod
    def get_version(cls, memory_id: int, version: int) -> Optional['AgentMemoryVersion']:
        """
        Busca uma versão específica de uma memória.

        Args:
            memory_id: ID da memória
            version: Número da versão

        Returns:
            Instância de AgentMemoryVersion ou None
        """
        return cls.query.filter_by(memory_id=memory_id, version=version).first()
