"""Testa rota user-facing para lazy-fetch de detalhes do subagent."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def admin_user():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'administrador'
    u.id = 1
    return u


@pytest.fixture
def normal_user():
    u = MagicMock()
    u.is_authenticated = True
    u.perfil = 'vendedor'
    u.id = 42
    return u


def test_user_fetches_own_subagent_summary_sanitized(client, normal_user):
    """User le seu proprio subagent — PII mascarada, sem cost."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100, cost_usd=0.012,
        findings_text='CNPJ 12.345.678/0001-90',
    )
    sess_mock = MagicMock(user_id=normal_user.id)

    with patch('flask_login.utils._get_user', return_value=normal_user), \
         patch('app.agente.routes.subagents._get_session',
               return_value=sess_mock), \
         patch('app.agente.routes.subagents.get_subagent_summary',
               return_value=summary):
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'cost_usd' not in data['subagent']
    assert '12.345.678/0001-90' not in data['subagent']['findings_text']


def test_user_cannot_read_other_users_session_returns_403(client, normal_user):
    """Sessao de outro usuario retorna 403."""
    sess_mock = MagicMock(user_id=999)

    with patch('flask_login.utils._get_user', return_value=normal_user), \
         patch('app.agente.routes.subagents._get_session',
               return_value=sess_mock):
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 403


def test_admin_reads_any_session(client, admin_user):
    """Admin le sessao de qualquer usuario + ve cost raw."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='x', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100, cost_usd=0.5,
        findings_text='CNPJ 12.345.678/0001-90',
    )
    sess_mock = MagicMock(user_id=999)

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.subagents._get_session',
               return_value=sess_mock), \
         patch('app.agente.routes.subagents.get_subagent_summary',
               return_value=summary):
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['subagent']['cost_usd'] == 0.5
    assert '12.345.678/0001-90' in data['subagent']['findings_text']


def test_flag_off_returns_404(client, admin_user):
    """USE_SUBAGENT_UI=false → 404."""
    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.subagents.USE_SUBAGENT_UI', False):
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 404


def test_session_not_found_returns_404(client, normal_user):
    """Sessao inexistente → 404."""
    with patch('flask_login.utils._get_user', return_value=normal_user), \
         patch('app.agente.routes.subagents._get_session',
               return_value=None):
        resp = client.get('/agente/api/sessions/s1/subagents/a1/summary')

    assert resp.status_code == 404
