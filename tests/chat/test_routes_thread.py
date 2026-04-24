import uuid

import pytest

_RUN = uuid.uuid4().hex[:8]


@pytest.fixture
def client(app):
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    return app.test_client()


def _login(client, user):
    """Simula Flask-Login via session. Requer fresh=True para passar @login_required."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_list_threads_vazio(client, user_factory, db_session):
    u = user_factory(email=f'lt_{_RUN}@t.local')
    _login(client, u)
    resp = client.get('/api/chat/threads')
    assert resp.status_code == 200
    assert resp.json == {'threads': []}


def test_create_dm(client, user_factory, db_session):
    a = user_factory(email=f'cr_a_{_RUN}@t.local')
    b = user_factory(email=f'cr_b_{_RUN}@t.local')
    _login(client, a)
    resp = client.post('/api/chat/threads/dm', json={'target_user_id': b.id})
    assert resp.status_code == 201
    assert resp.json['thread']['tipo'] == 'dm'


def test_create_dm_permission_denied(client, user_factory, db_session):
    a = user_factory(email=f'pd_a_{_RUN}@t.local')  # so NACOM
    b = user_factory(email=f'pd_b_{_RUN}@t.local', carvia=True)  # NACOM+CARVIA
    _login(client, a)
    resp = client.post('/api/chat/threads/dm', json={'target_user_id': b.id})
    assert resp.status_code == 403
