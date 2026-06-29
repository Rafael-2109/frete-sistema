"""
F1.3: handlers de erro SDK especializados no fork (AgentLojasClient).

Sem eles, ProcessError/CLINotFoundError/CLIConnectionError/CLIJSONDecodeError
caem no `except Exception` generico -> traceback bruto E o stream NAO emite
`done` -> o frontend fica preso esperando o evento de fim. O fix emite `error`
(mensagem amigavel + error_type) + `done` com `error_recovery=True` (destrava o
frontend), espelhando o agente web (client.py:2473-2530).
"""
import pytest

from claude_agent_sdk import ProcessError, CLINotFoundError

from app.agente_lojas.sdk import client as lojas_client_mod


class _RaisingClient:
    """Fake ClaudeSDKClient que lanca `exc` ao entrar no contexto async."""

    def __init__(self, exc):
        self._exc = exc

    def __call__(self, options=None):
        return self

    async def __aenter__(self):
        raise self._exc

    async def __aexit__(self, *a):
        return False


async def _coletar_eventos(monkeypatch, exc):
    # Pula o PostgresSessionStore (sem DB no teste unitario).
    monkeypatch.setattr(lojas_client_mod, '_LOJAS_SESSION_STORE_ENABLED', False)
    monkeypatch.setattr(lojas_client_mod, 'ClaudeSDKClient', _RaisingClient(exc))
    client = lojas_client_mod.get_lojas_client()
    eventos = []
    async for ev in client.stream_response(
        user_message='oi', user_id=1, user_name='T',
        perfil='administrador', loja_hora_id=None,
    ):
        eventos.append(ev)
    return eventos


@pytest.mark.asyncio
async def test_process_error_emite_error_e_done_recovery(monkeypatch):
    eventos = await _coletar_eventos(monkeypatch, ProcessError('boom', exit_code=1))
    tipos = [e['type'] for e in eventos]
    assert 'error' in tipos
    assert 'done' in tipos, "stream sem 'done' deixa o frontend preso"
    done = next(e for e in eventos if e['type'] == 'done')
    assert done['metadata'].get('error_recovery') is True
    err = next(e for e in eventos if e['type'] == 'error')
    assert err['metadata'].get('error_type') == 'process_error'
    assert err['metadata'].get('exit_code') == 1


@pytest.mark.asyncio
async def test_cli_not_found_emite_error_e_done_recovery(monkeypatch):
    eventos = await _coletar_eventos(monkeypatch, CLINotFoundError('no cli'))
    tipos = [e['type'] for e in eventos]
    assert 'error' in tipos
    assert 'done' in tipos, "stream sem 'done' deixa o frontend preso"
    done = next(e for e in eventos if e['type'] == 'done')
    assert done['metadata'].get('error_recovery') is True
    err = next(e for e in eventos if e['type'] == 'error')
    assert err['metadata'].get('error_type') == 'cli_not_found'
