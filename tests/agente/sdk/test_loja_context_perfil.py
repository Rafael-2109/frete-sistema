"""MOTOR UNICO — ETAPA 3.8a: infra do motor web p/ servir o perfil 'lojas'.

- UserPromptSubmit injeta <loja_context> quando agente_id='lojas' (lê o
  ContextVar _current_loja_scope setado pela rota); 'web' nunca injeta.
- PreToolUse (_keep_stream_open) SUPRIME os hints SQL/Bash Nacom
  (carteira_principal etc.) quando agente_id='lojas' — não vaza dominio Nacom
  ao operador de loja. 'web' mantem os hints.

Tudo INERTE em producao ate a rota /agente-lojas migrar p/ o motor (so dispara
com agente_id='lojas').
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
        user_id=1, user_name='operador', tool_failure_counts={},
        get_last_thinking=lambda: '', get_model_name=lambda: 'claude-opus-4-8',
        set_injected_ids=lambda i: None,
    )
    if agente_id is not None:
        kwargs['agente_id'] = agente_id
    return build_hooks(**kwargs)


# ---------------------------------------------------------------------------
# <loja_context> no UserPromptSubmit (perfil 'lojas')
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_userpromptsubmit_lojas_injeta_loja_context(monkeypatch, app):
    def fake_load(user_id, prompt=None, model_name=None, agente_id='web'):
        return (None, None, [])
    monkeypatch.setattr('app.agente.sdk.memory_injection._load_user_memories_for_context', fake_load)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_AUTO_MEMORY_INJECTION', True)

    from app.agente.config.permissions import set_loja_scope, clear_loja_scope
    set_loja_scope('vendedor', 3)
    try:
        hook = _get_hook(_build('lojas'), 'UserPromptSubmit', '_user_prompt_submit_hook')
        with app.app_context():
            try:
                out = await hook({'prompt': 'minha loja', 'hook_event_name': 'UserPromptSubmit'}, None, {})
            except Exception:
                out = None
    finally:
        clear_loja_scope()
    blob = str(out)
    assert '<loja_context>' in blob
    assert 'loja_ids_permitidas: [3]' in blob


@pytest.mark.asyncio
async def test_userpromptsubmit_web_nao_injeta_loja_context(monkeypatch, app):
    def fake_load(user_id, prompt=None, model_name=None, agente_id='web'):
        return ("MEMORIA_WEB", None, [])
    monkeypatch.setattr('app.agente.sdk.memory_injection._load_user_memories_for_context', fake_load)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_AUTO_MEMORY_INJECTION', True)

    hook = _get_hook(_build(), 'UserPromptSubmit', '_user_prompt_submit_hook')
    with app.app_context():
        try:
            out = await hook({'prompt': 'oi', 'hook_event_name': 'UserPromptSubmit'}, None, {})
        except Exception:
            out = None
    assert '<loja_context>' not in str(out)


# ---------------------------------------------------------------------------
# Supressão de hints Nacom no PreToolUse (perfil 'lojas')
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_keep_stream_open_lojas_suprime_hint_sql_nacom(app):
    hook = _get_hook(_build('lojas'), 'PreToolUse', '_keep_stream_open')
    with app.app_context():
        out = await hook(
            {'tool_name': 'mcp__sql__consultar_sql', 'tool_input': {},
             'hook_event_name': 'PreToolUse'}, None, {})
    assert 'carteira_principal' not in str(out)


@pytest.mark.asyncio
async def test_keep_stream_open_web_mantem_hint_sql_nacom(app):
    hook = _get_hook(_build(), 'PreToolUse', '_keep_stream_open')
    with app.app_context():
        out = await hook(
            {'tool_name': 'mcp__sql__consultar_sql', 'tool_input': {},
             'hook_event_name': 'PreToolUse'}, None, {})
    assert 'carteira_principal' in str(out)
