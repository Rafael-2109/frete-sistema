"""Regressao do race de criacao concorrente em get_or_create_client.

Bug 2 (2026-06-06): 2 requests da MESMA sessao chegando dentro da janela do
`await client.connect()` criavam clients separados e o 2o DESCONECTAVA o 1o,
matando o stream do turno em andamento ("2a mensagem interrompe a 1a e nao
responde"). O fix serializa a criacao por sessao (_creation_locks).

Deterministico, sem API: mocka ClaudeSDKClient com um connect() lento.
"""
import asyncio

import pytest

from app.agente.sdk import client_pool as cp


class _FakeClient:
    connects = 0
    disconnects = 0

    def __init__(self, options):
        self.options = options

    async def connect(self):
        type(self).connects += 1
        await asyncio.sleep(0.2)  # janela onde a race acontecia

    async def disconnect(self):
        type(self).disconnects += 1


@pytest.fixture(autouse=True)
def _isolar_pool(monkeypatch):
    import claude_agent_sdk
    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", _FakeClient)
    # sticky session no-op (evita qualquer dependencia de Redis)
    monkeypatch.setattr(cp, "claim_ownership", lambda *a, **k: True, raising=False)
    _FakeClient.connects = 0
    _FakeClient.disconnects = 0
    cp._registry.clear()
    cp._creation_locks.clear()
    yield
    cp._registry.clear()
    cp._creation_locks.clear()


def _gather_two(session_id):
    async def run():
        return await asyncio.gather(
            cp.get_or_create_client(session_id, options=object(), user_id=1),
            cp.get_or_create_client(session_id, options=object(), user_id=1),
        )
    return asyncio.run(run())


def test_concorrente_mesma_sessao_reusa_um_client(monkeypatch):
    """Com o lock (default ON): mesmo client, 1 connect, 0 disconnect."""
    monkeypatch.setenv("AGENT_POOL_CREATION_LOCK", "true")
    a, b = _gather_two("sess-lock-on")
    assert a is b, "as duas requests deveriam reusar o MESMO PooledClient"
    assert _FakeClient.connects == 1, "connect() deveria rodar uma unica vez"
    assert _FakeClient.disconnects == 0, "nenhum client deveria ser desconectado"
    assert len(cp._registry) == 1


def test_killswitch_off_restaura_comportamento_legado(monkeypatch):
    """Com o kill-switch OFF: comportamento antigo (race) — prova o rollback."""
    monkeypatch.setenv("AGENT_POOL_CREATION_LOCK", "false")
    _gather_two("sess-lock-off")
    # Legado: ambos conectam e o 2o substitui/desconecta o 1o.
    assert _FakeClient.connects == 2
    assert _FakeClient.disconnects == 1


def test_sessoes_distintas_nao_compartilham(monkeypatch):
    """Sessoes diferentes criam clients diferentes (sem serializacao cruzada)."""
    monkeypatch.setenv("AGENT_POOL_CREATION_LOCK", "true")

    async def run():
        a = await cp.get_or_create_client("sA", options=object(), user_id=1)
        b = await cp.get_or_create_client("sB", options=object(), user_id=1)
        return a, b

    a, b = asyncio.run(run())
    assert a is not b
    assert _FakeClient.connects == 2
    assert len(cp._registry) == 2
