import pytest
from unittest.mock import patch
import uuid

from app.chat.services.message_service import MessageService, MessageError
from app.chat.services.thread_service import ThreadService
from app.chat.models import ChatMessage, ChatMention

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


def test_edit_within_window(db_session, user_factory):
    a = user_factory(email=f'ed_a_{_RUN}@t.local')
    b = user_factory(email=f'ed_b_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='v1')
    edited = MessageService.edit(user=a, message_id=msg.id, new_content='v2')
    assert edited.content == 'v2'
    assert edited.editado_em is not None


def test_soft_delete(db_session, user_factory):
    a = user_factory(email=f'del_a_{_RUN}@t.local')
    b = user_factory(email=f'del_b_{_RUN}@t.local')
    thread = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=thread.id, content='tchau')
    MessageService.delete(user=a, message_id=msg.id)
    reloaded = ChatMessage.query.get(msg.id)
    assert reloaded.deletado_em is not None
    assert reloaded.deletado_por_id == a.id
