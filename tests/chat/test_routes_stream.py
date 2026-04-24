import uuid

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
