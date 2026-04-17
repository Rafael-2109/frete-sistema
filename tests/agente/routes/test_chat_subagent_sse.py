"""Testa SSE passthrough de subagent_summary com sanitizacao por perfil."""
from unittest.mock import MagicMock


def test_process_stream_event_admin_sees_cost():
    """Admin recebe cost_usd no payload."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    summary = {
        'agent_type': 'analista-carteira',
        'cost_usd': 0.012,
        'findings_text': 'CNPJ 12.345.678/0001-90 tem 5 pedidos',
        'tools_used': [{'name': 'q', 'args_summary': 'SELECT',
                         'result_summary': '', 'tool_use_id': 't'}],
    }

    admin = MagicMock(perfil='administrador')
    result = _sanitize_subagent_summary_for_user(summary, admin)

    assert result['cost_usd'] == 0.012
    assert '12.345.678/0001-90' in result['findings_text']  # admin ve raw


def test_process_stream_event_user_sanitized():
    """User nao-admin: sem cost_usd + PII mascarada."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    summary = {
        'agent_type': 'analista-carteira',
        'cost_usd': 0.012,
        'findings_text': 'CNPJ 12.345.678/0001-90 tem 5 pedidos',
        'tools_used': [{'name': 'q', 'args_summary': '12.345.678/0001-90',
                         'result_summary': '', 'tool_use_id': 't'}],
    }

    user = MagicMock(perfil='vendedor')
    result = _sanitize_subagent_summary_for_user(summary, user)

    assert 'cost_usd' not in result
    assert '12.345.678/0001-90' not in result['findings_text']
    assert '0001-90' in result['findings_text']  # preserva filial
    assert '12.345.678/0001-90' not in result['tools_used'][0]['args_summary']


def test_non_admin_without_perfil_treated_as_user():
    """User sem atributo perfil → tratado como non-admin (defensive)."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    summary = {'agent_type': 'x', 'cost_usd': 0.01, 'findings_text': '',
               'tools_used': []}
    user_no_perfil = MagicMock(spec=[])  # sem perfil attribute
    result = _sanitize_subagent_summary_for_user(summary, user_no_perfil)

    assert 'cost_usd' not in result
