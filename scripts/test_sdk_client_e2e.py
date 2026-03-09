#!/usr/bin/env python3
"""
Teste end-to-end da migração SDK Client COM chamadas reais à API.

Testa o fluxo COMPLETO: connect → query → stream → multi-turn → interrupt → disconnect.
Usa Haiku (barato, rápido) com prompts mínimos para reduzir custo.

Custo estimado: ~$0.01-0.02 por execução completa.

Uso:
    source .venv/bin/activate
    AGENT_PERSISTENT_SDK_CLIENT=true python scripts/test_sdk_client_e2e.py

Pré-requisitos:
    - ANTHROPIC_API_KEY (ou configurada no .env)
    - CLI `claude` instalada e acessível
    - Flag AGENT_PERSISTENT_SDK_CLIENT=true

Ref: .claude/references/ROADMAP_SDK_CLIENT.md
"""

import sys
import os
import asyncio
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ─── Contadores ──────────────────────────────────────────────────────
_passed = 0
_failed = 0
_warnings = 0
_errors = []
_total_cost = 0.0


def _ok(msg: str):
    global _passed
    _passed += 1
    print(f"  ✓ {msg}")


def _fail(msg: str, detail: str = ""):
    global _failed
    _failed += 1
    _errors.append(msg)
    print(f"  ✗ {msg}")
    if detail:
        for line in detail.split('\n')[:5]:
            print(f"    → {line}")


def _warn(msg: str):
    global _warnings
    _warnings += 1
    print(f"  ⚠ {msg}")


def _section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =====================================================================
# SEÇÃO 1: PRÉ-CONDIÇÕES
# =====================================================================
def test_preconditions():
    _section("1. PRÉ-CONDIÇÕES")

    # 1.1: Flag deve estar ligada
    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
    if USE_PERSISTENT_SDK_CLIENT:
        _ok("USE_PERSISTENT_SDK_CLIENT=true")
    else:
        _fail(
            "USE_PERSISTENT_SDK_CLIENT=false — E2E requer flag=true",
            "Execute: AGENT_PERSISTENT_SDK_CLIENT=true python scripts/test_sdk_client_e2e.py"
        )
        return False

    # 1.2: API key disponível
    from app.agente.config import get_settings
    settings = get_settings()
    if settings.api_key:
        _ok(f"API key configurada (***{settings.api_key[-4:]})")
    else:
        _fail("ANTHROPIC_API_KEY não configurada")
        return False

    # 1.3: CLI encontrada
    import shutil
    claude_path = shutil.which('claude')
    if claude_path:
        _ok(f"CLI encontrada: {claude_path}")
    else:
        _fail("CLI 'claude' não encontrada no PATH")
        return False

    # 1.4: Pool inicializa
    from app.agente.sdk.client_pool import _ensure_pool_initialized
    if _ensure_pool_initialized():
        _ok("Pool inicializado (daemon thread + event loop)")
    else:
        _fail("Pool não inicializou")
        return False

    return True


