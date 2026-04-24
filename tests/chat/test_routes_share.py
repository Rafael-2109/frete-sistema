import uuid
from unittest.mock import patch

import pytest

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
def test_share_screen_happy_path(mock_pub, client, user_factory, db_session):
    a = user_factory(email=f'sh_a_{_RUN}@t.local')
    b = user_factory(email=f'sh_b_{_RUN}@t.local')
    _login(client, a)
    resp = client.post('/api/chat/share/screen', json={
        'destinatario_user_id': b.id,
        'url': '/carteira/pedido/VCD123',
        'title': 'Pedido VCD123',
        'comentario': 'confere por favor',
    })
    assert resp.status_code == 201
    assert 'thread_id' in resp.json
    assert 'message_id' in resp.json


@patch('app.chat.realtime.publisher.publish')
def test_entity_message_creates_lazy_thread(mock_pub, client, user_factory, db_session):
    u = user_factory(email=f'em_{_RUN}@t.local')
    _login(client, u)
    # Primeiro post cria a thread
    entity_id = f'VCD_{_RUN}'
    resp = client.post(f'/api/chat/entity/pedido/{entity_id}/message', json={
        'content': 'primeiro comentario',
    })
    assert resp.status_code == 201
    thread_id_1 = resp.json['thread_id']

    # Segundo post reutiliza a MESMA thread
    resp2 = client.post(f'/api/chat/entity/pedido/{entity_id}/message', json={
        'content': 'segundo',
    })
    assert resp2.status_code == 201
    assert resp2.json['thread_id'] == thread_id_1


@patch('app.chat.realtime.publisher.publish')
def test_share_screen_invalid_payload(mock_pub, client, user_factory, db_session):
    u = user_factory(email=f'shi_{_RUN}@t.local')
    _login(client, u)
    resp = client.post('/api/chat/share/screen', json={'url': '/x'})  # sem destinatario
    assert resp.status_code == 400
