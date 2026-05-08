"""Testa endpoint GET /api/onboarding/permissoes-matriz.

Padrao seguido: tests/chat/test_routes_stream.py (login via session['_user_id']).
LOGIN_DISABLED=True esta no root conftest; quando precisamos validar redirect
de @login_required, usamos `app.config['LOGIN_DISABLED']=False` por teste.
"""
import uuid

import pytest

from app import db as _db
from app.auth.models import Usuario
from app.hora.models.permissao import HoraUserPermissao


_RUN = uuid.uuid4().hex[:8]


def _criar_usuario(perfil='vendedor', email_suffix='u'):
    """Cria usuario unico por teste para evitar colisao de UNIQUE(email)."""
    email = f'{email_suffix}_{_RUN}_{uuid.uuid4().hex[:6]}@onb.local'
    u = Usuario(
        nome='teste-onb',
        email=email,
        senha_hash='x' * 60,
        perfil=perfil,
        status='ativo',
        sistema_carvia=False,
        sistema_motochefe=False,
        sistema_logistica=False,
        loja_hora_id=None,
    )
    _db.session.add(u)
    _db.session.flush()
    return u


def _login(client, user):
    """Replica o pattern de tests/chat/test_routes_stream.py."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def _logout(client):
    with client.session_transaction() as sess:
        sess.clear()


@pytest.fixture
def db_session(app):
    """Rollback per-test (igual ao tests/chat/conftest.py)."""
    with app.app_context():
        yield _db.session
        _db.session.rollback()
        _db.session.remove()


def test_permissoes_matriz_admin_retorna_is_admin_true(app, client, db_session):
    u = _criar_usuario(perfil='administrador', email_suffix='admin')
    _login(client, u)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=hora')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is True
    assert data['user_id'] == u.id
    assert isinstance(data['permissoes'], dict)


def test_permissoes_matriz_vendedor_retorna_so_modulos_permitidos(app, client, db_session):
    u = _criar_usuario(perfil='vendedor', email_suffix='vend')
    p = HoraUserPermissao(
        user_id=u.id,
        modulo='vendas',
        pode_ver=True,
        pode_criar=True,
    )
    _db.session.add(p)
    _db.session.flush()
    _login(client, u)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=hora')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is False
    assert data['permissoes']['vendas']['ver'] is True
    assert data['permissoes']['vendas']['criar'] is True
    # Modulo sem entry/permissao deve estar com criar=False
    assert data['permissoes']['recebimentos']['criar'] is False


def test_permissoes_matriz_assai_admin(app, client, db_session):
    u = _criar_usuario(perfil='administrador', email_suffix='admin2')
    _login(client, u)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=motos_assai')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is True
    assert data['permissoes'] is None


def test_permissoes_matriz_modulo_invalido(app, client, db_session):
    u = _criar_usuario(perfil='administrador', email_suffix='adm3')
    _login(client, u)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=foo')
    assert r.status_code == 400


def test_permissoes_matriz_sem_login(app, client):
    """Sem login: @login_required deve retornar 302 (redirect login) ou 401.

    Como root conftest define LOGIN_DISABLED=True, sobrescrevemos por este
    teste para validar o decorator de fato.
    """
    original = app.config.get('LOGIN_DISABLED')
    app.config['LOGIN_DISABLED'] = False
    try:
        _logout(client)
        r = client.get('/api/onboarding/permissoes-matriz?modulo=hora', follow_redirects=False)
        assert r.status_code in (302, 401)
    finally:
        app.config['LOGIN_DISABLED'] = original
