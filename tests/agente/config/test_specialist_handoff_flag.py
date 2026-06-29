from unittest.mock import patch
import app.agente.config.feature_flags as ff


def _resolve(env, is_admin=False):
    with patch.dict('os.environ', env, clear=False):
        return ff.resolve_specialist_handoff_mode(is_admin=is_admin)


def test_default_off():
    # clear=True garante env limpo (CI pode ter AGENT_SPECIALIST_HANDOFF setado).
    with patch.dict('os.environ', {}, clear=True):
        assert ff.resolve_specialist_handoff_mode() == 'off'

def test_shadow_e_on_literais():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'shadow'}) == 'shadow'
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'on'}) == 'on'

def test_valor_invalido_cai_para_off():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'banana'}) == 'off'

def test_admin_e_on_para_admin_shadow_para_demais():
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'admin'}, is_admin=True) == 'on'
    assert _resolve({'AGENT_SPECIALIST_HANDOFF': 'admin'}, is_admin=False) == 'shadow'
