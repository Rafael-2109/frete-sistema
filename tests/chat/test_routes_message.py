import uuid
from unittest.mock import patch

import pytest

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
