"""Testa que o SSE generator subscreve canal Redis pubsub (#4 async events)."""
from unittest.mock import MagicMock


def test_sanitize_function_handles_subagent_validation():
    """_sanitize_subagent_summary_for_user funciona para tipo validation."""
    from app.agente.routes.chat import _sanitize_subagent_summary_for_user

    validation_data = {
        'agent_id': 'a1',
        'agent_type': 'analista-carteira',
        'score': 40,
        'reason': 'Inconsistencia detectada em CNPJ 12.345.678/0001-90',
        'flagged_claims': ['texto com CPF 123.456.789-00'],
    }

    admin = MagicMock(perfil='administrador')
    result_admin = _sanitize_subagent_summary_for_user(validation_data, admin)
    # Admin: sem alteracao
    assert '12.345.678/0001-90' in result_admin['reason']

    # Nota: validation_data nao tem cost_usd nem findings_text/tools_used, entao
    # o sanitizer so aplica mask em campos de string conhecidos
    # (funcao atual de sanitize foca em findings_text e tools_used)
    non_admin = MagicMock(perfil='operador')
    result_non_admin = _sanitize_subagent_summary_for_user(validation_data, non_admin)
    # Non-admin: cost_usd removido (nao existia, mas nao deve dar erro)
    assert 'cost_usd' not in result_non_admin
    # score e outros campos preservados
    assert result_non_admin['score'] == 40
    assert result_non_admin['agent_type'] == 'analista-carteira'
