"""MessageService — envio, edicao, delecao de mensagens com validacao e publish."""
from datetime import timedelta
from typing import List, Optional

from app import db
from app.auth.models import Usuario
from app.chat.models import ChatMessage, ChatMember, ChatMention, ChatThread, ChatAttachment
from app.chat.markdown_parser import extract_mentions
from app.utils.timezone import agora_utc_naive


MAX_CONTENT_BYTES = 8192
EDIT_WINDOW_MINUTES = 15


class MessageError(Exception):
    pass


def _is_active_member(user_id: int, thread_id: int) -> bool:
    return db.session.query(ChatMember).filter_by(
        thread_id=thread_id, user_id=user_id, removido_em=None,
    ).first() is not None


def _escape_like(value: str) -> str:
    """Escape SQL LIKE metacaracteres. `_` e `%` sao wildcards, `\\` e o escape char.

    Sem isso, mentions como @user_123 viram `LIKE 'user_123@%'` que casa com
    qualquer email de 8 chars + `@` (user_ aaa, userXaaa, etc.) — matches falsos.
    """
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class MessageService:

    @staticmethod
    def send(
        sender,
        thread_id: int,
        content: str,
        reply_to_message_id: Optional[int] = None,
        deep_link: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> ChatMessage:
        if not _is_active_member(sender.id, thread_id):
            raise PermissionError(f'user {sender.id} nao e membro de thread {thread_id}')

        if len(content.encode('utf-8')) > MAX_CONTENT_BYTES:
            raise MessageError(f'Conteudo excede tamanho maximo ({MAX_CONTENT_BYTES} bytes)')

        thread = db.session.get(ChatThread, thread_id)
        if thread is None:
            raise MessageError(f'Thread {thread_id} nao existe')

        msg = ChatMessage(
            thread_id=thread_id,
            sender_type='user',
            sender_user_id=sender.id,
            content=content,
            reply_to_message_id=reply_to_message_id,
            deep_link=deep_link,
        )
        db.session.add(msg)
        db.session.flush()  # obter msg.id e msg.criado_em

        # Mentions — so valem se mencionado e membro ativo (e nao e o proprio sender)
        usernames = extract_mentions(content)
        mentioned_ids: set[int] = set()
        if usernames:
            member_ids = {
                r.user_id for r in db.session.query(ChatMember).filter(
                    ChatMember.thread_id == thread_id,
                    ChatMember.removido_em.is_(None),
                ).all()
            }
            resolved = db.session.query(Usuario).filter(
                db.or_(*[
                    Usuario.email.like(f'{_escape_like(u)}@%', escape='\\')
                    for u in usernames
                ])
            ).all()
            for u in resolved:
                if u.id in member_ids and u.id != sender.id:
                    db.session.add(ChatMention(message_id=msg.id, mentioned_user_id=u.id))
                    mentioned_ids.add(u.id)

        # Anexos
        for att in (attachments or []):
            db.session.add(ChatAttachment(
                message_id=msg.id,
                s3_key=att['s3_key'], filename=att['filename'],
                mime_type=att['mime_type'], size_bytes=att['size_bytes'],
            ))

        thread.last_message_at = msg.criado_em
        db.session.commit()

        MessageService._publish_new(msg, thread, mentioned_ids)
        return msg

    @staticmethod
    def _publish_new(msg: ChatMessage, thread: ChatThread, mentioned_ids: set):
        from app.chat.realtime.publisher import publish  # import aqui para facilitar mock

        recipients = db.session.query(ChatMember).filter(
            ChatMember.thread_id == thread.id,
            ChatMember.removido_em.is_(None),
            ChatMember.user_id != (msg.sender_user_id or 0),
        ).all()

        for r in recipients:
            publish(r.user_id, 'message_new', {
                'thread_id': thread.id,
                'message_id': msg.id,
                'preview': (msg.content or '')[:100],
                'sender_user_id': msg.sender_user_id,
                'sender_type': msg.sender_type,
                'urgente': r.user_id in mentioned_ids,
                'deep_link': msg.deep_link,
                'criado_em': msg.criado_em.isoformat() if msg.criado_em else None,
            })

    @staticmethod
    def edit(user, message_id: int, new_content: str) -> ChatMessage:
        msg = db.session.get(ChatMessage, message_id)
        if msg is None:
            raise MessageError('Mensagem nao existe')
        if msg.sender_user_id != user.id:
            raise PermissionError('so o autor pode editar')
        if agora_utc_naive() - msg.criado_em > timedelta(minutes=EDIT_WINDOW_MINUTES):
            raise MessageError('janela de edicao expirada (15 min)')
        if len(new_content.encode('utf-8')) > MAX_CONTENT_BYTES:
            raise MessageError('conteudo excede tamanho maximo')
        msg.content = new_content
        msg.editado_em = agora_utc_naive()
        db.session.commit()

        from app.chat.realtime.publisher import publish
        for m in db.session.query(ChatMember).filter(
            ChatMember.thread_id == msg.thread_id,
            ChatMember.removido_em.is_(None),
        ).all():
            publish(m.user_id, 'message_edit', {
                'thread_id': msg.thread_id, 'message_id': msg.id, 'new_content': msg.content,
            })
        return msg

    @staticmethod
    def delete(user, message_id: int):
        msg = db.session.get(ChatMessage, message_id)
        if msg is None:
            raise MessageError('Mensagem nao existe')
        if msg.sender_user_id != user.id and user.perfil != 'administrador':
            raise PermissionError('so autor ou admin pode deletar')
        msg.deletado_em = agora_utc_naive()
        msg.deletado_por_id = user.id
        db.session.commit()

    @staticmethod
    def list_for_thread(user, thread_id: int, limit: int = 50, before_id: Optional[int] = None):
        """Lista mensagens da thread, mais recentes primeiro, com paginacao reverse-cursor."""
        if not _is_active_member(user.id, thread_id):
            raise PermissionError('nao e membro da thread')
        q = ChatMessage.query.filter_by(thread_id=thread_id).filter(ChatMessage.deletado_em.is_(None))
        if before_id is not None:
            q = q.filter(ChatMessage.id < before_id)
        return q.order_by(ChatMessage.id.desc()).limit(limit).all()