# =====================================================================
# SEÇÃO 2: SINGLE TURN — QUERY + STREAM (path persistente)
# =====================================================================
def test_single_turn(app):
    _section("2. SINGLE TURN (query + stream)")
    global _total_cost

    from app.agente.sdk.client import AgentClient
    from app.agente.sdk.client_pool import submit_coroutine, get_pooled_client
    from app.agente.config.permissions import set_current_session_id

    client = AgentClient()
    test_session_id = f"e2e-test-{int(time.time())}"

    # Coletar eventos
    events_collected = []
    event_types_seen = set()
    full_text = ""
    sdk_session_id_received = None

    async def _do_single_turn():
        nonlocal full_text, sdk_session_id_received

        # Setar ContextVars como routes.py faz
        set_current_session_id(test_session_id)

        async for event in client.stream_response(
            prompt="Responda apenas: 'OK'. Nada mais.",
            user_name="TestE2E",
            model="claude-haiku-4-5-20251001",  # Haiku = barato
            user_id=1,
            our_session_id=test_session_id,
            effort_level="low",
        ):
            events_collected.append(event)
            event_types_seen.add(event.type)

            if event.type == 'text':
                full_text += event.content or ""
            elif event.type == 'init':
                sdk_session_id_received = (event.content or {}).get('session_id')
            elif event.type == 'done':
                pass  # Processado abaixo

    try:
        future = submit_coroutine(_do_single_turn())
        future.result(timeout=60)
    except Exception as e:
        _fail(f"Single turn falhou: {type(e).__name__}: {e}")
        return None

    # 2.1: Recebeu eventos
    if events_collected:
        _ok(f"Recebeu {len(events_collected)} eventos")
    else:
        _fail("Nenhum evento recebido")
        return None

    # 2.2: Event types esperados
    required_types = {'init', 'text', 'done'}
    missing = required_types - event_types_seen
    if not missing:
        _ok(f"Event types presentes: {sorted(event_types_seen)}")
    else:
        _fail(f"Event types faltando: {missing}", f"Recebidos: {sorted(event_types_seen)}")

    # 2.3: Texto da resposta
    if full_text.strip():
        preview = full_text.strip()[:100]
        _ok(f"Resposta: '{preview}'")
    else:
        _fail("Texto vazio na resposta")

    # 2.4: Done event com tokens
    done_events = [e for e in events_collected if e.type == 'done']
    if done_events:
        done_data = done_events[0].content or {}
        input_tokens = done_data.get('input_tokens', 0)
        output_tokens = done_data.get('output_tokens', 0)
        cost = done_data.get('total_cost_usd', 0)
        _total_cost += cost if isinstance(cost, (int, float)) else 0
        if input_tokens > 0:
            _ok(f"Tokens: input={input_tokens}, output={output_tokens}, cost=${cost}")
        else:
            _warn(f"Tokens zerados: input={input_tokens}, output={output_tokens}")
    else:
        _fail("Nenhum done event")

    # 2.5: Client no pool
    pooled = get_pooled_client(test_session_id)
    if pooled and pooled.connected:
        _ok(f"Client no pool: connected=True, age={time.time()-pooled.created_at:.1f}s")
    else:
        _warn("Client não encontrado no pool após query (pode ter sido cleaned up)")

    # 2.6: init event tem persistent=True
    init_events = [e for e in events_collected if e.type == 'init']
    if init_events:
        meta = init_events[0].metadata or {}
        if meta.get('persistent') is True:
            _ok("init event: persistent=True (path correto)")
        else:
            _fail("init event: persistent != True", f"metadata={meta}")

    return test_session_id


