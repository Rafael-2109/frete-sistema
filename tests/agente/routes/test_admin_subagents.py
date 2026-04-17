"""Testes do endpoint admin de debug de subagentes (#1)."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def admin_user():
    user = MagicMock()
    user.is_authenticated = True
    user.perfil = 'administrador'
    user.id = 1
    return user


@pytest.fixture
def normal_user():
    user = MagicMock()
    user.is_authenticated = True
    user.perfil = 'vendedor'
    user.id = 2
    return user


def test_list_subagents_admin_returns_200(client, admin_user):
    """GET /api/admin/sessions/<id>/subagents retorna lista para admin."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=8234, cost_usd=0.012, num_turns=4,
        tools_used=[{'name': 'query_sql', 'args_summary': 'SELECT',
                     'result_summary': '24 rows', 'tool_use_id': 't1'}]
    )

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.get_session_subagents_summary',
               return_value=[summary]):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert len(data['subagents']) == 1
    assert data['subagents'][0]['agent_type'] == 'analista-carteira'
    assert data['subagents'][0]['cost_usd'] == 0.012  # admin ve custo


def test_list_subagents_non_admin_returns_403(client, normal_user):
    """Non-admin recebe 403."""
    with patch('flask_login.utils._get_user', return_value=normal_user):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 403


def test_get_subagent_detail_admin_returns_raw(client, admin_user):
    """GET detail retorna summary com PII raw (include_pii=True) para admin."""
    from app.agente.sdk.subagent_reader import SubagentSummary
    from datetime import datetime

    summary = SubagentSummary(
        agent_id='a1', agent_type='analista-carteira', status='done',
        started_at=datetime(2026, 4, 16), ended_at=datetime(2026, 4, 16),
        duration_ms=100,
        findings_text='Cliente 12.345.678/0001-90 tem 5 pedidos',
    )

    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.get_subagent_summary',
               return_value=summary) as mock_get:
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents/a1')

    assert resp.status_code == 200
    # admin chama com include_pii=True
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs.get('include_pii') is True


def test_flag_off_returns_404(client, admin_user):
    """Quando USE_SUBAGENT_DEBUG_ENDPOINT=false, rota retorna 404."""
    with patch('flask_login.utils._get_user', return_value=admin_user), \
         patch('app.agente.routes.admin_subagents.USE_SUBAGENT_DEBUG_ENDPOINT',
               False):
        resp = client.get('/agente/api/admin/sessions/sess-1/subagents')

    assert resp.status_code == 404
