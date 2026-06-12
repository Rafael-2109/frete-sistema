"""P1 — AskUserQuestion no Teams via espera ASSINCRONA (nao bloqueia o pool).

Root cause secundario: o path Teams de `can_use_tool` (permissions.py) esperava
a resposta do Adaptive Card com `wait_for_answer` SINCRONO, que BLOQUEIA o event
loop do pool persistente por ate TEAMS_ASK_USER_TIMEOUT. Com o timeout subindo
para 600s, isso congelaria TODAS as outras conversas do pool durante 10 min.

Fix: usar `async_wait_for_answer` quando ha event loop rodando (espelha o path
web, ja em producao), suspendendo a coroutine em vez de bloquear a thread.

Teste determinístico (sem timing fragil): a resposta é submetida por uma
COROUTINE concorrente (nao uma thread). Ela só roda se o event loop estiver
LIVRE durante a espera:
  - async (fix): a espera cede o loop -> a coroutine roda -> submete -> Allow.
  - sync (bug): a espera bloqueia o loop -> a coroutine nunca roda -> timeout -> Deny.
"""
import asyncio

import pytest

from app.agente.config import permissions
from app.agente.config.permissions import can_use_tool, set_current_session_id


@pytest.fixture(autouse=True)
def _clean_registry():
    from app.agente.sdk.pending_questions import _lock, _pending
    with _lock:
        _pending.clear()
    yield
    with _lock:
        _pending.clear()


@pytest.mark.asyncio
async def test_askuser_teams_usa_espera_async_nao_bloqueia_loop(monkeypatch):
    sid = 'sess-teams-async-1'
    set_current_session_id(sid)

    # Forca o branch Teams: sem event_queue (web), com teams_task_id.
    monkeypatch.setattr(permissions, 'get_event_queue', lambda s: None)
    monkeypatch.setattr(permissions, 'get_teams_task_id', lambda s: 'task-test-1')
    # Pula o UPDATE da TeamsTask no banco (nao precisamos de DB neste teste).
    monkeypatch.setattr(permissions, '_execute_with_context', lambda fn: None)
    # Timeout curto: se a espera bloquear (sync), o teste falha rapido por Deny.
    import app.agente.config.feature_flags as ff
    monkeypatch.setattr(ff, 'TEAMS_ASK_USER_TIMEOUT', 1, raising=False)
    with permissions._context_lock:
        permissions._teams_ask_attempts.pop(sid, None)

    async def responde_pelo_loop():
        # Só executa se o event loop estiver LIVRE durante a espera do AskUser.
        from app.agente.sdk.pending_questions import submit_answer
        submit_answer(sid, {'q?': 'Opcao A'})

    # Agendada ANTES da espera; register_question (sincrono) ja rodou quando ela executa.
    asyncio.create_task(responde_pelo_loop())

    result = await can_use_tool('AskUserQuestion', {'questions': [{'question': 'q?'}]})

    # async: o loop cedeu -> coroutine respondeu -> Allow com as respostas.
    assert getattr(result, 'updated_input', None) is not None, (
        f"esperava PermissionResultAllow, veio {type(result).__name__} "
        f"(espera SINCRONA bloqueou o loop -> coroutine nao rodou -> timeout)"
    )
    assert result.updated_input.get('answers') == {'q?': 'Opcao A'}
