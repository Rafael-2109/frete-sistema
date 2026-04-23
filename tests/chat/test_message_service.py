import pytest
from unittest.mock import patch
import uuid

from app import db
from app.chat.services.message_service import MessageService, MessageError
from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatMessage, ChatMention, ChatMember, ChatThread

# Prefixo unico por run para evitar colisao de emails em DB com commits persistidos
_RUN = uuid.uuid4().hex[:8]


@patch('app.chat.realtime.publisher.publish')
def test_send_simple(mock_pub, db_session, user_factory):
    a = user_factory(email=f'ms_a_{_RUN}@t.local')
    b = user_factory(email=f'ms_b_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)

    msg = MessageService.send(sender=a, thread_id=thread.id, content='Oi!')
    assert msg.id is not None
    assert msg.sender_type == 'user'
    assert msg.content == 'Oi!'
    assert mock_pub.called
    called_user_ids = [c.args[0] for c in mock_pub.call_args_list]
    assert b.id in called_user_ids
    assert a.id not in called_user_ids


def test_send_rejects_non_member(db_session, user_factory):
    a = user_factory(email=f'ms_na_{_RUN}@t.local')
    b = user_factory(email=f'ms_nb_{_RUN}@t.local')
    c = user_factory(email=f'ms_nc_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    with pytest.raises(PermissionError):
        MessageService.send(sender=c, thread_id=thread.id, content='intruso')


def test_send_rejects_oversized(db_session, user_factory):
    a = user_factory(email=f'ms_o1_{_RUN}@t.local')
    b = user_factory(email=f'ms_o2_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    huge = 'x' * 9000
    with pytest.raises(MessageError, match='tamanho'):
        MessageService.send(sender=a, thread_id=thread.id, content=huge)


@patch('app.chat.realtime.publisher.publish')
def test_send_with_mentions_persists_rows(mock_pub, db_session, user_factory):
    # username = "alice_<run>" e "bob_<run>" para matching unico por run
    alice_name = f'alice_{_RUN}'
    bob_name = f'bob_{_RUN}'
    a = user_factory(email=f'{alice_name}@t.local')
    b = user_factory(email=f'{bob_name}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content=f'olhe @{bob_name} isso')
    mentions = ChatMention.query.filter_by(message_id=msg.id).all()
    assert any(m.mentioned_user_id == b.id for m in mentions)


@patch('app.chat.realtime.publisher.publish')
def test_send_with_mention_escapes_like_wildcards(mock_pub, db_session, user_factory):
    """Regression: `_` e wildcard LIKE single-char. Sem escape, @userWS_1 casa com
    userWSX1, userWSY1, etc. Thread com 3 membros: sender + alvo literal + falso positivo.
    Mencao `@userWS_1_<run>` deve resolver APENAS o alvo literal."""
    sender = user_factory(email=f'ms_sender_{_RUN}@t.local')
    u_exato = user_factory(email=f'userWS_1_{_RUN}@t.local')
    u_falso = user_factory(email=f'userWSX1_{_RUN}@t.local')  # casaria sem escape do `_`

    # Criar group thread com 3 membros (sender, u_exato, u_falso)
    thread = ChatThread(tipo='group', titulo=f'regression_{_RUN}', criado_por_id=sender.id)
    db.session.add(thread)
    db.session.flush()
    for u in (sender, u_exato, u_falso):
        db.session.add(ChatMember(thread_id=thread.id, user_id=u.id, role='member'))
    db.session.commit()

    msg = MessageService.send(
        sender=sender, thread_id=thread.id,
        content=f'ola @userWS_1_{_RUN}',
    )
    mentioned_ids = {
        m.mentioned_user_id for m in ChatMention.query.filter_by(message_id=msg.id).all()
    }
    assert u_exato.id in mentioned_ids        # resolve o literal
    assert u_falso.id not in mentioned_ids    # `_` escapado nao casa com 'X'


@patch('app.chat.realtime.publisher.publish')
def test_edit_within_window(mock_pub, db_session, user_factory):
    a = user_factory(email=f'ed_a_{_RUN}@t.local')
    b = user_factory(email=f'ed_b_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='v1')
    edited = MessageService.edit(user=a, message_id=msg.id, new_content='v2')
    assert edited.content == 'v2'
    assert edited.editado_em is not None


@patch('app.chat.realtime.publisher.publish')
def test_soft_delete(mock_pub, db_session, user_factory):
    a = user_factory(email=f'del_a_{_RUN}@t.local')
    b = user_factory(email=f'del_b_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='tchau')
    MessageService.delete(user=a, message_id=msg.id)
    db.session.expire_all()  # forcar SELECT em vez de identity map
    reloaded = db.session.get(ChatMessage, msg.id)
    assert reloaded is not None
    assert reloaded.deletado_em is not None
    assert reloaded.deletado_por_id == a.id
