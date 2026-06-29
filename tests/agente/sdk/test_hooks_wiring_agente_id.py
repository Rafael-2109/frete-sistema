"""MOTOR UNICO — ETAPA 2.4: wiring de agente_id em build_hooks -> 3 callers.

build_hooks(agente_id) propaga o PERFIL para os 3 pontos de injecao que JA
filtram por agente (M3 fatia 2), mas hoje recebem 'web' (hardcoded/default):
- UserPromptSubmit  -> _load_user_memories_for_context(agente_id=...)
- PreToolUse Skill   -> _build_skill_pretool_context -> get_skill_reminders_for_session(agente_id=...)
- PreToolUse enforce -> _load_enforce_directives(agente_id=...)

Default 'web' = byte-identico (web/Teams/WhatsApp).
"""
import pytest


def _get_hook(hooks_dict, event, fn_name):
    for matcher in hooks_dict.get(event, []):
        for fn in matcher.hooks:
            if fn.__name__ == fn_name:
                return fn
    raise RuntimeError(f'{fn_name} nao encontrado em {event}')


def _build(agente_id=None):
    from app.agente.sdk.hooks import build_hooks
    kwargs = dict(
        user_id=1, user_name='x', tool_failure_counts={},
        get_last_thinking=lambda: '', get_model_name=lambda: 'claude-opus-4-8',
        set_injected_ids=lambda i: None,
    )
    if agente_id is not None:
        kwargs['agente_id'] = agente_id
    return build_hooks(**kwargs)


# ---------------------------------------------------------------------------
# Caller 1 — UserPromptSubmit -> _load_user_memories_for_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_userpromptsubmit_propaga_agente_id_lojas(monkeypatch, app):
    captura = {}

    def fake_load(user_id, prompt=None, model_name=None, agente_id='web'):
        captura['agente_id'] = agente_id
        return (None, None, [])

    # mock no MODULO-FONTE antes de build_hooks (import local em build_hooks:256)
    monkeypatch.setattr('app.agente.sdk.memory_injection._load_user_memories_for_context', fake_load)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_AUTO_MEMORY_INJECTION', True)

    hook = _get_hook(_build('lojas'), 'UserPromptSubmit', '_user_prompt_submit_hook')
    with app.app_context():
        try:
            await hook({'prompt': 'oi', 'hook_event_name': 'UserPromptSubmit'}, None, {})
        except Exception:
            pass
    assert captura.get('agente_id') == 'lojas'


@pytest.mark.asyncio
async def test_userpromptsubmit_default_web(monkeypatch, app):
    captura = {}

    def fake_load(user_id, prompt=None, model_name=None, agente_id='web'):
        captura['agente_id'] = agente_id
        return (None, None, [])

    monkeypatch.setattr('app.agente.sdk.memory_injection._load_user_memories_for_context', fake_load)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_AUTO_MEMORY_INJECTION', True)

    hook = _get_hook(_build(), 'UserPromptSubmit', '_user_prompt_submit_hook')
    with app.app_context():
        try:
            await hook({'prompt': 'oi', 'hook_event_name': 'UserPromptSubmit'}, None, {})
        except Exception:
            pass
    assert captura.get('agente_id') == 'web'


# ---------------------------------------------------------------------------
# Caller 2 — _build_skill_pretool_context -> get_skill_reminders_for_session
# ---------------------------------------------------------------------------

def test_build_skill_pretool_context_propaga_agente_id(monkeypatch, app):
    captura = {}

    def fake_rem(user_id, session_id, agente_id='web'):
        captura['agente_id'] = agente_id
        return {}

    monkeypatch.setattr('app.agente.sdk.memory_injection.get_skill_reminders_for_session', fake_rem)
    monkeypatch.setattr('app.agente.config.feature_flags.AGENT_SKILL_EVAL', True)
    from app.agente.sdk.hooks import _build_skill_pretool_context
    with app.app_context():
        _build_skill_pretool_context(5, 'consultando-estoque-loja', agente_id='lojas')
    assert captura.get('agente_id') == 'lojas'


# ---------------------------------------------------------------------------
# Caller 3 — _enforce_mandatory_invariants -> _load_enforce_directives
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enforce_hook_propaga_agente_id_lojas(monkeypatch, app):
    captura = {}

    def fake_enf(user_id, agente_id='web'):
        captura['agente_id'] = agente_id
        return []

    monkeypatch.setattr('app.agente.sdk.hooks._load_enforce_directives', fake_enf)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_MANDATORY_HARD_ENFORCE', True)

    hook = _get_hook(_build('lojas'), 'PreToolUse', '_enforce_mandatory_invariants')
    with app.app_context():
        try:
            await hook({'tool_name': 'Bash', 'tool_input': {'command': 'x'},
                        'hook_event_name': 'PreToolUse'}, None, {})
        except Exception:
            pass
    assert captura.get('agente_id') == 'lojas'
