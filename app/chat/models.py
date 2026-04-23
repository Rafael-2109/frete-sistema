"""
Modelos do modulo chat in-app.

Referencia: docs/superpowers/specs/2026-04-23-chat-inapp-design.md secao 4.
"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship

from app import db
from app.utils.timezone import agora_utc_naive


class ChatThread(db.Model):
    __tablename__ = 'chat_threads'

    id = Column(BigInteger, primary_key=True)
    tipo = Column(String(20), nullable=False)  # dm | group | entity | system_dm
    titulo = Column(String(200), nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    sistemas_required = Column(JSONB, nullable=False, default=list)
    criado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = Column(DateTime, nullable=True, onupdate=agora_utc_naive)
    arquivado_em = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)

    criado_por = relationship('Usuario', foreign_keys=[criado_por_id])

    __table_args__ = (
        # Partial unique index: only one thread per entity_type+entity_id when entity_type is set.
        # UniqueConstraint does not support postgresql_where; use Index(unique=True) instead.
        # `text()` evita referencia a Column detached em __table_args__ (garante DDL correto).
        Index(
            'uq_chat_threads_entity',
            'entity_type', 'entity_id',
            unique=True,
            postgresql_where=text("entity_type IS NOT NULL"),
        ),
        # Garante 1 caixa de entrada de sistema por usuario (spec secao 4.1).
        # Previne race condition no SystemNotifier._get_or_create_system_dm.
        Index(
            'uq_chat_threads_system_dm',
            'criado_por_id',
            unique=True,
            postgresql_where=text("tipo = 'system_dm'"),
        ),
        Index('idx_chat_threads_last_msg', 'last_message_at'),
        CheckConstraint("tipo IN ('dm','group','entity','system_dm')", name='ck_chat_threads_tipo'),
    )


class ChatMember(db.Model):
    __tablename__ = 'chat_members'

    id = Column(BigInteger, primary_key=True)
    thread_id = Column(BigInteger, ForeignKey('chat_threads.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    role = Column(String(20), nullable=False, default='member')  # owner | admin | member
    adicionado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    last_read_message_id = Column(BigInteger, ForeignKey('chat_messages.id', use_alter=True), nullable=True)
    # server_default ensures DB-level default; the Python-side __init__ below ensures transient objects
    # also have silenciado=False before any flush (required for correct boolean checks in code/tests).
    silenciado = Column(Boolean, nullable=False, default=False, server_default='false')
    removido_em = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        kwargs.setdefault('silenciado', False)
        super().__init__(**kwargs)

    thread = relationship('ChatThread', backref='members', foreign_keys=[thread_id])
    user = relationship('Usuario', foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_chat_members_user_thread', 'user_id', 'thread_id'),
        # Partial unique: 1 membership ativo por (thread, user). Soft-remove permite re-adicao.
        Index(
            'uq_chat_members_active',
            'thread_id', 'user_id',
            unique=True,
            postgresql_where=text("removido_em IS NULL"),
        ),
        CheckConstraint("role IN ('owner','admin','member')", name='ck_chat_members_role'),
    )


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = Column(BigInteger, primary_key=True)
    thread_id = Column(BigInteger, ForeignKey('chat_threads.id'), nullable=False)
    sender_type = Column(String(10), nullable=False)  # user | system
    sender_user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    sender_system_source = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    content_tsv = Column(TSVECTOR, nullable=True)
    reply_to_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=True)
    deep_link = Column(String(500), nullable=True)
    nivel = Column(String(20), nullable=True)  # INFO | ATENCAO | CRITICO
    dados = Column(JSONB, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)
    editado_em = Column(DateTime, nullable=True)
    deletado_em = Column(DateTime, nullable=True)
    deletado_por_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)

    thread = relationship('ChatThread', backref='messages', foreign_keys=[thread_id])
    sender_user = relationship('Usuario', foreign_keys=[sender_user_id])
    reply_to = relationship('ChatMessage', remote_side=[id], foreign_keys=[reply_to_message_id])

    __table_args__ = (
        Index('idx_chat_messages_thread_time', 'thread_id', 'criado_em'),
        Index('idx_chat_messages_sender_time', 'sender_user_id', 'criado_em',
              postgresql_where=text("sender_type = 'user'")),
        Index('idx_chat_messages_content_tsv', 'content_tsv', postgresql_using='gin'),
        CheckConstraint("sender_type IN ('user','system')", name='ck_chat_messages_sender_type'),
        CheckConstraint(
            "(sender_type='user' AND sender_user_id IS NOT NULL) OR "
            "(sender_type='system' AND sender_system_source IS NOT NULL)",
            name='ck_chat_messages_sender_consistency',
        ),
    )


class ChatAttachment(db.Model):
    __tablename__ = 'chat_attachments'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    s3_key = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    message = relationship('ChatMessage', backref='attachments')


class ChatMention(db.Model):
    __tablename__ = 'chat_mentions'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    mentioned_user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)

    message = relationship('ChatMessage', backref='mentions')
    mentioned_user = relationship('Usuario')


class ChatReaction(db.Model):
    __tablename__ = 'chat_reactions'

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('chat_messages.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    emoji = Column(String(16), nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    message = relationship('ChatMessage', backref='reactions')

    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_chat_reactions'),
    )


class ChatForward(db.Model):
    __tablename__ = 'chat_forwards'

    id = Column(BigInteger, primary_key=True)
    original_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=False)
    forwarded_message_id = Column(BigInteger, ForeignKey('chat_messages.id'), nullable=False)
    forwarded_by_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc_naive)

    original = relationship('ChatMessage', foreign_keys=[original_message_id])
    forwarded = relationship('ChatMessage', foreign_keys=[forwarded_message_id])
    forwarded_by = relationship('Usuario', foreign_keys=[forwarded_by_id])
