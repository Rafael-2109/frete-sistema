"""Testes da rota GET /api/chat/users/eligible (Fix A + C)."""
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
        sess.clear()
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_lista_elegiveis_exclui_self(client, user_factory, db_session):
    a = user_factory(email=f'el_a_{_RUN}@t.local')
    b = user_factory(email=f'el_b_{_RUN}@t.local')
    _login(client, a)
    # filtra por _RUN para isolar da poluicao do DB local
    resp = client.get(f'/api/chat/users/eligible?q={_RUN}')
    assert resp.status_code == 200
    ids = [u['id'] for u in resp.json['users']]
    assert a.id not in ids
    assert b.id in ids  # mesmas flags -> elegivel


def test_exclui_usuarios_teams(client, user_factory, db_session):
    """Fix C: emails com @teams (robos do Teams) nao aparecem."""
    a = user_factory(email=f'el_a2_{_RUN}@t.local')
    user_factory(email=f'robo_{_RUN}@teams.microsoft.com')
    user_factory(email=f'robo2_{_RUN}@teams.local')
    _login(client, a)
    resp = client.get('/api/chat/users/eligible')
    assert resp.status_code == 200
    emails = [u['email'] for u in resp.json['users']]
    assert not any('@teams' in e for e in emails)


def test_filtro_q_busca_nome_email(client, user_factory, db_session):
    a = user_factory(email=f'el_a3_{_RUN}@t.local')
    alvo = user_factory(email=f'fulano_{_RUN}@t.local', nome=f'Fulano da Silva {_RUN}')
    _login(client, a)
    # Busca por pedaco do nome
    resp = client.get(f'/api/chat/users/eligible?q=Fulano')
    assert resp.status_code == 200
    assert any(u['id'] == alvo.id for u in resp.json['users'])
    # Busca por pedaco do email
    resp = client.get(f'/api/chat/users/eligible?q=fulano_{_RUN}')
    assert any(u['id'] == alvo.id for u in resp.json['users'])


def test_elegiveis_respeita_sistemas_cruzados(client, user_factory, db_session):
    """User com apenas NACOM nao ve users com CARVIA."""
    a = user_factory(email=f'el_nac_{_RUN}@t.local')  # so NACOM
    b = user_factory(email=f'el_car_{_RUN}@t.local', carvia=True)  # NACOM+CARVIA
    _login(client, a)
    resp = client.get('/api/chat/users/eligible')
    ids = [u['id'] for u in resp.json['users']]
    assert b.id not in ids  # b tem superset -> a NAO pode adicionar


def test_limit_cap(client, user_factory, db_session):
    a = user_factory(email=f'el_lim_{_RUN}@t.local')
    _login(client, a)
    resp = client.get('/api/chat/users/eligible?limit=9999')
    # Limit cappado em 50 — nao valida count exato (DB pode ter usuarios historicos),
    # mas garante que request nao explode
    assert resp.status_code == 200
    assert len(resp.json['users']) <= 50


def test_unauth_redirects(client):
    resp = client.get('/api/chat/users/eligible')
    assert resp.status_code == 302  # Flask-Login redirect para login
