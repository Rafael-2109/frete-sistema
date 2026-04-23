"""
ThreadService — CRUD de chat_thread + lazy creation para DM / system_dm / entity.
"""
from typing import Optional

from app import db
from app.chat.models import ChatThread, ChatMember
from app.chat.services.permission_checker import pode_adicionar


class ThreadService:

    @staticmethod
    def get_or_create_dm(actor, target) -> ChatThread:
        """Busca DM entre actor e target, cria se nao existe. Valida permissao."""
        if not pode_adicionar(actor, target):
            raise PermissionError(
                f'Usuario {actor.id} nao pode iniciar DM com {target.id} (permissao cruzada)'
            )

        # DM existente: thread tipo=dm onde ambos sao membros ativos
        existing = db.session.query(ChatThread).filter(
            ChatThread.tipo == 'dm',
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == actor.id, ChatMember.removido_em.is_(None))
            ),
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == target.id, ChatMember.removido_em.is_(None))
            ),
        ).first()

        if existing:
            return existing

        thread = ChatThread(
            tipo='dm',
            criado_por_id=actor.id,
            sistemas_required=[],
        )
        db.session.add(thread)
        db.session.flush()

        for u in (actor, target):
            db.session.add(ChatMember(
                thread_id=thread.id,
                user_id=u.id,
                role='member',
                adicionado_por_id=actor.id,
            ))
        db.session.commit()
        return thread

    @staticmethod
    def get_or_create_system_dm(user) -> ChatThread:
        """Caixa de entrada do sistema para o usuario (lazy)."""
        t = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=user.id).first()
        if t:
            return t
        t = ChatThread(tipo='system_dm', criado_por_id=user.id, sistemas_required=[])
        db.session.add(t)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=t.id,
            user_id=user.id,
            role='owner',
        ))
        db.session.commit()
        return t

    @staticmethod
    def get_entity_thread(entity_type: str, entity_id: str) -> Optional[ChatThread]:
        """Busca thread de entidade sem criar (lazy read)."""
        return ChatThread.query.filter_by(entity_type=entity_type, entity_id=entity_id).first()

    @staticmethod
    def create_entity_thread(entity_type: str, entity_id: str, creator) -> ChatThread:
        """Cria thread vinculada a entidade do sistema (pedido, embarque, etc.)."""
        thread = ChatThread(
            tipo='entity',
            entity_type=entity_type,
            entity_id=entity_id,
            criado_por_id=creator.id,
            sistemas_required=[],
        )
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatMember(
            thread_id=thread.id,
            user_id=creator.id,
            role='owner',
            adicionado_por_id=creator.id,
        ))
        db.session.commit()
        return thread

    @staticmethod
    def add_member(thread: ChatThread, actor, target, role: str = 'member') -> ChatMember:
        """Adiciona target como membro de thread. Valida permissao de actor."""
        if not pode_adicionar(actor, target):
            raise PermissionError('permissao negada')
        mem = ChatMember(
            thread_id=thread.id,
            user_id=target.id,
            role=role,
            adicionado_por_id=actor.id,
        )
        db.session.add(mem)
        db.session.commit()
        return mem

    @staticmethod
    def list_threads_for_user(user, tipo: Optional[str] = None, limit: int = 50):
        """Lista threads do usuario (membro ativo, thread nao arquivada)."""
        q = db.session.query(ChatThread).join(
            ChatMember, ChatMember.thread_id == ChatThread.id
        ).filter(
            ChatMember.user_id == user.id,
            ChatMember.removido_em.is_(None),
            ChatThread.arquivado_em.is_(None),
        )
        if tipo:
            q = q.filter(ChatThread.tipo == tipo)
        return q.order_by(ChatThread.last_message_at.desc().nullslast()).limit(limit).all()
