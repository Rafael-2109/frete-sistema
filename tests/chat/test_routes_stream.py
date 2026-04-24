import uuid
from unittest.mock import patch

import pytest

from app.chat.services.message_service import MessageService
from app.chat.services.system_notifier import SystemNotifier
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


def test_unread_endpoint_zero(client, user_factory, db_session):
    u = user_factory(email=f'un_{_RUN}@t.local')
    _login(client, u)
    resp = client.get('/api/chat/unread')
    assert resp.status_code == 200
    assert resp.json == {'system': 0, 'user': 0}


def test_search_endpoint_no_query(client, user_factory, db_session):
    u = user_factory(email=f'sr_{_RUN}@t.local')
    _login(client, u)
    resp = client.get('/api/chat/search?q=')
    assert resp.status_code == 400


@patch('app.chat.realtime.publisher.publish')
def test_unread_counts_system_messages(mock_pub, client, user_factory, db_session):
    """Regression: SQL NULL semantics — sender_type='system' (sender_user_id IS NULL)
    era excluido silenciosamente por `<>` em NULL retornar NULL (3VL)."""
    u = user_factory(email=f'uns_{_RUN}@t.local')
    SystemNotifier.alert(
        user_ids=[u.id], source='recebimento', titulo='T', content='C',
        deep_link='/x', nivel='INFO',
    )
    _login(client, u)
    resp = client.get('/api/chat/unread')
    assert resp.status_code == 200
    assert resp.json['system'] == 1
    assert resp.json['user'] == 0


@patch('app.chat.realtime.publisher.publish')
def test_unread_counts_user_messages(mock_pub, client, user_factory, db_session):
    """Path feliz: mensagem de outro user deve contar em `user`."""
    a = user_factory(email=f'unu_a_{_RUN}@t.local')
    b = user_factory(email=f'unu_b_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    MessageService.send(sender=a, thread_id=t.id, content='oi b')
    _login(client, b)
    resp = client.get('/api/chat/unread')
    assert resp.status_code == 200
    assert resp.json['user'] == 1
    assert resp.json['system'] == 0


@patch('app.chat.realtime.publisher.publish')
def test_mark_read_happy_path(mock_pub, client, user_factory, db_session):
    a = user_factory(email=f'mr_a_{_RUN}@t.local')
    b = user_factory(email=f'mr_b_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    msg = MessageService.send(sender=a, thread_id=t.id, content='marcar')
    _login(client, b)
    resp = client.post(f'/api/chat/threads/{t.id}/read')
    assert resp.status_code == 200
    assert resp.json['last_read'] == msg.id
    # Apos ler, unread deve zerar
    resp2 = client.get('/api/chat/unread')
    assert resp2.json['user'] == 0


def test_mark_read_non_member(client, user_factory, db_session):
    a = user_factory(email=f'mrn_a_{_RUN}@t.local')
    b = user_factory(email=f'mrn_b_{_RUN}@t.local')
    c = user_factory(email=f'mrn_c_{_RUN}@t.local')
    t = ThreadService.get_or_create_dm(a, b)
    _login(client, c)
    resp = client.post(f'/api/chat/threads/{t.id}/read')
    assert resp.status_code == 403
