import uuid
from unittest.mock import patch

import pytest

from app.chat.services.message_service import MessageService
from app.chat.services.thread_service import ThreadService

_RUN = uuid.uuid4().hex[:8]


@pytest.fixture
def client(app):
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    return app.test_client()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


@patch('app.chat.realtime.publisher.publish')
def test_send_message_via_route(mock_pub, client, user_factory, db_session):
    a = user_factory(email=f'rm_a_{_RUN}@t.local')
    b = user_factory(email=f'rm_b_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    _login(client, a)
    resp = client.post('/api/chat/messages', json={
        'thread_id': t.id, 'content': 'oi',
    })
    assert resp.status_code == 201
    assert resp.json['message']['content'] == 'oi'


@patch('app.chat.realtime.publisher.publish')
def test_send_rejects_non_member(mock_pub, client, user_factory, db_session):
    a = user_factory(email=f'nm_a_{_RUN}@t.local')
    b = user_factory(email=f'nm_b_{_RUN}@t.local')
    c = user_factory(email=f'nm_c_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    _login(client, c)
    resp = client.post('/api/chat/messages', json={'thread_id': t.id, 'content': 'intruso'})
    assert resp.status_code == 403


@patch('app.chat.realtime.publisher.publish')
def test_forward_rejects_non_member_of_origin(mock_pub, client, user_factory, db_session):
    """Security: user sem acesso a thread origem nao pode encaminhar (vazamento)."""
    a = user_factory(email=f'fwo_a_{_RUN}@t.local')
    b = user_factory(email=f'fwo_b_{_RUN}@t.local')
    c = user_factory(email=f'fwo_c_{_RUN}@t.local')
    # Thread origem: A-B. Msg da A.
    t_origem = ThreadService.get_or_create_dm(a, b)
    msg_origem = MessageService.send(sender=a, thread_id=t_origem.id, content='segredo')
    # Thread destino: C tem acesso (com B).
    t_destino = ThreadService.get_or_create_dm(c, b)
    # C tenta encaminhar msg de A (thread que C nao eh membro)
    _login(client, c)
    resp = client.post(
        f'/api/chat/messages/{msg_origem.id}/forward',
        json={'destino_thread_id': t_destino.id},
    )
    assert resp.status_code == 403
    assert 'mensagem original' in resp.json['error']


@patch('app.chat.realtime.publisher.publish')
def test_forward_rejects_deleted_message(mock_pub, client, user_factory, db_session):
    """Security: forward nao pode expor content de msg soft-deletada."""
    a = user_factory(email=f'fwd_a_{_RUN}@t.local')
    b = user_factory(email=f'fwd_b_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=t.id, content='sera apagado')
    MessageService.delete(user=a, message_id=msg.id)
    _login(client, a)
    resp = client.post(
        f'/api/chat/messages/{msg.id}/forward',
        json={'destino_thread_id': t.id},
    )
    assert resp.status_code == 400
    assert 'deletada' in resp.json['error']