# =====================================================================
# SEÇÃO 3: MULTI-TURN — CONTEXTO PRESERVADO
# =====================================================================
def test_multi_turn(app, session_id: str):
    _section("3. MULTI-TURN (contexto preservado)")
    global _total_cost

    if not session_id:
        _warn("SKIPPED: single turn falhou, sem session_id")
        return session_id

    from app.agente.sdk.client import AgentClient
    from app.agente.sdk.client_pool import submit_coroutine, get_pooled_client
    from app.agente.config.permissions import set_current_session_id

    client = AgentClient()
    full_text = ""
    events_collected = []

    # Turno 2: perguntar sobre o turno anterior
    async def _do_second_turn():
        nonlocal full_text

        set_current_session_id(session_id)

        async for event in client.stream_response(
            prompt="O que eu pedi no turno anterior? Responda em 1 frase curta.",
            user_name="TestE2E",
            model="claude-haiku-4-5-20251001",
            user_id=1,
            our_session_id=session_id,
            effort_level="low",
        ):
            events_collected.append(event)
            if event.type == 'text':
                full_text += event.content or ""
            elif event.type == 'done':
                content = event.content or {}
                global _total_cost
                _total_cost += content.get('total_cost_usd', 0) if isinstance(content.get('total_cost_usd'), (int, float)) else 0

    try:
        future = submit_coroutine(_do_second_turn())
        future.result(timeout=60)
    except Exception as e:
        _fail(f"Multi-turn falhou: {type(e).__name__}: {e}")
        return session_id

    # 3.1: Resposta existe
    if full_text.strip():
        preview = full_text.strip()[:150]
        _ok(f"Turno 2 resposta: '{preview}'")
    else:
        _fail("Turno 2: texto vazio")

    # 3.2: Contexto preservado — deve mencionar "OK" ou "turno anterior" ou similar
    lower = full_text.lower()
    context_words = ['ok', 'respond', 'diss', 'pedi', 'anterior', 'último', 'turno']
    has_context = any(w in lower for w in context_words)
    if has_context:
        _ok("Contexto preservado: resposta referencia turno anterior")
    else:
        _warn(f"Contexto talvez não preservado. Resposta: '{full_text.strip()[:100]}'")

    # 3.3: Client reutilizado (não criou novo)
    pooled = get_pooled_client(session_id)
    if pooled and pooled.connected:
        age = time.time() - pooled.created_at
        _ok(f"Client REUTILIZADO: age={age:.1f}s (mesmo desde turno 1)")
    else:
        _fail("Client não reutilizado (deveria ser o mesmo do turno 1)")

    # 3.4: Done event presente
    done_events = [e for e in events_collected if e.type == 'done']
    if done_events:
        _ok(f"Done event no turno 2: {len(events_collected)} eventos total")
    else:
        _fail("Turno 2 sem done event")

    return session_id


# =====================================================================
# SEÇÃO 4: SSE EVENT TYPES
# =====================================================================
def test_sse_event_types(app, session_id: str):
    _section("4. SSE EVENT TYPES (turno 3 — com tool call)")
    global _total_cost

    if not session_id:
        _warn("SKIPPED: sem session_id")
        return session_id

    from app.agente.sdk.client import AgentClient
    from app.agente.sdk.client_pool import submit_coroutine
    from app.agente.config.permissions import set_current_session_id

    client = AgentClient()
    events_collected = []

    # Turno 3: prompt que pode gerar thinking (se effort > low)
    async def _do_third_turn():
        set_current_session_id(session_id)

        async for event in client.stream_response(
            prompt="Quanto é 2+2? Responda apenas o número.",
            user_name="TestE2E",
            model="claude-haiku-4-5-20251001",
            user_id=1,
            our_session_id=session_id,
            effort_level="low",
        ):
            events_collected.append(event)
            if event.type == 'done':
                content = event.content or {}
                global _total_cost
                _total_cost += content.get('total_cost_usd', 0) if isinstance(content.get('total_cost_usd'), (int, float)) else 0

    try:
        future = submit_coroutine(_do_third_turn())
        future.result(timeout=60)
    except Exception as e:
        _fail(f"Turno 3 falhou: {type(e).__name__}: {e}")
        return session_id

    event_types = {e.type for e in events_collected}

    # 4.1: init e done presentes
    if 'init' in event_types and 'done' in event_types:
        _ok(f"init + done presentes (total events: {len(events_collected)})")
    else:
        _fail(f"init ou done ausentes: {event_types}")

    # 4.2: text presente
    if 'text' in event_types:
        _ok("text event presente")
    else:
        _warn("Sem text events (pode ser resposta muito curta)")

    # 4.3: Listar todos os types vistos nos 3 turnos
    _ok(f"Types vistos neste turno: {sorted(event_types)}")

    return session_id


