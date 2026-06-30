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


# ---------------------------------------------------------------------------
# E3.8a (parte 2) — suprimir contexto Nacom RESIDUAL no UserPromptSubmit p/ 'lojas':
# sql_admin_context + pessoal_grant injetavam instrucoes do dominio Nacom
# (mcp__sql/pessoal_*, tools que NEM existem para o perfil lojas) mesmo para um
# admin operando a loja. Nao vazam DADOS (mcp__sql bloqueado), mas confundem o
# operador e instruem tools inexistentes. user_id=1 e admin (USUARIOS_SQL_ADMIN).
# ---------------------------------------------------------------------------

def _mock_ctx(monkeypatch):
    def fake_load(user_id, prompt=None, model_name=None, agente_id='web'):
        return (None, None, [])
    monkeypatch.setattr('app.agente.sdk.memory_injection._load_user_memories_for_context', fake_load)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_AUTO_MEMORY_INJECTION', True)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_PROMPT_CACHE_OPTIMIZATION', True)
    monkeypatch.setattr('app.agente.config.feature_flags.USE_CUSTOM_SYSTEM_PROMPT', True)


async def _run_ups(agente_id, app):
    hook = _get_hook(_build(agente_id), 'UserPromptSubmit', '_user_prompt_submit_hook')
    with app.app_context():
        try:
            out = await hook({'prompt': 'oi', 'hook_event_name': 'UserPromptSubmit'}, None, {})
        except Exception:
            out = None
    return str(out)


@pytest.mark.asyncio
async def test_ups_lojas_admin_nao_injeta_sql_admin_context(monkeypatch, app):
    _mock_ctx(monkeypatch)
    blob = await _run_ups('lojas', app)
    assert 'MODO SQL ADMIN' not in blob
    assert 'sql_admin_context' not in blob


@pytest.mark.asyncio
async def test_ups_web_admin_mantem_sql_admin_context(monkeypatch, app):
    _mock_ctx(monkeypatch)
    blob = await _run_ups(None, app)  # web (byte-identico)
    assert 'MODO SQL ADMIN' in blob


@pytest.mark.asyncio
async def test_ups_lojas_admin_nao_injeta_pessoal_grant(monkeypatch, app):
    _mock_ctx(monkeypatch)
    blob = await _run_ups('lojas', app)
    assert 'pessoal_access' not in blob


@pytest.mark.asyncio
async def test_ups_web_admin_mantem_pessoal_grant(monkeypatch, app):
    _mock_ctx(monkeypatch)
    blob = await _run_ups(None, app)  # web (byte-identico)
    assert 'pessoal_access' in blob


# ---------------------------------------------------------------------------
# PreCompact: nao instruir mcp__memory (tool bloqueada p/ lojas) nem vocabulario
# Nacom (VCD/VFB/separacao) numa sessao de loja que atinja o limite de contexto.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pre_compact_lojas_nao_injeta_template_nacom(app):
    hook = _get_hook(_build('lojas'), 'PreCompact', '_pre_compact_hook')
    with app.app_context():
        out = await hook({'session_id': 'x', 'hook_event_name': 'PreCompact'}, None, {})
    blob = str(out)
    assert 'mcp__memory__save_memory' not in blob  # tool bloqueada p/ lojas
    assert 'VCD' not in blob  # vocabulario Nacom


@pytest.mark.asyncio
async def test_pre_compact_web_mantem_template(app):
    hook = _get_hook(_build(), 'PreCompact', '_pre_compact_hook')
    with app.app_context():
        out = await hook({'session_id': 'x', 'hook_event_name': 'PreCompact'}, None, {})
    assert 'mcp__memory__save_memory' in str(out)  # web inalterado
