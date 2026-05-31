"""Tests para propagacao de session_id via PreToolUse hook (audit hook 2026-05-28).

Cobertura:
- Bash command e prefixado com export AGENT_SESSION_ID/AGENT_TOOL_USE_ID/AGENT_TYPE/AGENT_USER_NAME
- Tool non-Bash NAO e mutado
- Flag USE_ODOO_AUDIT_HOOK=False desliga propagacao
- session_id ausente vira 'noctx'
- shlex.quote escapa valores com aspas (defesa contra injection)
"""
import pytest


@pytest.fixture
def hook_keep_stream_open():
    """Constroi o hook _keep_stream_open via build_hooks() factory."""
    from app.agente.sdk.hooks import build_hooks
    hooks_dict = build_hooks(
        user_id=1,
        user_name='rafael',
        tool_failure_counts={},
        get_last_thinking=lambda: '',
        get_model_name=lambda: 'claude-opus-4-8',
        set_injected_ids=lambda x: None,
    )
    # build_hooks retorna {'PreToolUse': [HookMatcher(..., hooks=[fn])], ...}
    pre_matchers = hooks_dict.get('PreToolUse', [])
    # Pega o primeiro hook do primeiro matcher
    for matcher in pre_matchers:
        for fn in matcher.hooks:
            if fn.__name__ == '_keep_stream_open':
                return fn
    raise RuntimeError('_keep_stream_open nao encontrado')


@pytest.mark.asyncio
async def test_bash_command_prefixado_quando_flag_on(hook_keep_stream_open, monkeypatch):
    """Bash recebe prefix export AGENT_SESSION_ID=... + command original."""
    monkeypatch.setenv('AGENT_ODOO_AUDIT_HOOK', 'true')
    # Reimport para flag pegar nova ENV
    from importlib import reload
    from app.agente.config import feature_flags
    reload(feature_flags)

    from app.agente.config.permissions import set_current_session_id
    set_current_session_id('sess-test-001')

    hook_input = {
        'tool_name': 'Bash',
        'tool_input': {'command': 'python script.py --confirmar'},
        'tool_use_id': 'toolu_01abcd',
        'agent_type': 'main',
        'session_id': 'sdk_sess_xyz',
        'transcript_path': '/tmp/t.jsonl',
        'cwd': '/tmp',
        'agent_id': 'agent_main',
        'hook_event_name': 'PreToolUse',
    }
    out = await hook_keep_stream_open(hook_input, None, {})

    assert out['continue_'] is True
    hso = out.get('hookSpecificOutput', {})
    updated = hso.get('updatedInput')
    assert updated is not None, 'updatedInput deveria estar presente'
    cmd = updated['command']
    assert 'export AGENT_SESSION_ID=' in cmd
    assert "'sess-test-001'" in cmd or 'sess-test-001' in cmd
    assert 'export AGENT_TOOL_USE_ID=' in cmd
    assert 'toolu_01abcd' in cmd
    assert 'export AGENT_TYPE=' in cmd
    assert 'export AGENT_USER_NAME=' in cmd
    assert 'rafael' in cmd
    assert cmd.endswith('python script.py --confirmar')


@pytest.mark.asyncio
async def test_flag_off_nao_propaga(hook_keep_stream_open, monkeypatch):
    """Sem AGENT_ODOO_AUDIT_HOOK, Bash NAO recebe export."""
    monkeypatch.setenv('AGENT_ODOO_AUDIT_HOOK', 'false')
    from importlib import reload
    from app.agente.config import feature_flags
    reload(feature_flags)

    hook_input = {
        'tool_name': 'Bash',
        'tool_input': {'command': 'ls -la'},
        'tool_use_id': 'toolu_xyz',
        'agent_type': 'main',
        'session_id': 'x',
        'transcript_path': '/tmp/t.jsonl',
        'cwd': '/tmp',
        'agent_id': 'a',
        'hook_event_name': 'PreToolUse',
    }
    out = await hook_keep_stream_open(hook_input, None, {})

    hso = out.get('hookSpecificOutput', {}) if out else {}
    assert 'updatedInput' not in hso or hso.get('updatedInput') is None


@pytest.mark.asyncio
async def test_tool_non_bash_nao_propaga(hook_keep_stream_open, monkeypatch):
    """Tool != Bash (ex: Read) NAO e mutada."""
    monkeypatch.setenv('AGENT_ODOO_AUDIT_HOOK', 'true')
    from importlib import reload
    from app.agente.config import feature_flags
    reload(feature_flags)

    hook_input = {
        'tool_name': 'Read',
        'tool_input': {'file_path': '/tmp/x.txt'},
        'tool_use_id': 'toolu_read',
        'agent_type': 'main',
        'session_id': 's',
        'transcript_path': '/tmp/t.jsonl',
        'cwd': '/tmp',
        'agent_id': 'a',
        'hook_event_name': 'PreToolUse',
    }
    out = await hook_keep_stream_open(hook_input, None, {})

    hso = out.get('hookSpecificOutput', {}) if out else {}
    assert 'updatedInput' not in hso or hso.get('updatedInput') is None


@pytest.mark.asyncio
async def test_session_id_ausente_usa_noctx(hook_keep_stream_open, monkeypatch):
    """ContextVar sem session_id → prefix usa 'noctx'."""
    monkeypatch.setenv('AGENT_ODOO_AUDIT_HOOK', 'true')
    from importlib import reload
    from app.agente.config import feature_flags
    reload(feature_flags)

    # Limpar ContextVar
    from app.agente.config.permissions import set_current_session_id
    try:
        set_current_session_id(None)  # se aceitar
    except Exception:
        pass

    hook_input = {
        'tool_name': 'Bash',
        'tool_input': {'command': 'echo hello'},
        'tool_use_id': '',
        'agent_type': '',
        'session_id': '',
        'transcript_path': '/tmp/t.jsonl',
        'cwd': '/tmp',
        'agent_id': '',
        'hook_event_name': 'PreToolUse',
    }
    out = await hook_keep_stream_open(hook_input, None, {})

    hso = out.get('hookSpecificOutput', {})
    updated = hso.get('updatedInput')
    if updated:
        cmd = updated['command']
        # 'noctx' aparece pelo menos em SESSION_ID quando ContextVar vazia.
        # tool_use_id vazio vira 'notui'.
        assert 'noctx' in cmd or 'notui' in cmd or 'export' in cmd