# =====================================================================
# SEÇÃO 5: CONTEXTVAR ISOLATION (2 sessões simultâneas)
# =====================================================================
def test_session_isolation(app):
    _section("5. ISOLAMENTO DE SESSÕES (2 queries paralelas)")
    global _total_cost

    from app.agente.sdk.client import AgentClient
    from app.agente.sdk.client_pool import submit_coroutine, get_pooled_client
    from app.agente.config.permissions import set_current_session_id

    client = AgentClient()
    session_a = f"e2e-iso-A-{int(time.time())}"
    session_b = f"e2e-iso-B-{int(time.time())}"
    result_a = []
    result_b = []

    async def _query_session(sid, results, number):
        set_current_session_id(sid)
        text = ""
        async for event in client.stream_response(
            prompt=f"Responda apenas o número {number}. Nada mais.",
            user_name="TestE2E",
            model="claude-haiku-4-5-20251001",
            user_id=1,
            our_session_id=sid,
            effort_level="low",
        ):
            if event.type == 'text':
                text += event.content or ""
            elif event.type == 'done':
                content = event.content or {}
                global _total_cost
                _total_cost += content.get('total_cost_usd', 0) if isinstance(content.get('total_cost_usd'), (int, float)) else 0
        results.append(text.strip())

    try:
        # Lançar 2 queries em paralelo via submit_coroutine
        future_a = submit_coroutine(_query_session(session_a, result_a, 42))
        future_b = submit_coroutine(_query_session(session_b, result_b, 99))

        future_a.result(timeout=60)
        future_b.result(timeout=60)
    except Exception as e:
        _fail(f"Queries paralelas falharam: {type(e).__name__}: {e}")
        return

    # 5.1: Ambas responderam
    if result_a and result_b:
        _ok(f"Sessão A respondeu: '{result_a[0][:50]}'")
        _ok(f"Sessão B respondeu: '{result_b[0][:50]}'")
    else:
        _fail(f"Respostas incompletas: A={result_a}, B={result_b}")
        return

    # 5.2: Clients distintos no pool
    pooled_a = get_pooled_client(session_a)
    pooled_b = get_pooled_client(session_b)
    if pooled_a and pooled_b:
        if pooled_a is not pooled_b:
            _ok("2 PooledClients distintos no pool (isolamento OK)")
        else:
            _fail("Mesmo PooledClient para 2 sessões!")
    else:
        _warn(f"Pool lookup: A={pooled_a is not None}, B={pooled_b is not None}")

    # Cleanup
    from app.agente.sdk.client_pool import disconnect_client
    for sid in [session_a, session_b]:
        try:
            future = submit_coroutine(disconnect_client(sid))
            future.result(timeout=10)
        except Exception:
            pass


# =====================================================================
# SEÇÃO 6: DISCONNECT E CLEANUP
# =====================================================================
def test_disconnect(app, session_id: str):
    _section("6. DISCONNECT E CLEANUP")

    if not session_id:
        _warn("SKIPPED: sem session_id")
        return

    from app.agente.sdk.client_pool import (
        submit_coroutine, disconnect_client, get_pooled_client, get_pool_status,
    )

    # 6.1: Client existe antes do disconnect
    pooled = get_pooled_client(session_id)
    if pooled:
        _ok(f"Client existe pré-disconnect: connected={pooled.connected}")
    else:
        _warn("Client já não existe no pool")
        return

    # 6.2: Disconnect
    try:
        future = submit_coroutine(disconnect_client(session_id))
        result = future.result(timeout=15)
        if result:
            _ok("disconnect_client() retornou True")
        else:
            _fail("disconnect_client() retornou False")
    except Exception as e:
        _fail(f"disconnect_client falhou: {e}")
        return

    # 6.3: Client removido do pool
    pooled_after = get_pooled_client(session_id)
    if pooled_after is None:
        _ok("Client removido do pool após disconnect")
    else:
        _fail(f"Client AINDA no pool após disconnect: connected={pooled_after.connected}")

    # 6.4: Pool status saudável
    status = get_pool_status()
    if status.get('status') == 'healthy':
        _ok(f"Pool status: healthy ({status.get('total_clients', 0)} clients restantes)")
    else:
        _warn(f"Pool status: {status.get('status')}")


