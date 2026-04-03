"""
Modelos SQLAlchemy do Agente.

FEAT-011: Lista de Sessões
FEAT-030: Histórico de Mensagens Persistente

Arquitetura:
- Histórico COMPLETO armazenado no campo `data` (JSONB)
- SDK usado apenas como canal de comunicação (pode expirar)
- Quando SDK expira, injeta histórico de mensagens como contexto
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid

from app import db
from app.utils.timezone import agora_utc_naive


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

    # Transcript JSONL do SDK para restore após reciclagem do worker (Bug Teams #1)
    # TEXT separado do JSONB `data` para evitar overhead de reescrita JSONB.
    # PostgreSQL TEXT suporta até 1GB — suficiente para sessões longas.
    sdk_session_transcript = db.Column(db.Text, nullable=True)

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

    # =========================================================================
    # MÉTODOS DE PERSISTÊNCIA DE TRANSCRIPT (Bug Teams #1)
    # =========================================================================

    def save_transcript(self, transcript: str) -> None:
        """
        Salva transcript JSONL do SDK no banco.

        Chamado após cada resposta do SDK para permitir restore
        caso o worker Render recicle e perca o arquivo do disco.

        Args:
            transcript: Conteúdo completo do JSONL como string
        """
        self.sdk_session_transcript = transcript
        self.updated_at = agora_utc_naive()

    def get_transcript(self) -> Optional[str]:
        """
        Retorna transcript JSONL salvo no banco.

        Returns:
            Conteúdo do JSONL ou None se nunca salvo
        """
        return self.sdk_session_transcript

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

    # Importance scoring (QW-1): peso heurístico 0-1
    # Usado no retrieval junto com recency decay e cosine similarity
    importance_score = db.Column(db.Float, default=0.5, nullable=False)

    # Último acesso (QW-1): quando a memória foi injetada/lida pela última vez
    # Usado para calcular recency decay no retrieval
    last_accessed_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), nullable=False)

    # ── Taxonomia v2: categoria + permanência (Memory System v2) ──
    # Categorias: permanent, structural, operational (default), contextual, cold
    # permanent: regras de escopo, permissões, identidade — sem decay
    # structural: gotchas Odoo, campos que não existem — decay lento (~60d meia-vida)
    # operational: workflows, preferências de formato — decay médio (~30d)
    # contextual: alertas, estado sistema, sessões recentes — decay rápido (~3d)
    # cold: memórias depreciadas — só busca explícita, sem injeção automática
    category = db.Column(db.String(20), default='operational', nullable=False, index=True)

    # Flag para memórias movidas para tier frio (sem injeção automática)
    is_cold = db.Column(db.Boolean, default=False, nullable=False)

    # ── Feedback Loop v2: rastreamento de uso e efetividade ──
    # Quantas vezes esta memória foi injetada no contexto
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    # Quantas vezes o Agent usou conteúdo desta memória na resposta
    effective_count = db.Column(db.Integer, default=0, nullable=False)
    # Quantas vezes o usuário corrigiu após injeção desta memória
    correction_count = db.Column(db.Integer, default=0, nullable=False)
    # Flag para memórias com potencial contradição detectada
    has_potential_conflict = db.Column(db.Boolean, default=False, nullable=False)

    # ── Memoria Compartilhada: escopo + auditoria (PRD v2.1) ──
    # escopo='pessoal': memoria individual (default, comportamento atual)
    # escopo='empresa': memoria compartilhada (user_id=0, visivel para todos)
    escopo = db.Column(db.String(20), default='pessoal', nullable=False)

    # Quem originou a memoria empresa (auditoria). NULL para pessoais.
    created_by = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id', ondelete='SET NULL'),
        nullable=True,
    )

    # Ciclo de revisao (v5): ultima vez que conteudo foi validado
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    # Relacionamento - cascade delete quando usuário é deletado
    user = db.relationship(
        'Usuario',
        foreign_keys=[user_id],
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
        changed_by: Quem fez a mudança ('user', 'sonnet', 'claude')
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
    changed_by = db.Column(db.String(50), nullable=True)  # 'user', 'sonnet', 'claude'

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
            changed_by: Quem fez a mudança ('user', 'sonnet', 'claude')

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


class AgentMemoryEntity(db.Model):
    """
    Nó do Knowledge Graph — entidade canônica extraída de memórias.

    T3-3: Knowledge Graph Simplificado.

    Cada entidade é única por (user_id, entity_type, entity_name).
    entity_key é um ID canônico opcional (CNPJ raiz, cod_produto, UF).

    Entity types:
        - uf: Estado brasileiro (SP, AM, etc.)
        - pedido: Número de pedido (VCD2565291)
        - cnpj: CNPJ raiz (8 dígitos)
        - valor: Valor monetário (R$ X.XXX)
        - transportadora: Nome normalizado
        - produto: Nome normalizado
        - cliente: Nome normalizado
        - fornecedor: Nome normalizado
        - regra: Regra de negócio (semântico, via Sonnet)
    """
    __tablename__ = 'agent_memory_entities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)

    # Tipo da entidade (uf, pedido, cnpj, transportadora, produto, etc.)
    entity_type = db.Column(db.String(30), nullable=False)

    # Nome normalizado (uppercase, sem acentos)
    entity_name = db.Column(db.String(200), nullable=False)

    # ID canônico opcional (CNPJ raiz, cod_produto, UF)
    entity_key = db.Column(db.String(100), nullable=True)

    # Contagem de menções (tracking para GC de entidades órfãs)
    mention_count = db.Column(db.Integer, nullable=False, default=1)

    # Timestamps
    first_seen_at = db.Column(db.DateTime, nullable=False, default=lambda: agora_utc_naive())
    last_seen_at = db.Column(db.DateTime, nullable=False, default=lambda: agora_utc_naive())

    __table_args__ = (
        db.UniqueConstraint('user_id', 'entity_type', 'entity_name', name='uq_user_entity'),
        db.Index('idx_ame_user_type', 'user_id', 'entity_type'),
        db.Index('idx_ame_entity_key', 'entity_key', postgresql_where=db.text('entity_key IS NOT NULL')),
    )

    def __repr__(self):
        return f'<AgentMemoryEntity {self.entity_type}:{self.entity_name} user={self.user_id}>'


class AgentMemoryEntityLink(db.Model):
    """
    Link entre entidade e memória — indica que a entidade foi mencionada na memória.

    T3-3: Knowledge Graph Simplificado.

    relation_type:
        - 'mentions': menção genérica (default)
        - 'corrects': memória corrige informação sobre a entidade
        - 'prefers': memória indica preferência sobre a entidade
    """
    __tablename__ = 'agent_memory_entity_links'

    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memory_entities.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    memory_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memories.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    # Tipo de relação: mentions, corrects, prefers
    relation_type = db.Column(db.String(30), nullable=False, default='mentions')

    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: agora_utc_naive())

    # Relacionamentos
    entity = db.relationship('AgentMemoryEntity', backref=db.backref('links', lazy='dynamic'))
    memory = db.relationship('AgentMemory', backref=db.backref('entity_links', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('entity_id', 'memory_id', 'relation_type', name='uq_entity_memory_link'),
    )

    def __repr__(self):
        return f'<AgentMemoryEntityLink entity={self.entity_id} memory={self.memory_id} rel={self.relation_type}>'


class AgentMemoryEntityRelation(db.Model):
    """
    Relação semântica entre entidades (ex: RODONAVES atrasa_para AM).

    T3-3: Knowledge Graph Simplificado.

    relation_type:
        - 'co_occurs': entidades coocorrem na mesma memória (default)
        - Semânticos via Sonnet: 'atrasa_para', 'melhor_para', 'fornece', etc.
    """
    __tablename__ = 'agent_memory_entity_relations'

    id = db.Column(db.Integer, primary_key=True)
    source_entity_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memory_entities.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    target_entity_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memory_entities.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    # Tipo da relação (co_occurs, atrasa_para, melhor_para, etc.)
    relation_type = db.Column(db.String(50), nullable=False, default='co_occurs')

    # Peso da relação (para ranking)
    weight = db.Column(db.Float, nullable=False, default=1.0)

    # Memória que originou a relação (NULL se removida)
    memory_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_memories.id', ondelete='SET NULL'),
        nullable=True,
    )

    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: agora_utc_naive())

    # Relacionamentos
    source_entity = db.relationship(
        'AgentMemoryEntity',
        foreign_keys=[source_entity_id],
        backref=db.backref('outgoing_relations', lazy='dynamic'),
    )
    target_entity = db.relationship(
        'AgentMemoryEntity',
        foreign_keys=[target_entity_id],
        backref=db.backref('incoming_relations', lazy='dynamic'),
    )

    __table_args__ = (
        db.UniqueConstraint(
            'source_entity_id', 'target_entity_id', 'relation_type',
            name='uq_entity_relation',
        ),
    )

    def __repr__(self):
        return (
            f'<AgentMemoryEntityRelation '
            f'src={self.source_entity_id} {self.relation_type} tgt={self.target_entity_id}>'
        )


class AgentIntelligenceReport(db.Model):
    """
    Relatorio de inteligencia do agente (D7 do cron semanal).

    Bridge Agent SDK <-> Claude Code: persiste metricas, recomendacoes prescritivas
    e backlog acumulado. Lido pelo intersession_briefing (agente) e via MCP (Claude Code).

    report_json contem:
        - period: {start, end, days}
        - metrics: {sessions, cost, resolution_rate, unique_users}
        - tool_effectiveness: [{tool, calls, category, trend}]
        - skill_gaps: [{topic, frequency, tools_available, recommendation}]
        - friction_hotspots: [{pattern, count, suggestion}]
        - memory_corrections: [{path, corrections, suggestion}]
        - recommendations: [{id, severity, title, description, affected_files, suggested_action, weeks_open}]

    backlog_json: lista de recomendacoes acumuladas de semanas anteriores (auto-escalate apos 4 semanas).
    """
    __tablename__ = 'agent_intelligence_reports'

    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, unique=True, nullable=False, index=True)

    # Metricas de resumo (para queries rapidas sem parsear JSONB)
    health_score = db.Column(db.Numeric(5, 1), default=0)
    friction_score = db.Column(db.Numeric(5, 1), default=0)
    recommendation_count = db.Column(db.Integer, default=0)
    sessions_analyzed = db.Column(db.Integer, default=0)

    # Conteudo completo
    report_json = db.Column(db.JSON, nullable=False)
    report_markdown = db.Column(db.Text, nullable=False)
    backlog_json = db.Column(db.JSON, default=list)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    def __repr__(self):
        return f'<AgentIntelligenceReport {self.report_date} score={self.health_score}>'

    @classmethod
    def get_latest(cls) -> Optional['AgentIntelligenceReport']:
        """Retorna o relatorio mais recente."""
        return cls.query.order_by(cls.report_date.desc()).first()

    @classmethod
    def upsert(
        cls,
        report_date,
        health_score: float,
        friction_score: float,
        recommendation_count: int,
        sessions_analyzed: int,
        report_json: dict,
        report_markdown: str,
        backlog_json: list,
    ) -> 'AgentIntelligenceReport':
        """
        Insere ou atualiza relatorio para uma data (UNIQUE constraint em report_date).

        Returns:
            Instancia criada/atualizada
        """
        from sqlalchemy.orm.attributes import flag_modified

        existing = cls.query.filter_by(report_date=report_date).first()

        if existing:
            existing.health_score = health_score
            existing.friction_score = friction_score
            existing.recommendation_count = recommendation_count
            existing.sessions_analyzed = sessions_analyzed
            existing.report_json = report_json
            existing.report_markdown = report_markdown
            existing.backlog_json = backlog_json
            existing.updated_at = agora_utc_naive()
            flag_modified(existing, 'report_json')
            flag_modified(existing, 'backlog_json')
            return existing

        report = cls(
            report_date=report_date,
            health_score=health_score,
            friction_score=friction_score,
            recommendation_count=recommendation_count,
            sessions_analyzed=sessions_analyzed,
            report_json=report_json,
            report_markdown=report_markdown,
            backlog_json=backlog_json,
        )
        db.session.add(report)
        return report


class AgentImprovementDialogue(db.Model):
    """
    Dialogo versionado de melhoria continua entre Agent SDK e Claude Code.

    Agent SDK escreve sugestoes (v1), Claude Code avalia/implementa (v2),
    Agent SDK verifica se atende (v3). Max 3 versoes por suggestion_key.

    Status lifecycle:
        proposed -> responded -> verified -> closed
        proposed -> rejected (por Claude Code)
        responded -> needs_revision (por Agent SDK, gera v3)

    Categorias:
        skill_suggestion: skills que ajudariam mas nao existem
        instruction_request: instrucoes/clarificacoes que o agente precisa
        prompt_feedback: feedback sobre system_prompt e memorias
        gotcha_report: armadilhas e informacoes uteis
        memory_feedback: memorias que estao incorretas ou faltando
    """
    __tablename__ = 'agent_improvement_dialogue'

    id = db.Column(db.Integer, primary_key=True)

    # Identidade do dialogo
    suggestion_key = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)

    # Autoria e status
    author = db.Column(db.String(20), nullable=False)  # 'agent_sdk' | 'claude_code'
    status = db.Column(db.String(20), nullable=False, default='proposed')

    # Conteudo
    category = db.Column(db.String(30), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default='info')
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_json = db.Column(db.JSON, default=dict)

    # Campos de resposta (preenchidos por Claude Code)
    affected_files = db.Column(db.ARRAY(db.Text), nullable=True)
    implementation_notes = db.Column(db.Text, nullable=True)
    auto_implemented = db.Column(db.Boolean, default=False)

    # Rastreabilidade
    source_session_ids = db.Column(db.ARRAY(db.Text), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: agora_utc_naive(),
        onupdate=lambda: agora_utc_naive(),
    )

    __table_args__ = (
        db.UniqueConstraint('suggestion_key', 'version', name='uq_aid_key_version'),
    )

    def __repr__(self):
        return (
            f'<AgentImprovementDialogue {self.suggestion_key} '
            f'v{self.version} {self.status} by={self.author}>'
        )

    # =========================================================================
    # CLASSMETHODS
    # =========================================================================

    @classmethod
    def generate_key(cls) -> str:
        """Gera suggestion_key unica: IMP-YYYY-MM-DD-NNN."""
        from app.utils.timezone import agora_utc_naive
        today = agora_utc_naive().strftime('%Y-%m-%d')
        # Conta sugestoes do dia para gerar sequencial
        count = cls.query.filter(
            cls.suggestion_key.like(f'IMP-{today}-%'),
            cls.version == 1,
        ).count()
        return f'IMP-{today}-{count + 1:03d}'

    @classmethod
    def create_suggestion(
        cls,
        category: str,
        severity: str,
        title: str,
        description: str,
        evidence: Optional[Dict] = None,
        session_ids: Optional[List[str]] = None,
    ) -> 'AgentImprovementDialogue':
        """
        Cria nova sugestao do Agent SDK (v1).

        Returns:
            Instancia criada
        """
        suggestion = cls(
            suggestion_key=cls.generate_key(),
            version=1,
            author='agent_sdk',
            status='proposed',
            category=category,
            severity=severity,
            title=title,
            description=description,
            evidence_json=evidence or {},
            source_session_ids=session_ids or [],
        )
        db.session.add(suggestion)
        return suggestion

    @classmethod
    def get_pending_suggestions(cls, limit: int = 10) -> List['AgentImprovementDialogue']:
        """
        Retorna sugestoes pendentes para Claude Code avaliar.

        Usado pelo D8 cron via query no Render Postgres.
        """
        return cls.query.filter_by(
            status='proposed',
            author='agent_sdk',
            version=1,
        ).order_by(
            db.case(
                (cls.severity == 'critical', 0),
                (cls.severity == 'warning', 1),
                else_=2,
            ),
            cls.created_at.asc(),
        ).limit(limit).all()

    @classmethod
    def get_unverified_responses(cls, days: int = 14) -> List['AgentImprovementDialogue']:
        """
        Retorna respostas de Claude Code que o Agent SDK ainda nao verificou.

        Usado pelo intersession_briefing para injetar no contexto do agente.
        """
        cutoff = agora_utc_naive() - __import__('datetime').timedelta(days=days)
        return cls.query.filter(
            cls.author == 'claude_code',
            cls.status == 'responded',
            cls.created_at >= cutoff,
        ).order_by(cls.created_at.desc()).limit(5).all()

    @classmethod
    def get_open_by_category(cls) -> List['AgentImprovementDialogue']:
        """
        Retorna sugestoes abertas agrupadas por categoria.

        Usado para dedup antes de criar nova sugestao.
        """
        return cls.query.filter(
            cls.status.in_(['proposed', 'responded']),
            cls.version == 1,
        ).all()

    @classmethod
    def get_recently_rejected(cls, days: int = 7) -> List['AgentImprovementDialogue']:
        """
        Retorna sugestoes rejeitadas nos ultimos N dias.

        Evita re-geracao ciclica: Sonnet nao deve sugerir novamente
        algo que o Claude Code ja avaliou e descartou.
        """
        from app.utils.timezone import agora_utc_naive
        cutoff = agora_utc_naive() - __import__('datetime').timedelta(days=days)
        return cls.query.filter(
            cls.status == 'rejected',
            cls.updated_at >= cutoff,
        ).all()

    @classmethod
    def upsert_response(
        cls,
        suggestion_key: str,
        version: int,
        author: str,
        status: str,
        description: str,
        implementation_notes: Optional[str] = None,
        affected_files: Optional[List[str]] = None,
        auto_implemented: bool = False,
    ) -> 'AgentImprovementDialogue':
        """
        Insere ou atualiza resposta (v2 de Claude Code ou v3 de Agent SDK).

        Tambem atualiza o status da versao anterior (v1 ou v2).
        """
        from sqlalchemy.orm.attributes import flag_modified

        existing = cls.query.filter_by(
            suggestion_key=suggestion_key,
            version=version,
        ).first()

        if existing:
            existing.author = author
            existing.status = status
            existing.description = description
            existing.implementation_notes = implementation_notes
            existing.affected_files = affected_files
            existing.auto_implemented = auto_implemented
            existing.updated_at = agora_utc_naive()
            if existing.evidence_json:
                flag_modified(existing, 'evidence_json')

            # Atualizar status da versao anterior (bug fix: path existing nao atualizava v1)
            prev_version = version - 1
            prev = cls.query.filter_by(
                suggestion_key=suggestion_key,
                version=prev_version,
            ).first()
            if prev and prev.status not in (status, 'closed'):
                prev.status = status
                prev.updated_at = agora_utc_naive()

            return existing

        # Buscar v1 para copiar category/severity/title
        v1 = cls.query.filter_by(
            suggestion_key=suggestion_key,
            version=1,
        ).first()

        if not v1:
            raise ValueError(f"suggestion_key {suggestion_key} nao encontrada")

        # Atualizar status da versao anterior
        prev_version = version - 1
        prev = cls.query.filter_by(
            suggestion_key=suggestion_key,
            version=prev_version,
        ).first()
        if prev:
            prev.status = status
            prev.updated_at = agora_utc_naive()

        response = cls(
            suggestion_key=suggestion_key,
            version=version,
            author=author,
            status=status,
            category=v1.category,
            severity=v1.severity,
            title=v1.title,
            description=description,
            evidence_json={},
            affected_files=affected_files,
            implementation_notes=implementation_notes,
            auto_implemented=auto_implemented,
            source_session_ids=v1.source_session_ids,
        )
        db.session.add(response)
        return response
