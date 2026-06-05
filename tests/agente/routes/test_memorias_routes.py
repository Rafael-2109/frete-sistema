"""Smoke HTTP da tela de gestao de memorias: auth (admin/non-admin) + render + contrato JSON.

Usa o `client` do conftest (nao redefine fixture `app`). current_user via patch do _get_user.
"""
from unittest.mock import MagicMock, patch


def _admin():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'administrador'
    u.id = 1
    u.nome = 'Admin Teste'
    u.email = 'admin@test.com'
    return u


def _normal():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'vendedor'
    u.id = 2
    u.nome = 'Vendedor'
    u.email = 'v@test.com'
    return u


def test_api_admin_memories_admin_200(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/agente/api/admin/memories')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    assert 'memories' in d
    assert 'stats' in d
    assert {'total', 'conflicts', 'hard_rules', 'cold'} <= set(d['stats'].keys())


def test_api_admin_memories_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.get('/agente/api/admin/memories')
    assert resp.status_code == 403


def test_api_admin_memories_conflicts_only_filtro(client):
    """conflicts_only=1 nao quebra e retorna lista (vazia ou so conflitos)."""
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/agente/api/admin/memories?conflicts_only=1')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    assert all(m['has_potential_conflict'] for m in d['memories'])


def test_resolve_conflict_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.put('/agente/api/memories/999999/resolve-conflict')
    assert resp.status_code == 403


def test_resolve_conflict_404_inexistente(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.put('/agente/api/memories/999999999/resolve-conflict')
    assert resp.status_code == 404
