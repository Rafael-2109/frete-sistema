"""
CUTOVER E3.9 — isolamento ponta a ponta (fio condutor da rota -> perfil 'lojas').

O isolamento POR PERFIL ja e' provado exaustivamente:
  - skills allow-list / agents={orientador-loja} / briefing vazio
        -> tests/agente/test_client_por_perfil.py (E1.2)
  - <loja_context> injetado + hints SQL/Bash Nacom suprimidos p/ 'lojas'
        -> tests/agente/sdk/test_loja_context_perfil.py (E3.8a)
  - memoria gravada/lida por agente='lojas'
        -> tests/agente/sdk/test_memory_isolation_por_agente.py (F2/E2.6)

Estes testes fecham o ELO QUE FALTAVA: provam que a ROTA do agente lojas (via
`_drain_via_motor`) e' servida pelo perfil 'lojas' — NUNCA 'web' — de modo que o
operador de loja herda TODO o isolamento acima e ve ZERO conteudo Nacom.
"""
import asyncio
import queue

import app.agente_lojas.routes.chat as chat_mod
from app.agente.config.permissions import get_current_agent_id, get_loja_scope
from app.agente_lojas.config.settings import AGENTE_ID


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_cutover_serve_perfil_lojas_nunca_web(monkeypatch):
    captured = {}

    class _Fake:
        async def stream_response(self, **kwargs):
            captured['agente_runtime'] = get_current_agent_id()
            captured['loja_scope_runtime'] = get_loja_scope()
            for _ in ():  # async generator vazio
                yield

    def _fake_get_client(agente_id='web'):
        captured['get_client_arg'] = agente_id
        return _Fake()

    monkeypatch.setattr('app.agente.sdk.client.get_client', _fake_get_client)

    _run(chat_mod._drain_via_motor(
        user_message='como esta minha loja?', user_id=42, user_name='Operador',
        perfil='vendedor', loja_hora_id=3, sdk_session_id=None,
        our_session_id='e2e-iso-1', event_queue=queue.Queue(), state={},
    ))

    # A rota usa o perfil isolado 'lojas' (nao 'web')...
    assert captured['get_client_arg'] == AGENTE_ID == 'lojas'
    # ...e durante o stream o ContextVar de agente e o escopo de loja estao setados
    assert captured['agente_runtime'] == 'lojas'
    assert captured['loja_scope_runtime'] == ('vendedor', 3)


def test_perfil_servido_pelo_cutover_tem_briefing_nacom_vazio():
    # Guard ancorado no cutover: o client que a rota usa (get_client(AGENTE_ID))
    # NAO injeta o briefing institucional Nacom (isolamento HORA). Reforca
    # test_client_por_perfil.py amarrando ao AGENTE_ID da rota lojas.
    from app.agente.sdk.client import get_client
    c = get_client(AGENTE_ID)
    assert c.agente_id == 'lojas'
    assert c.settings.empresa_briefing_path == ''
    assert c.empresa_briefing == ''


def test_cutover_admin_loja_scope_sem_loja_especifica(monkeypatch):
    # Admin (pode_ver_todas): loja_hora_id=None. O escopo ainda e' setado como
    # ('administrador', None) -> o hook E3.8a injeta <loja_context> de admin.
    captured = {}

    class _Fake:
        async def stream_response(self, **kwargs):
            captured['loja_scope_runtime'] = get_loja_scope()
            for _ in ():
                yield

    monkeypatch.setattr('app.agente.sdk.client.get_client', lambda agente_id='web': _Fake())

    _run(chat_mod._drain_via_motor(
        user_message='visao geral', user_id=1, user_name='Rafael',
        perfil='administrador', loja_hora_id=None, sdk_session_id=None,
        our_session_id='e2e-iso-admin', event_queue=queue.Queue(), state={},
    ))
    assert captured['loja_scope_runtime'] == ('administrador', None)
    # cleanup do finally
    assert get_current_agent_id() == 'web'
    assert get_loja_scope() is None
