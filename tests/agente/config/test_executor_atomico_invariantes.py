# tests/agente/config/test_executor_atomico_invariantes.py
import asyncio
import os
from unittest import mock
from app.agente.config import permissions as perm


def _deny_check(tool_name, tool_input):
    # asyncio.run (NAO get_event_loop().run_until_complete — quebra com "loop
    # already running" sob pytest-asyncio). Precedente: test_permissions_odoo_tax_gate.py.
    return asyncio.run(perm.can_use_tool(tool_name, tool_input, None))

def test_executor_nao_bypassa_gate_r11_action_update_taxes(app):
    with app.app_context():
        perm.set_current_session_id('exec-1')
        with mock.patch('app.agente.config.feature_flags.USE_ODOO_TAX_GATE', True):
            res = _deny_check('Bash', {
                'command': "python -c \"models.execute_kw(db,uid,pw,'sale.order',"
                           "'action_update_taxes',[[123]])\""})
        assert res.__class__.__name__ == 'PermissionResultDeny'

def test_executor_definicao_carrega_com_tools_apertadas():
    from app.agente.config.agent_loader import load_agent_definitions
    defs = load_agent_definitions(os.path.join(os.getcwd(), '.claude', 'agents'))
    ex = defs.get('executor-recebimento-nfpo')
    assert ex is not None, 'executor nao carregou'
    # AgentDefinition (claude_agent_sdk) tem campo `tools` (list) — verificado.
    # Apertada: so' Bash/Grep/Read, sem Write/Edit.
    assert ex.tools is not None
    assert 'Write' not in ex.tools and 'Edit' not in ex.tools
    assert set(ex.tools) <= {'Bash', 'Grep', 'Read'}
