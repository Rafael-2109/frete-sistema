"""
Modelos SQLAlchemy para embeddings com pgvector.

Cada dominio (SSW, produtos, extrato, etc.) tem seu proprio modelo
com colunas especificas + coluna `embedding` do tipo vector.

IMPORTANTE: Requer extensao pgvector no PostgreSQL:
    CREATE EXTENSION IF NOT EXISTS vector;
"""

from app import db
from app.utils.timezone import agora_utc_naive


class SswDocumentEmbedding(db.Model):
    """
    Embedding de chunks da documentacao SSW.

    Cada registro corresponde a uma secao (header) de um arquivo .md.
    O chunk_text contem o conteudo da secao, e heading o titulo (## ou #).
    """
    __tablename__ = 'ssw_document_embeddings'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do chunk
    doc_path = db.Column(db.Text, nullable=False)       # Path relativo ao ssw/ (ex: comercial/110-cotacao.md)
    chunk_index = db.Column(db.Integer, nullable=False)  # Indice do chunk no documento (0-based)
    chunk_text = db.Column(db.Text, nullable=False)      # Conteudo textual do chunk
    heading = db.Column(db.Text, nullable=True)          # Titulo da secao (ex: "## Como Usar")
    doc_title = db.Column(db.Text, nullable=True)        # Titulo do documento (primeiro # do arquivo)

    # Embedding — armazenado como TEXT contendo a representacao do vetor
    # Em producao com pgvector: ALTER COLUMN embedding TYPE vector(1024)
    # Sem pgvector: armazenado como JSON string para fallback
    embedding = db.Column(db.Text, nullable=True)

    # Metadados
    char_count = db.Column(db.Integer, nullable=True)    # Tamanho do chunk em caracteres
    token_count = db.Column(db.Integer, nullable=True)   # Tokens estimados (~chars/4)
    model_used = db.Column(db.String(50), nullable=True) # Modelo usado para embedding

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    # Constraint unica: um doc nao pode ter dois chunks com mesmo indice
    __table_args__ = (
        db.UniqueConstraint('doc_path', 'chunk_index', name='uq_ssw_doc_chunk'),
        db.Index('idx_ssw_emb_doc_path', 'doc_path'),
    )

    def __repr__(self):
        return f'<SswDocumentEmbedding {self.doc_path}#{self.chunk_index}>'

    def to_dict(self):
        """Serializa para resposta (sem embedding por ser muito grande)."""
        return {
            'id': self.id,
            'doc_path': self.doc_path,
            'chunk_index': self.chunk_index,
            'heading': self.heading,
            'doc_title': self.doc_title,
            'chunk_text': self.chunk_text[:200] + '...' if len(self.chunk_text or '') > 200 else self.chunk_text,
            'char_count': self.char_count,
        }


class ProductEmbedding(db.Model):
    """
    Embedding de produtos para matching semantico.

    Cada registro corresponde a um produto do cadastro.
    O texto embedado combina nome + tipo + descricao para matching robusto.
    """
    __tablename__ = 'product_embeddings'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do produto
    cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)
    nome_produto = db.Column(db.Text, nullable=False)
    tipo_materia_prima = db.Column(db.String(100), nullable=True)
    texto_embedado = db.Column(db.Text, nullable=False)  # Texto combinado usado para gerar embedding

    # Embedding — mesmo padrao do SswDocumentEmbedding
    embedding = db.Column(db.Text, nullable=True)

    # Metadados
    model_used = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    def __repr__(self):
        return f'<ProductEmbedding {self.cod_produto}>'


class FinancialEntityEmbedding(db.Model):
    """
    Embedding de entidades financeiras (fornecedores e clientes) para matching semantico.

    Cada registro corresponde a um CNPJ raiz (8 digitos) agrupando filiais.
    O texto embedado combina nome canonico + variacoes conhecidas.

    Usado pelo FavorecidoResolverService (Layer 4) e ExtratoMatchingService
    para resolver nomes truncados/abreviados que ILIKE nao consegue.
    """
    __tablename__ = 'financial_entity_embeddings'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao
    entity_type = db.Column(db.String(20), nullable=False)   # 'supplier' ou 'customer'
    cnpj_raiz = db.Column(db.String(8), nullable=False)       # 8 digitos (grupo empresarial)
    cnpj_completo = db.Column(db.String(20), nullable=True)   # Um CNPJ representativo
    nome = db.Column(db.Text, nullable=False)                  # Nome canonico (longest raz_social)
    nomes_alternativos = db.Column(db.Text, nullable=True)    # JSON: variacoes conhecidas
    texto_embedado = db.Column(db.Text, nullable=False)       # Texto usado para embedding

    # Embedding — mesmo padrao do SswDocumentEmbedding/ProductEmbedding
    embedding = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    __table_args__ = (
        db.UniqueConstraint('entity_type', 'cnpj_raiz', name='uq_fin_entity_type_cnpj'),
        db.Index('idx_fin_entity_type', 'entity_type'),
        db.Index('idx_fin_entity_cnpj_raiz', 'cnpj_raiz'),
    )

    def __repr__(self):
        return f'<FinancialEntityEmbedding {self.entity_type}:{self.cnpj_raiz} {self.nome[:30]}>'

    def to_dict(self):
        """Serializa para resposta (sem embedding por ser muito grande)."""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'cnpj_raiz': self.cnpj_raiz,
            'cnpj_completo': self.cnpj_completo,
            'nome': self.nome,
            'nomes_alternativos': self.nomes_alternativos,
        }