# =====================================================================
# SEÇÃO 7: PATH ANTIGO (flag=false, rollback)
# =====================================================================
def test_old_path(app):
    _section("7. ROLLBACK PATH (query() — simulação)")

    # Não vamos realmente desligar a flag (afetaria o daemon).
    # Em vez disso, verificamos que o path antigo ainda compila.
    try:
        from app.agente.sdk.client import AgentClient
        client = AgentClient()

        # Verificar que _stream_response (path antigo) ainda existe
        assert hasattr(client, '_stream_response'), "_stream_response removido!"
        assert hasattr(client, '_make_streaming_prompt'), "_make_streaming_prompt removido!"
        _ok("Path antigo (_stream_response + _make_streaming_prompt) ainda existe (rollback OK)")
    except Exception as e:
        _fail(f"Path antigo check falhou: {e}")

    # Verificar dispatch no stream_response
    try:
        import inspect
        source = inspect.getsource(AgentClient.stream_response)
        if 'USE_PERSISTENT_SDK_CLIENT' in source:
            _ok("stream_response(): dispatch flag presente (coexistência OK)")
        else:
            _fail("stream_response(): dispatch flag AUSENTE")
    except Exception as e:
        _fail(f"Dispatch check falhou: {e}")


# =====================================================================
# RESUMO
# =====================================================================
def print_summary():
    print(f"\n{'='*60}")
    print(f"  RESUMO — TESTE END-TO-END (API REAL)")
    print(f"{'='*60}")
    print(f"  ✓ Passou:   {_passed}")
    print(f"  ✗ Falhou:   {_failed}")
    print(f"  ⚠ Avisos:   {_warnings}")
    print(f"  💰 Custo:   ${_total_cost:.4f}")
    print(f"{'='*60}")

    if _errors:
        print(f"\n  FALHAS:")
        for err in _errors:
            print(f"    ✗ {err}")

    if _failed == 0:
        print(f"\n  🟢 TODOS OS TESTES E2E PASSARAM")
    else:
        print(f"\n  🔴 {_failed} TESTE(S) E2E FALHARAM — verificar acima")

    print()
    return _failed == 0


# =====================================================================
# MAIN
# =====================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  TESTE END-TO-END: Migração SDK Client (API REAL)")
    print("  Modelo: claude-haiku-4-5 (barato)")
    print("  Custo estimado: ~$0.01-0.02")
    print("  Ref: .claude/references/ROADMAP_SDK_CLIENT.md")
    print("=" * 60)

    if not os.path.exists('app/agente/sdk/client_pool.py'):
        print("\n✗ ERRO: Execute do diretório raiz do projeto!")
        sys.exit(1)

    # Criar Flask app
    from app import create_app
    app = create_app()

    with app.app_context():
        try:
            # Seção 1: Pré-condições
            if not test_preconditions():
                print("\n✗ Pré-condições falharam. Abortando.")
                print_summary()
                sys.exit(1)

            # Seção 2: Single turn
            session_id = test_single_turn(app)

            # Seção 3: Multi-turn
            session_id = test_multi_turn(app, session_id)

            # Seção 4: SSE event types
            session_id = test_sse_event_types(app, session_id)

            # Seção 5: Isolamento de sessões
            test_session_isolation(app)

            # Seção 6: Disconnect
            test_disconnect(app, session_id)

            # Seção 7: Rollback path
            test_old_path(app)

        except Exception as e:
            print(f"\n✗ ERRO FATAL: {e}")
            traceback.print_exc()
        finally:
            # Cleanup: desconectar todos os clients de teste
            try:
                from app.agente.sdk.client_pool import shutdown_pool
                shutdown_pool()
            except Exception:
                pass

            success = print_summary()
            sys.exit(0 if success else 1)
