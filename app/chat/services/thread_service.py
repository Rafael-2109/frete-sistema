"""
ThreadService — CRUD de chat_thread + lazy creation para DM / system_dm / entity.
"""
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import db
from app.chat.models import ChatThread, ChatMember
from app.chat.services.permission_checker import pode_adicionar


def _dm_lock_key(a_id: int, b_id: int) -> int:
    """Deriva chave estavel para pg_advisory_xact_lock a partir do par (actor, target).

    Combina min/max dos ids em int64 (bigint). User ids sao int32, logo cabem.
    """
    lo, hi = min(a_id, b_id), max(a_id, b_id)
    return (lo << 31) | hi


def _system_dm_lock_key(user_id: int) -> int:
    """Key distinta do DM (bit alto setado para evitar colisao com _dm_lock_key)."""
    return (1 << 62) | user_id


class ThreadService:

    @staticmethod
    def _find_existing_dm(actor_id: int, target_id: int) -> Optional[ChatThread]:
        return db.session.query(ChatThread).filter(
            ChatThread.tipo == 'dm',
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == actor_id, ChatMember.removido_em.is_(None))
            ),
            ChatThread.id.in_(
                db.session.query(ChatMember.thread_id)
                    .filter(ChatMember.user_id == target_id, ChatMember.removido_em.is_(None))
            ),
        ).first()

    @staticmethod
    def get_or_create_dm(actor, target) -> ChatThread:
        """Busca DM entre actor e target, cria se nao existe. Valida permissao.

        Race guard: SELECT + INSERT sem lock pode criar 2 threads em dois requests
        simultaneos (double-click do usuario, por exemplo). Usamos pg_advisory_xact_lock
        para serializar por par (actor, target). Dois requests com mesma key esperam
        em fila ate commit/rollback; sem bloquear outros pares.
        """
        if not pode_adicionar(actor, target):
            raise PermissionError(
                f'Usuario {actor.id} nao pode iniciar DM com {target.id} (permissao cruzada)'
            )

        # Advisory lock de transacao: liberado automaticamente no COMMIT/ROLLBACK.
        # Key estavel por par ordenado — get_or_create_dm(a, b) == get_or_create_dm(b, a).
        db.session.execute(
            text('SELECT pg_advisory_xact_lock(:k)'),
            {'k': _dm_lock_key(actor.id, target.id)},
        )

        existing = ThreadService._find_existing_dm(actor.id, target.id)
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
        """Caixa de entrada do sistema para o usuario (lazy).

        Race guard: `uq_chat_threads_system_dm` (migration) previne duplicata no DB.
        Sem advisory lock, dois workers RQ disparando alert() simultaneamente para
        o mesmo user levam o 2o a receber IntegrityError — aqui fazemos rollback
        + re-fetch para retornar o system_dm criado pelo 1o.
        """
        t = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=user.id).first()
        if t:
            return t

        db.session.execute(
            text('SELECT pg_advisory_xact_lock(:k)'),
            {'k': _system_dm_lock_key(user.id)},
        )
        # Re-check apos lock (pode ter sido criado enquanto esperavamos)
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
        try:
            db.session.commit()
        except IntegrityError:
            # Defesa em profundidade: se lock falhou / constraint ainda engatilhou.
            db.session.rollback()
            winner = ChatThread.query.filter_by(tipo='system_dm', criado_por_id=user.id).first()
            if winner is None:
                raise
            return winner
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
        """Adiciona target como membro de thread. Valida permissao de actor.

        Politica:
        - DM e system_dm sao bilaterais/unilaterais por natureza — nao aceitam add.
        - group/entity: so admin global ou owner da thread adiciona novos membros.
        - pode_adicionar(actor, target) continua valendo como segundo gate (cross-domain).
        """
        # Guard estrutural: DM so tem 2 membros; system_dm so tem 1.
        if thread.tipo in ('dm', 'system_dm'):
            raise PermissionError(f'thread tipo={thread.tipo} nao aceita novos membros')

        # Admin global bypassa demais checks.
        is_admin = getattr(actor, 'perfil', None) == 'administrador'

        if not is_admin:
            # Actor precisa ser membro ativo com role owner para adicionar.
            actor_membership = db.session.query(ChatMember).filter_by(
                thread_id=thread.id,
                user_id=actor.id,
                removido_em=None,
            ).first()
            if actor_membership is None:
                raise PermissionError('actor nao e membro da thread')
            if actor_membership.role not in ('owner', 'admin'):
                raise PermissionError('actor precisa ser owner/admin da thread')

        # Gate cross-domain (sistemas): actor pode "alcancar" target?
        if not pode_adicionar(actor, target):
            raise PermissionError('permissao cruzada negada')

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