class SessionTurnEmbedding(db.Model):
    """
    Embedding de turns (pares user+assistant) de sessoes do agente.

    Cada registro corresponde a um par de mensagens (user -> assistant)
    de uma sessao do agente web. Permite busca semantica em conversas
    passadas ("lembra quando conversamos sobre...").

    Granularidade: turn-level (nao session-level) para precisao na busca.
    """
    __tablename__ = 'session_turn_embeddings'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao
    session_id = db.Column(db.String(255), nullable=False)   # AgentSession.session_id (nosso UUID)
    user_id = db.Column(db.Integer, nullable=False)           # Denormalizado para WHERE
    turn_index = db.Column(db.Integer, nullable=False)        # Indice do par no session (0-based)

    # Conteudo
    user_content = db.Column(db.Text, nullable=False)         # Mensagem do usuario
    assistant_summary = db.Column(db.Text, nullable=True)     # Primeiros 500 chars da resposta
    texto_embedado = db.Column(db.Text, nullable=False)       # Combinado para embedding

    # Embedding
    embedding = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    content_hash = db.Column(db.String(32), nullable=True)    # MD5 para stale detection

    # Metadata de sessao (denormalizado para display)
    session_title = db.Column(db.String(200), nullable=True)
    session_created_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    __table_args__ = (
        db.UniqueConstraint('session_id', 'turn_index', name='uq_session_turn'),
        db.Index('idx_ste_user_id', 'user_id'),
        db.Index('idx_ste_session_id', 'session_id'),
    )

    def __repr__(self):
        return f'<SessionTurnEmbedding {self.session_id[:8]}#{self.turn_index}>'

    def to_dict(self):
        """Serializa para resposta (sem embedding)."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'turn_index': self.turn_index,
            'user_content': self.user_content[:200] + '...' if len(self.user_content or '') > 200 else self.user_content,
            'assistant_summary': self.assistant_summary,
            'session_title': self.session_title,
            'session_created_at': self.session_created_at.isoformat() if self.session_created_at else None,
        }


class AgentMemoryEmbedding(db.Model):
    """
    Embedding de memorias persistentes do agente.

    Cada registro corresponde a um arquivo de memoria (agent_memories)
    do usuario. Permite injecao de memorias por relevancia semantica
    ao inves de recencia.

    FK logica para agent_memories.id — ON DELETE CASCADE via trigger.
    """
    __tablename__ = 'agent_memory_embeddings'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao
    memory_id = db.Column(db.Integer, nullable=False)         # FK logica -> agent_memories.id
    user_id = db.Column(db.Integer, nullable=False)            # Denormalizado para WHERE
    path = db.Column(db.String(500), nullable=False)           # Denormalizado de agent_memories.path

    # Embedding
    texto_embedado = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    content_hash = db.Column(db.String(32), nullable=True)    # MD5 para stale detection

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: agora_utc_naive())
    updated_at = db.Column(db.DateTime, default=lambda: agora_utc_naive(), onupdate=lambda: agora_utc_naive())

    __table_args__ = (
        db.UniqueConstraint('memory_id', name='uq_memory_embedding'),
        db.Index('idx_ame_user_id', 'user_id'),
        db.Index('idx_ame_memory_id', 'memory_id'),
    )

    def __repr__(self):
        return f'<AgentMemoryEmbedding memory_id={self.memory_id} {self.path}>'

    def to_dict(self):
        """Serializa para resposta (sem embedding)."""
        return {
            'id': self.id,
            'memory_id': self.memory_id,
            'path': self.path,
            'content_hash': self.content_hash,
        }
