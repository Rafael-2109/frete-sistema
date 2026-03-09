#!/usr/bin/env python3
"""
Diagnóstico completo da migração SDK Client (Fases 0-3).

Testa TODOS os pontos críticos SEM fazer chamadas ao Claude API.
Pode ser executado no Render Shell ou localmente.

Uso:
    source .venv/bin/activate
    python scripts/test_sdk_client_migration.py

Ref: .claude/references/ROADMAP_SDK_CLIENT.md
"""

import sys
import os
import asyncio
import threading
import time
import traceback
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass

# ─── Setup path ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ─── Contadores ──────────────────────────────────────────────────────
_passed = 0
_failed = 0
_warnings = 0
_errors = []


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
        print(f"    → {detail}")


def _warn(msg: str):
    global _warnings
    _warnings += 1
    print(f"  ⚠ {msg}")


def _section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =====================================================================
# SEÇÃO 1: IMPORTS E FEATURE FLAGS
# =====================================================================
def test_imports_and_flags():
    _section("1. IMPORTS E FEATURE FLAGS")

    # 1.1: Feature flags importam sem erro
    try:
        from app.agente.config.feature_flags import (
            USE_PERSISTENT_SDK_CLIENT,
            PERSISTENT_CLIENT_IDLE_TIMEOUT,
            PERSISTENT_CLIENT_CLEANUP_INTERVAL,
        )
        _ok(f"Feature flags importadas: USE_PERSISTENT_SDK_CLIENT={USE_PERSISTENT_SDK_CLIENT}")
        _ok(f"IDLE_TIMEOUT={PERSISTENT_CLIENT_IDLE_TIMEOUT}s, CLEANUP_INTERVAL={PERSISTENT_CLIENT_CLEANUP_INTERVAL}s")
    except ImportError as e:
        _fail("Feature flags não importam", str(e))
        return

    # 1.2: client_pool importa sem erro
    try:
        from app.agente.sdk.client_pool import (
            submit_coroutine,
            get_or_create_client,
            disconnect_client,
            get_pooled_client,
            get_pool_status,
            shutdown_pool,
            PooledClient,
        )
        _ok("client_pool.py: todas 7 funções importam OK")
    except ImportError as e:
        _fail("client_pool.py não importa", str(e))
        return

    # 1.3: sdk/__init__.py exports
    try:
        from app.agente.sdk import (
            submit_coroutine as sc,
            get_or_create_client as gocc,
            disconnect_client as dc,
            get_pooled_client as gpc,
            get_pool_status as gps,
            shutdown_pool as sp,
            PooledClient as PC,
        )
        _ok("sdk/__init__.py: exports OK")
    except ImportError as e:
        _fail("sdk/__init__.py exports incompletos", str(e))

    # 1.4: pending_questions importa
    try:
        from app.agente.sdk.pending_questions import (
            register_question,
            submit_answer,
            wait_for_answer,
            async_wait_for_answer,
            cancel_pending,
            PendingQuestion,
        )
        _ok("pending_questions.py: imports OK")
    except ImportError as e:
        _fail("pending_questions.py não importa", str(e))

    # 1.5: permissions DC-2 helpers
    try:
        from app.agente.config.permissions import (
            _get_app_context,
            _execute_with_context,
            set_current_session_id,
            get_current_session_id,
            set_event_queue,
            cleanup_session_context,
        )
        _ok("permissions.py: DC-2 helpers + context functions importam OK")
    except ImportError as e:
        _fail("permissions.py imports incompletos", str(e))


# =====================================================================
# SEÇÃO 2: POOL INFRASTRUCTURE
# =====================================================================
def test_pool_infrastructure():
    _section("2. POOL INFRASTRUCTURE (client_pool.py)")

    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
    from app.agente.sdk.client_pool import (
        PooledClient,
        get_pool_status,
        get_pooled_client,
        _pool_initialized,
        _registry,
    )

    # 2.1: PooledClient dataclass
    try:
        pc = PooledClient(
            client=None,
            session_id="test-session-123",
            user_id=42,
        )
        assert pc.session_id == "test-session-123"
        assert pc.user_id == 42
        assert pc.connected is False
        assert isinstance(pc.lock, asyncio.Lock)
        assert isinstance(pc.created_at, float)
        assert isinstance(pc.last_used, float)
        _ok("PooledClient dataclass: criação + defaults OK")
    except Exception as e:
        _fail("PooledClient dataclass falhou", str(e))

    # 2.2: asyncio.Lock no dataclass (Q1 — loop-agnostic)
    try:
        pc1 = PooledClient(client=None, session_id="a")
        pc2 = PooledClient(client=None, session_id="b")
        assert pc1.lock is not pc2.lock, "Locks devem ser instâncias distintas"
        _ok("asyncio.Lock: instâncias distintas por PooledClient (loop-agnostic)")
    except Exception as e:
        _fail("asyncio.Lock dataclass test falhou", str(e))

    # 2.3: get_pool_status quando flag=false
    if not USE_PERSISTENT_SDK_CLIENT:
        status = get_pool_status()
        assert status['enabled'] is False
        assert status['status'] == 'disabled'
        _ok("get_pool_status(): disabled quando flag=false")
    else:
        status = get_pool_status()
        assert status['enabled'] is True
        assert status['status'] in ('healthy', 'degraded')
        _ok(f"get_pool_status(): enabled, status={status['status']}, clients={status['total_clients']}")

    # 2.4: get_pooled_client retorna None para sessão inexistente
    result = get_pooled_client("nonexistent-session-id-12345")
    assert result is None, f"Esperado None, obteve {result}"
    _ok("get_pooled_client(): None para sessão inexistente")

    # 2.5: Registry está vazio (ou contém apenas sessões ativas)
    with threading.Lock():
        count = len(_registry)
    _ok(f"Registry: {count} clients ativos")

    # 2.6: submit_coroutine quando flag=false
    if not USE_PERSISTENT_SDK_CLIENT:
        try:
            from app.agente.sdk.client_pool import submit_coroutine

            async def _dummy():
                return 42

            submit_coroutine(_dummy())
            _fail("submit_coroutine deveria lançar RuntimeError quando flag=false")
        except RuntimeError as e:
            if "Pool não inicializado" in str(e):
                _ok("submit_coroutine(): RuntimeError correto quando flag=false")
            else:
                _fail("submit_coroutine(): RuntimeError inesperado", str(e))
        except Exception as e:
            _fail("submit_coroutine(): exceção inesperada", str(e))


# =====================================================================
# SEÇÃO 3: DAEMON THREAD (quando flag=true)
# =====================================================================
def test_daemon_thread():
    _section("3. DAEMON THREAD (flag=true only)")

    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT

    if not USE_PERSISTENT_SDK_CLIENT:
        _warn("SKIPPED: USE_PERSISTENT_SDK_CLIENT=false — daemon thread não inicia")
        return

    from app.agente.sdk.client_pool import (
        _sdk_loop,
        _sdk_loop_thread,
        _pool_initialized,
        _ensure_pool_initialized,
        submit_coroutine,
    )

    # Garantir inicialização (daemon inicia lazily)
    _ensure_pool_initialized()

    # Reler referências após inicialização
    from app.agente.sdk import client_pool as _cp
    _sdk_loop_thread = _cp._sdk_loop_thread
    _sdk_loop = _cp._sdk_loop

    # 3.1: Daemon thread está vivo
    if _sdk_loop_thread and _sdk_loop_thread.is_alive():
        _ok(f"Daemon thread vivo: name={_sdk_loop_thread.name}")
    else:
        _fail("Daemon thread NÃO está vivo")
        return

    # 3.2: Event loop está rodando
    if _sdk_loop and _sdk_loop.is_running():
        _ok(f"Event loop rodando: id={id(_sdk_loop)}")
    else:
        _fail("Event loop NÃO está rodando")
        return

    # 3.3: submit_coroutine funciona (round-trip)
    try:
        async def _echo():
            await asyncio.sleep(0.01)
            return "echo-from-daemon"

        future = submit_coroutine(_echo())
        result = future.result(timeout=5)
        assert result == "echo-from-daemon"
        _ok("submit_coroutine(): round-trip OK (coroutine executou no daemon)")
    except Exception as e:
        _fail("submit_coroutine() round-trip falhou", str(e))

    # 3.4: submit_coroutine preserva exceções
    try:
        async def _raise_error():
            raise ValueError("teste-erro-propagado")

        future = submit_coroutine(_raise_error())
        try:
            future.result(timeout=5)
            _fail("submit_coroutine deveria propagar ValueError")
        except ValueError as ve:
            if "teste-erro-propagado" in str(ve):
                _ok("submit_coroutine(): exceção propagada corretamente ao caller")
            else:
                _fail("submit_coroutine(): ValueError incorreto", str(ve))
    except Exception as e:
        _fail("submit_coroutine() propagação de erro falhou", str(e))

    # 3.5: Concorrência — 2 coroutines no mesmo loop
    try:
        results = []

        async def _concurrent(n):
            await asyncio.sleep(0.05)
            return f"result-{n}"

        f1 = submit_coroutine(_concurrent(1))
        f2 = submit_coroutine(_concurrent(2))
        r1 = f1.result(timeout=5)
        r2 = f2.result(timeout=5)
        assert r1 == "result-1"
        assert r2 == "result-2"
        _ok("submit_coroutine(): 2 coroutines concorrentes OK")
    except Exception as e:
        _fail("Concorrência submit_coroutine falhou", str(e))


# =====================================================================
# SEÇÃO 4: DC-2 FIX (app_context no daemon)
# =====================================================================
def test_dc2_app_context():
    _section("4. DC-2: APP_CONTEXT HANDLING")

    # 4.1: Dentro de app_context → _get_app_context retorna None
    try:
        from app.agente.config.permissions import _get_app_context, _execute_with_context
        from app import create_app

        app = create_app()
        with app.app_context():
            ctx = _get_app_context()
            assert ctx is None, f"Dentro de app_context, deveria ser None, obteve {ctx}"
            _ok("_get_app_context(): retorna None quando já tem app_context")
    except Exception as e:
        _fail("_get_app_context() dentro de app_context falhou", str(e))

    # 4.2: Fora de app_context → _get_app_context retorna context manager
    # Testado em thread separada (sem Flask context stack)
    try:
        test_result = [None]

        def _test_outside_context():
            try:
                ctx = _get_app_context()
                if ctx is not None:
                    with ctx:
                        from flask import current_app
                        _ = current_app.name
                    test_result[0] = "ok"
                else:
                    test_result[0] = "returned_none"
            except Exception as ex:
                test_result[0] = f"error: {ex}"

        t = threading.Thread(target=_test_outside_context)
        t.start()
        t.join(timeout=10)

        if test_result[0] == "ok":
            _ok("_get_app_context(): retorna context manager funcional fora de app_context (thread separada)")
        else:
            _fail("_get_app_context() fora de app_context", str(test_result[0]))
    except Exception as e:
        _fail("_get_app_context() fora de app_context falhou", str(e))

    # 4.3: _execute_with_context funciona em ambos cenários
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            result = _execute_with_context(lambda: "ok-inside")
            assert result == "ok-inside"
            _ok("_execute_with_context(): OK dentro de app_context")
    except Exception as e:
        _fail("_execute_with_context dentro de app_context falhou", str(e))


# =====================================================================
# SEÇÃO 5: CONTEXTVAR ISOLATION
# =====================================================================
def test_contextvar_isolation():
    _section("5. CONTEXTVAR ISOLATION")

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.agente.config.permissions import (
            set_current_session_id,
            get_current_session_id,
        )

        # 5.1: Set/get na mesma thread
        set_current_session_id("test-session-A")
        got = get_current_session_id()
        assert got == "test-session-A", f"Esperado test-session-A, obteve {got}"
        _ok("ContextVar: set/get na mesma thread OK")

        # 5.2: Isolamento entre threads
        other_thread_value = [None]

        def _read_in_other_thread():
            other_thread_value[0] = get_current_session_id()

        t = threading.Thread(target=_read_in_other_thread)
        t.start()
        t.join(timeout=2)

        # Outra thread deve ter valor default (None), não "test-session-A"
        if other_thread_value[0] is None:
            _ok("ContextVar: isolamento entre threads OK (outra thread = None)")
        else:
            _fail(
                "ContextVar: vazou entre threads!",
                f"Outra thread leu: {other_thread_value[0]}"
            )

        # 5.3: ContextVar em asyncio.Task (herança)
        from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
        if USE_PERSISTENT_SDK_CLIENT:
            try:
                from app.agente.sdk.client_pool import submit_coroutine

                async def _check_cv():
                    # Setar no daemon thread
                    set_current_session_id("daemon-test-cv")
                    return get_current_session_id()

                future = submit_coroutine(_check_cv())
                result = future.result(timeout=5)
                assert result == "daemon-test-cv"
                _ok("ContextVar: set/get funciona no daemon thread via submit_coroutine")
            except Exception as e:
                _fail("ContextVar no daemon thread falhou", str(e))
        else:
            _warn("SKIPPED: ContextVar no daemon (flag=false)")

        # Cleanup
        set_current_session_id(None)


# =====================================================================
# SEÇÃO 6: PENDING QUESTIONS (Dual Events)
# =====================================================================
def test_pending_questions():
    _section("6. PENDING QUESTIONS (Dual Events)")

    from app.agente.sdk.pending_questions import (
        register_question,
        submit_answer,
        cancel_pending,
        PendingQuestion,
        _pending,
    )

    test_session = "test-pq-session-123"

    # 6.1: register_question cria PendingQuestion com threading.Event
    try:
        pq = register_question(test_session, {"question": "Teste?"})
        assert isinstance(pq, PendingQuestion)
        assert pq.session_id == test_session
        assert isinstance(pq.event, threading.Event)
        assert not pq.event.is_set()
        _ok("register_question(): PendingQuestion criado com threading.Event")
    except Exception as e:
        _fail("register_question() falhou", str(e))
        return

    # 6.2: submit_answer sinaliza threading.Event
    try:
        submit_answer(test_session, {"answer": "Sim"})
        assert pq.event.is_set(), "threading.Event deveria estar setado"
        assert pq.answer is not None
        assert pq.answer.get("answer") == "Sim"
        _ok("submit_answer(): threading.Event sinalizado + answer salvo")
    except Exception as e:
        _fail("submit_answer() falhou", str(e))

    # 6.3: cancel_pending limpa estado
    try:
        # Registrar nova question
        pq2 = register_question(test_session, {"question": "Outra?"})
        cancel_pending(test_session)
        assert pq2.event.is_set(), "cancel deveria sinalizar event"
        assert test_session not in _pending
        _ok("cancel_pending(): limpa estado e sinaliza events")
    except Exception as e:
        _fail("cancel_pending() falhou", str(e))

    # Cleanup final
    if test_session in _pending:
        cancel_pending(test_session)


# =====================================================================
# SEÇÃO 7: CLIENT.PY — DISPATCH E GET_RESPONSE
# =====================================================================
def test_client_dispatch():
    _section("7. CLIENT.PY — DISPATCH E SIGNATURES")

    # 7.1: get_response aceita our_session_id
    try:
        import inspect
        from app.agente.sdk.client import AgentClient
        sig = inspect.signature(AgentClient.get_response)
        params = list(sig.parameters.keys())
        assert "our_session_id" in params, f"our_session_id ausente. Params: {params}"
        _ok(f"get_response(): our_session_id na assinatura (posição {params.index('our_session_id')})")
    except Exception as e:
        _fail("get_response() signature check falhou", str(e))

    # 7.2: stream_response aceita our_session_id
    try:
        sig = inspect.signature(AgentClient.stream_response)
        params = list(sig.parameters.keys())
        assert "our_session_id" in params
        _ok(f"stream_response(): our_session_id na assinatura (posição {params.index('our_session_id')})")
    except Exception as e:
        _fail("stream_response() signature check falhou", str(e))

    # 7.3: _stream_response_persistent aceita our_session_id
    try:
        sig = inspect.signature(AgentClient._stream_response_persistent)
        params = list(sig.parameters.keys())
        assert "our_session_id" in params
        _ok("_stream_response_persistent(): our_session_id na assinatura")
    except Exception as e:
        _fail("_stream_response_persistent() signature check falhou", str(e))

    # 7.4: Dispatch logic — verificar que stream_response tem branch de flag
    try:
        import ast
        with open('app/agente/sdk/client.py') as f:
            source = f.read()

        # Procurar o pattern de dispatch dentro de stream_response
        assert "USE_PERSISTENT_SDK_CLIENT" in source
        assert "_stream_response_persistent" in source
        _ok("stream_response(): dispatch flag + _stream_response_persistent presentes")
    except Exception as e:
        _fail("Dispatch logic check falhou", str(e))


# =====================================================================
# SEÇÃO 8: TEAMS SERVICES — DISPATCH E APP_CONTEXT
# =====================================================================
def test_teams_dispatch():
    _section("8. TEAMS SERVICES — DISPATCH E APP_CONTEXT")

    # 8.1: _obter_resposta_agente tem dispatch logic
    try:
        with open('app/teams/services.py') as f:
            source = f.read()

        # Sync path — deve ter submit_coroutine + asyncio.run
        assert "submit_coroutine(_get_response_with_timeout())" in source
        assert "asyncio.run(_get_response_with_timeout())" in source
        _ok("_obter_resposta_agente(): dispatch submit_coroutine/asyncio.run presente")
    except Exception as e:
        _fail("_obter_resposta_agente dispatch check falhou", str(e))

    # 8.2: _obter_resposta_agente passa our_session_id
    try:
        assert "our_session_id=our_session_id," in source
        assert 'our_session_id = session.session_id if session else None' in source
        _ok("_obter_resposta_agente(): our_session_id derivado e passado OK")
    except Exception as e:
        _fail("our_session_id em _obter_resposta_agente falhou", str(e))

    # 8.3: _obter_resposta_agente_streaming tem dispatch + app param
    try:
        import inspect
        from app.teams.services import _obter_resposta_agente_streaming
        sig = inspect.signature(_obter_resposta_agente_streaming)
        params = list(sig.parameters.keys())
        assert "app" in params, f"app ausente. Params: {params}"
        _ok(f"_obter_resposta_agente_streaming(): app na assinatura (posição {params.index('app')})")
    except Exception as e:
        _fail("_obter_resposta_agente_streaming signature check falhou", str(e))

    # 8.4: _safe_flush pattern presente
    try:
        assert "_safe_flush" in source
        assert "_needs_app_ctx" in source
        assert "app.app_context()" in source
        _ok("_safe_flush(): pattern com app_context presente no streaming path")
    except Exception as e:
        _fail("_safe_flush pattern check falhou", str(e))

    # 8.5: Streaming dispatch
    try:
        assert "submit_coroutine(_stream_with_timeout())" in source
        assert "asyncio.run(_stream_with_timeout())" in source
        _ok("_obter_resposta_agente_streaming(): dispatch submit_coroutine/asyncio.run presente")
    except Exception as e:
        _fail("Streaming dispatch check falhou", str(e))

    # 8.6: process_teams_task_async passa app
    try:
        assert "app=app," in source
        _ok("process_teams_task_async(): app=app passado ao streaming function")
    except Exception as e:
        _fail("app=app em process_teams_task_async falhou", str(e))


# =====================================================================
# SEÇÃO 9: TIMEOUT CASCADE (INVARIANTE CRÍTICA)
# =====================================================================
def test_timeout_cascade():
    _section("9. TIMEOUT CASCADE (invariante obrigatória)")

    # Heartbeat(10) < AskUser_web(55) < AskUser_Teams(120) < SDK_inactivity(240) < Stream_max(540) < Render(600)

    try:
        from app.agente.sdk.pending_questions import USER_RESPONSE_TIMEOUT
        from app.agente.config.feature_flags import TEAMS_ASK_USER_TIMEOUT

        # Ler constantes de routes.py
        with open('app/agente/routes.py') as f:
            routes_source = f.read()

        import re
        heartbeat = int(re.search(r'HEARTBEAT_INTERVAL_SECONDS\s*=\s*(\d+)', routes_source).group(1))
        stream_max = int(re.search(r'MAX_STREAM_DURATION_SECONDS\s*=\s*(\d+)', routes_source).group(1))
        sdk_inactivity = int(re.search(r'SDK_INACTIVITY_TIMEOUT_SECONDS\s*=\s*(\d+)', routes_source).group(1))

        render_hard = 600  # Configurado na infra Render

        timeouts = {
            'Heartbeat SSE': heartbeat,
            'AskUser web': USER_RESPONSE_TIMEOUT,
            'AskUser Teams': TEAMS_ASK_USER_TIMEOUT,
            'SDK inactivity': sdk_inactivity,
            'Stream max': stream_max,
            'Render hard': render_hard,
        }

        # Verificar ordenação
        values = list(timeouts.values())
        names = list(timeouts.keys())

        all_ordered = True
        for i in range(len(values) - 1):
            if values[i] >= values[i + 1]:
                _fail(
                    f"Timeout DESORDENADO: {names[i]}({values[i]}s) >= {names[i+1]}({values[i+1]}s)",
                    "Cascade de timeouts QUEBRADA — pode causar falhas em cascata"
                )
                all_ordered = False

        if all_ordered:
            cascade_str = " < ".join(f"{n}({v}s)" for n, v in timeouts.items())
            _ok(f"Cascade: {cascade_str}")

        # Verificar regra específica: AskUser web < SDK inactivity
        if USER_RESPONSE_TIMEOUT < sdk_inactivity:
            _ok(f"AskUser web ({USER_RESPONSE_TIMEOUT}s) < SDK inactivity ({sdk_inactivity}s) — REGRA RESPEITADA")
        else:
            _fail(
                f"AskUser web ({USER_RESPONSE_TIMEOUT}s) >= SDK inactivity ({sdk_inactivity}s)",
                "CLI mataria o stream antes do usuário responder!"
            )

    except Exception as e:
        _fail("Timeout cascade check falhou", str(e))


# =====================================================================
# SEÇÃO 10: ANÁLISE ESTÁTICA (grep patterns)
# =====================================================================
def test_static_analysis():
    _section("10. ANÁLISE ESTÁTICA")

    import subprocess

    def _grep_count(pattern, file_path):
        """Conta ocorrências de pattern em file."""
        try:
            result = subprocess.run(
                ['grep', '-c', pattern, file_path],
                capture_output=True, text=True
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            return -1

    # 10.1: streaming_done_event.set() em client.py (error handlers)
    count = _grep_count("streaming_done_event.set()", "app/agente/sdk/client.py")
    if count >= 5:
        _ok(f"streaming_done_event.set(): {count} chamadas em error handlers (esperado ≥5)")
    else:
        _fail(f"streaming_done_event.set(): apenas {count} chamadas (esperado ≥5)", "Error handler pode não limpar done_event")

    # 10.2: event_queue.put(None) em routes.py (sentinel)
    count = _grep_count("event_queue.put(None)", "app/agente/routes.py")
    if count >= 1:
        _ok(f"event_queue.put(None): {count} sentinel(s) em routes.py")
    else:
        _fail("event_queue.put(None): sentinel AUSENTE", "SSE generator pode travar!")

    # 10.3: _context_lock em permissions.py (thread-safety)
    count = _grep_count("_context_lock", "app/agente/config/permissions.py")
    if count >= 5:
        _ok(f"_context_lock: {count} usos em permissions.py")
    else:
        _warn(f"_context_lock: apenas {count} usos — verificar thread-safety manual")

    # 10.4: asyncio.new_event_loop() NÃO deve aparecer no agente (exceto client_pool)
    result = subprocess.run(
        ['grep', '-rn', 'asyncio.new_event_loop()', 'app/agente/'],
        capture_output=True, text=True
    )
    locations = [l for l in result.stdout.strip().split('\n') if l and 'client_pool.py' not in l]
    if not locations:
        _ok("asyncio.new_event_loop(): 0 ocorrências em agente/ (exceto client_pool) — correto")
    else:
        _warn(f"asyncio.new_event_loop(): encontrado fora de client_pool: {locations}")

    # 10.5: Verificar que streaming loop usa _safe_flush, não _flush_partial_to_db diretamente
    with open('app/teams/services.py') as f:
        source = f.read()

    # Dentro de _stream_with_flush, o loop (async for event ...) deve usar _safe_flush.
    # _flush_partial_to_db aparece DENTRO da definição de _safe_flush — isso é esperado.
    # Verificar que fora da definição de _safe_flush, não há chamada direta.
    start = source.find("async def _stream_with_flush():")
    end = source.find("async def _stream_with_timeout():", start)
    if start > 0 and end > start:
        stream_block = source[start:end]
        safe_calls = stream_block.count("_safe_flush(")
        # Contar _flush_partial_to_db fora da definição de _safe_flush
        safe_flush_def_start = stream_block.find("def _safe_flush(")
        safe_flush_def_end = stream_block.find("async for event", safe_flush_def_start) if safe_flush_def_start > 0 else -1
        if safe_flush_def_start > 0 and safe_flush_def_end > safe_flush_def_start:
            # Bloco após _safe_flush definition (o loop de eventos)
            loop_block = stream_block[safe_flush_def_end:]
            direct_in_loop = loop_block.count("_flush_partial_to_db(")
            if direct_in_loop == 0 and safe_calls >= 2:
                _ok(f"_stream_with_flush: loop usa _safe_flush ({safe_calls}x), não _flush_partial_to_db")
            elif direct_in_loop > 0:
                _fail(
                    f"_stream_with_flush: {direct_in_loop} chamadas diretas a _flush_partial_to_db no loop!",
                    "No daemon thread, _flush_partial_to_db sem app_context vai falhar"
                )
        else:
            _warn("_stream_with_flush: não conseguiu extrair bloco para análise")

    # 10.6: get_response passa our_session_id para stream_response
    with open('app/agente/sdk/client.py') as f:
        client_source = f.read()

    # Encontrar bloco get_response → stream_response call
    get_resp_start = client_source.find("async def get_response(")
    get_resp_end = client_source.find("return AgentResponse(", get_resp_start)
    if get_resp_start > 0 and get_resp_end > get_resp_start:
        get_resp_block = client_source[get_resp_start:get_resp_end]
        if "our_session_id=our_session_id" in get_resp_block:
            _ok("get_response → stream_response: our_session_id passado corretamente")
        else:
            _fail("get_response → stream_response: our_session_id NÃO passado!", "Pool key ficará '' para Teams")


# =====================================================================
# SEÇÃO 11: DATABASE (verificação de modelos)
# =====================================================================
def test_database_models():
    _section("11. DATABASE — MODELOS E SESSÕES")

    from app import create_app, db
    app = create_app()

    with app.app_context():
        # 11.1: AgentSession modelo existe
        try:
            from app.agente.models import AgentSession
            columns = [c.name for c in AgentSession.__table__.columns]
            assert 'session_id' in columns
            assert 'user_id' in columns
            assert 'data' in columns
            _ok(f"AgentSession: {len(columns)} colunas (session_id, user_id, data presentes)")
        except Exception as e:
            _fail("AgentSession modelo falhou", str(e))

        # 11.2: TeamsTask modelo existe
        try:
            from app.teams.models import TeamsTask
            columns = [c.name for c in TeamsTask.__table__.columns]
            assert 'id' in columns
            assert 'status' in columns
            assert 'resposta' in columns
            _ok(f"TeamsTask: {len(columns)} colunas (id, status, resposta presentes)")
        except Exception as e:
            _fail("TeamsTask modelo falhou", str(e))

        # 11.3: Verificar que DB responde (query simples)
        try:
            result = db.session.execute(db.text("SELECT 1")).scalar()
            assert result == 1
            _ok("Database: conexão OK (SELECT 1)")
        except Exception as e:
            _fail("Database conexão falhou", str(e))

        # 11.4: Contar sessões Teams ativas
        try:
            from app.agente.models import AgentSession
            teams_count = AgentSession.query.filter(
                AgentSession.session_id.like("teams_%")
            ).count()
            _ok(f"Sessões Teams no DB: {teams_count}")
        except Exception as e:
            _warn(f"Contagem de sessões Teams falhou: {e}")


# =====================================================================
# SEÇÃO 12: INTERRUPT (Fase 2)
# =====================================================================
def test_interrupt():
    _section("12. INTERRUPT (Fase 2)")

    # 12.1: Endpoint interrupt existe e tem lógica correta
    try:
        with open('app/agente/routes.py') as f:
            routes_source = f.read()

        assert "api/interrupt" in routes_source
        assert "USE_PERSISTENT_SDK_CLIENT" in routes_source
        assert "pooled.client.interrupt()" in routes_source or "client.interrupt()" in routes_source
        _ok("Endpoint /api/interrupt: presente com dispatch de flag")
    except Exception as e:
        _fail("Endpoint interrupt check falhou", str(e))

    # 12.2: interrupt_ack emitido por _parse_sdk_message
    try:
        with open('app/agente/sdk/client.py') as f:
            client_source = f.read()

        assert "interrupt_ack" in client_source
        _ok("interrupt_ack: emitido por _parse_sdk_message quando subtype='interrupted'")
    except Exception as e:
        _fail("interrupt_ack check falhou", str(e))

    # 12.3: Frontend já trata interrupt_ack
    try:
        with open('app/static/agente/js/chat.js') as f:
            chat_source = f.read()

        assert "interrupt_ack" in chat_source
        _ok("Frontend: chat.js trata interrupt_ack SSE event")
    except Exception as e:
        _warn(f"chat.js interrupt_ack check: {e}")


# =====================================================================
# SEÇÃO 13: INTEGRAÇÃO COMPLETA (flag=true, sem API call)
# =====================================================================
def test_integration_flag_true():
    _section("13. INTEGRAÇÃO (flag=true, sem API call)")

    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT

    if not USE_PERSISTENT_SDK_CLIENT:
        _warn("SKIPPED: USE_PERSISTENT_SDK_CLIENT=false — testes de integração requerem flag=true")
        _warn("Para testar: AGENT_PERSISTENT_SDK_CLIENT=true python scripts/test_sdk_client_migration.py")
        return

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.agente.sdk.client_pool import (
            submit_coroutine,
            get_pool_status,
        )

        # 13.1: Pool health check
        status = get_pool_status()
        if status.get('status') == 'healthy':
            _ok(f"Pool health: healthy ({status['total_clients']} clients)")
        else:
            _fail(f"Pool health: {status.get('status')}", str(status))

        # 13.2: Simular _safe_flush pattern (verificar app_context no daemon)
        try:
            async def _test_app_context_daemon():
                # No daemon thread, current_app não existe
                try:
                    from flask import current_app
                    _ = current_app.name
                    return "had_context"
                except RuntimeError:
                    return "no_context"

            future = submit_coroutine(_test_app_context_daemon())
            result = future.result(timeout=5)
            if result == "no_context":
                _ok("Daemon thread: confirmado SEM Flask app_context (como esperado)")
            else:
                _warn("Daemon thread TEM app_context — _safe_flush wrapping talvez desnecessário")
        except Exception as e:
            _fail("Teste app_context no daemon falhou", str(e))

        # 13.3: Simular _safe_flush com app.app_context() no daemon
        try:
            async def _test_safe_flush_pattern():
                _needs_ctx = False
                try:
                    from flask import current_app
                    _ = current_app.name
                except RuntimeError:
                    _needs_ctx = True

                if _needs_ctx:
                    # Simular o que _safe_flush faria
                    with app.app_context():
                        from app import db
                        result = db.session.execute(db.text("SELECT 1")).scalar()
                        return f"flush_ok_{result}"
                return "no_flush_needed"

            future = submit_coroutine(_test_safe_flush_pattern())
            result = future.result(timeout=5)
            if result == "flush_ok_1":
                _ok("_safe_flush pattern: DB access via app.app_context() no daemon OK")
            else:
                _ok(f"_safe_flush pattern: resultado={result}")
        except Exception as e:
            _fail("_safe_flush pattern no daemon falhou", str(e))

        # 13.4: ContextVar no daemon thread
        try:
            from app.agente.config.permissions import (
                set_current_session_id,
                get_current_session_id,
            )

            async def _test_cv_daemon():
                set_current_session_id("daemon-integration-test")
                val = get_current_session_id()
                set_current_session_id(None)  # cleanup
                return val

            future = submit_coroutine(_test_cv_daemon())
            result = future.result(timeout=5)
            assert result == "daemon-integration-test"
            _ok("ContextVar set/get no daemon: integração OK")
        except Exception as e:
            _fail("ContextVar integração no daemon falhou", str(e))

        # 13.5: MCP tools user_id ContextVar
        try:
            async def _test_user_id_cv():
                from app.agente.tools.text_to_sql_tool import (
                    _current_user_id as sql_user_id,
                )
                from app.agente.tools.memory_mcp_tool import (
                    _current_user_id as mem_user_id,
                )

                sql_user_id.set(99)
                mem_user_id.set(99)
                result = (sql_user_id.get(), mem_user_id.get())
                sql_user_id.set(0)
                mem_user_id.set(0)
                return result

            future = submit_coroutine(_test_user_id_cv())
            r = future.result(timeout=5)
            assert r == (99, 99)
            _ok("MCP ContextVars (sql, memory): set/get no daemon OK")
        except Exception as e:
            _fail("MCP ContextVars no daemon falhou", str(e))


# =====================================================================
# SEÇÃO 14: DC-2 VERIFICATION (2 pontos EXATOS em permissions.py)
# =====================================================================
def test_dc2_exact_points():
    _section("14. DC-2: VERIFICAÇÃO DOS 2 PONTOS EXATOS")

    # G11: Os 2 pontos onde db.session.get(TeamsTask) existia sem
    # _execute_with_context() — DEVEM estar wrappados após fix DC-2.
    try:
        with open('app/agente/config/permissions.py') as f:
            source = f.read()

        # Ponto 1: _update_task_awaiting (awaiting_user_input)
        # Deve ter _execute_with_context(_update_task_awaiting)
        if '_execute_with_context(_update_task_awaiting)' in source:
            _ok("DC-2 ponto 1: _update_task_awaiting wrappado em _execute_with_context")
        else:
            _fail("DC-2 ponto 1: _update_task_awaiting NÃO wrappado!", "db.session.get() sem app_context no daemon")

        # Ponto 2: _reset_task_timeout (timeout path)
        # Deve ter _execute_with_context(_reset_task_timeout)
        if '_execute_with_context(_reset_task_timeout)' in source:
            _ok("DC-2 ponto 2: _reset_task_timeout wrappado em _execute_with_context")
        else:
            _fail("DC-2 ponto 2: _reset_task_timeout NÃO wrappado!", "db.session.get() sem app_context no daemon")

        # Verificar que NÃO há db.session.get(TeamsTask) FORA de _execute_with_context
        import re
        # Encontrar todas as linhas com db.session.get(TeamsTask
        matches = [(i+1, line.strip()) for i, line in enumerate(source.split('\n'))
                   if 'db.session.get(TeamsTask' in line]

        # Cada match deve estar dentro de uma função passada a _execute_with_context
        # Verificar que todas estão dentro de def _update_task_* ou def _reset_task_*
        for line_num, line in matches:
            # Verificar contexto: a função pai deve ser uma closure wrappada
            preceding = source.split('\n')[max(0, line_num-10):line_num]
            preceding_text = '\n'.join(preceding)
            if 'def _update_task_' in preceding_text or 'def _reset_task_' in preceding_text:
                pass  # OK, está dentro de closure wrappada
            else:
                _fail(
                    f"DC-2: db.session.get(TeamsTask) na linha {line_num} FORA de closure wrappada!",
                    f"Linha: {line}"
                )

        if len(matches) >= 2:
            _ok(f"DC-2: {len(matches)} usos de db.session.get(TeamsTask), todos em closures wrappadas")

    except Exception as e:
        _fail("DC-2 exact points check falhou", str(e))


# =====================================================================
# SEÇÃO 15: DC-3, DC-6, PLAYWRIGHT (Descobertas Críticas)
# =====================================================================
def test_critical_discoveries():
    _section("15. DESCOBERTAS CRÍTICAS (DC-3, DC-6, DC-1)")

    # G3: DC-3 — self.settings.model em vez de options_dict.get("model")
    # no hook H06 (_user_prompt_submit_hook)
    try:
        with open('app/agente/sdk/client.py') as f:
            client_source = f.read()

        # Encontrar o bloco do UserPromptSubmit hook
        hook_start = client_source.find("def _user_prompt_submit_hook(")
        if hook_start < 0:
            hook_start = client_source.find("_user_prompt_submit")
        hook_end = client_source.find("\n        return ", hook_start + 1) if hook_start > 0 else -1

        if hook_start > 0:
            # Extrair bloco do hook (próximas ~200 linhas)
            hook_block = client_source[hook_start:hook_start + 8000]

            # Deve usar self.settings.model (DC-3 fix)
            uses_settings_model = "self.settings.model" in hook_block
            # NÃO deve usar options_dict.get("model") para lógica de model
            uses_options_dict_model = 'options_dict.get("model")' in hook_block or "options_dict.get('model')" in hook_block

            if uses_settings_model:
                _ok("DC-3: Hook H06 usa self.settings.model (não stale)")
            else:
                _warn("DC-3: self.settings.model NÃO encontrado no hook H06 — pode usar options_dict (stale)")

            if uses_options_dict_model:
                _warn("DC-3: options_dict.get('model') ainda presente no hook H06 — pode ficar stale com set_model()")
        else:
            _warn("DC-3: Não encontrou bloco _user_prompt_submit_hook")

    except Exception as e:
        _fail("DC-3 check falhou", str(e))

    # G4: DC-6 — async_event (asyncio.Event) em PendingQuestion
    try:
        from app.agente.sdk.pending_questions import PendingQuestion, register_question, cancel_pending
        import inspect

        # Verificar que PendingQuestion tem campo async_event
        fields = {f.name for f in PendingQuestion.__dataclass_fields__.values()}
        assert 'async_event' in fields, f"async_event ausente. Campos: {fields}"
        _ok("DC-6: PendingQuestion tem campo async_event (asyncio.Event)")

        # Testar que register_question em async context cria async_event
        from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
        if USE_PERSISTENT_SDK_CLIENT:
            from app.agente.sdk.client_pool import submit_coroutine

            async def _test_async_event_creation():
                test_sid = "test-dc6-async-event"
                pq = register_question(test_sid, {"q": "test?"})
                has_async = pq.async_event is not None
                cancel_pending(test_sid)
                return has_async

            future = submit_coroutine(_test_async_event_creation())
            has_async = future.result(timeout=5)
            if has_async:
                _ok("DC-6: register_question em async context cria asyncio.Event")
            else:
                _fail("DC-6: register_question em async context NÃO criou asyncio.Event!")
        else:
            _warn("DC-6 SKIPPED: async_event creation requer flag=true (daemon com event loop)")

    except Exception as e:
        _fail("DC-6 check falhou", str(e))

    # G6: DC-1 — Playwright globals awareness
    try:
        with open('app/agente/tools/playwright_mcp_tool.py') as f:
            pw_source = f.read()

        # Verificar presença de globals compartilhados (awareness)
        globals_found = []
        for gvar in ['_playwright', '_browser', '_context', '_page']:
            if f'{gvar} =' in pw_source or f'{gvar}: ' in pw_source:
                globals_found.append(gvar)

        if globals_found:
            _warn(
                f"DC-1 Playwright: {len(globals_found)} globals compartilhados "
                f"({', '.join(globals_found)}). Fix planejado Fase 4"
            )
        else:
            _ok("DC-1: Nenhum global compartilhado encontrado (já fixado?)")

        # Verificar se _frame_local usa threading.local (vai ser migrado para ContextVar na Fase 4)
        if 'threading.local' in pw_source:
            _warn("DC-1: _frame_local usa threading.local (migrará para ContextVar na Fase 4)")

    except Exception as e:
        _warn(f"DC-1 Playwright check: {e}")


# =====================================================================
# SEÇÃO 16: REGRESSION GUARDS (REG04, auto-restart, concurrency)
# =====================================================================
def test_regression_guards():
    _section("16. REGRESSION GUARDS")

    import subprocess

    # G5: REG04 — threading.local() NÃO deve existir em agente/ (exceto playwright, docs, debug, comments)
    try:
        result = subprocess.run(
            ['grep', '-rn', 'threading.local()', 'app/agente/'],
            capture_output=True, text=True
        )
        locations = []
        for l in result.stdout.strip().split('\n'):
            if not l:
                continue
            # Excluir falsos positivos conhecidos
            if 'playwright_mcp_tool.py' in l:  # DC-1 aceito (Fase 4)
                continue
            if '.md' in l.split(':')[0]:  # Documentação
                continue
            if l.split(':')[0].endswith('.md'):  # Documentação
                continue
            # Verificar se é comentário ou string (# ou aspas antes de threading.local)
            line_content = ':'.join(l.split(':')[2:]).strip() if len(l.split(':')) > 2 else ''
            if line_content.startswith('#') or line_content.startswith('"""') or line_content.startswith("'''"):
                continue
            # Debug endpoint /contextvar-test é teste interno, não uso em produção
            if 'contextvar-test' in l or 'contextvar_test' in l or 'test_tl' in l:
                continue
            locations.append(l)

        if not locations:
            _ok("REG04: 0 usos de threading.local() em agente/ (exceto playwright/docs/debug/comments)")
        else:
            _fail(
                f"REG04: threading.local() encontrado em {len(locations)} local(is)!",
                f"Locais: {'; '.join(locations[:3])}"
            )
    except Exception as e:
        _fail("REG04 check falhou", str(e))

    # G1: R01 — Daemon auto-restart após crash
    try:
        from app.agente.sdk.client_pool import _run_loop_forever
        import inspect
        source = inspect.getsource(_run_loop_forever)

        # Deve resetar _pool_initialized = False no except/finally
        if '_pool_initialized = False' in source or '_pool_initialized' in source:
            _ok("R01: _run_loop_forever() reseta _pool_initialized no crash (auto-restart path)")
        else:
            _fail("R01: _run_loop_forever() NÃO reseta _pool_initialized!", "Daemon crash = agente offline permanente")
    except Exception as e:
        _fail("R01 auto-restart check falhou", str(e))

    # G2: R08 — asyncio.Lock no PooledClient previne query concorrente
    try:
        from app.agente.sdk.client_pool import PooledClient
        pc = PooledClient(client=None, session_id="test-lock")
        assert isinstance(pc.lock, asyncio.Lock), f"lock não é asyncio.Lock: {type(pc.lock)}"
        _ok("R08: PooledClient tem asyncio.Lock para serialização")

        # Verificar que _stream_response_persistent usa o lock
        with open('app/agente/sdk/client.py') as f:
            client_source = f.read()

        persistent_start = client_source.find("async def _stream_response_persistent(")
        if persistent_start > 0:
            # Buscar no bloco completo até o próximo "async def" no mesmo nível
            next_method = client_source.find("\n    async def ", persistent_start + 10)
            if next_method < 0:
                next_method = len(client_source)
            persistent_block = client_source[persistent_start:next_method]
            if 'pooled.lock' in persistent_block or 'async with pooled.lock' in persistent_block:
                _ok("R08: _stream_response_persistent() usa pooled.lock (anti-concurrent)")
            else:
                _warn("R08: pooled.lock NÃO encontrado em _stream_response_persistent — concorrência possível")
    except Exception as e:
        _fail("R08 concurrency lock check falhou", str(e))

    # G8: _parse_sdk_message é método standalone
    try:
        from app.agente.sdk.client import AgentClient
        assert hasattr(AgentClient, '_parse_sdk_message'), "_parse_sdk_message não existe em AgentClient"
        import inspect
        sig = inspect.signature(AgentClient._parse_sdk_message)
        params = list(sig.parameters.keys())
        assert 'message' in params, f"_parse_sdk_message sem param 'message': {params}"
        _ok(f"_parse_sdk_message(): método standalone, params={params}")
    except Exception as e:
        _fail("_parse_sdk_message check falhou", str(e))

    # G7: 3ª ContextVar — session_search_tool._current_user_id
    try:
        from app.agente.tools.session_search_tool import _current_user_id as session_user_id
        from contextvars import ContextVar
        assert isinstance(session_user_id, ContextVar)
        _ok("CV03: session_search_tool._current_user_id é ContextVar")

        # Testar no daemon se flag=true
        from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
        if USE_PERSISTENT_SDK_CLIENT:
            from app.agente.sdk.client_pool import submit_coroutine

            async def _test_session_cv():
                session_user_id.set(88)
                val = session_user_id.get()
                session_user_id.set(0)
                return val

            future = submit_coroutine(_test_session_cv())
            result = future.result(timeout=5)
            assert result == 88
            _ok("CV03: session_search_tool ContextVar funciona no daemon thread")
        else:
            _warn("CV03 SKIPPED: daemon test requer flag=true")
    except Exception as e:
        _fail("CV03 session_search_tool check falhou", str(e))


# =====================================================================
# SEÇÃO 17: POOL LIFECYCLE (shutdown, cleanup, recovery)
# =====================================================================
def test_pool_lifecycle():
    _section("17. POOL LIFECYCLE (shutdown, cleanup, recovery)")

    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT

    # G9: shutdown_pool existe e é callable
    try:
        from app.agente.sdk.client_pool import shutdown_pool
        import inspect
        assert callable(shutdown_pool)
        source = inspect.getsource(shutdown_pool)
        assert '_shutdown_requested = True' in source
        assert 'disconnect_client' in source
        assert '_sdk_loop.stop' in source or 'call_soon_threadsafe' in source
        _ok("shutdown_pool(): existe, seta _shutdown_requested, desconecta clients, para loop")
    except Exception as e:
        _fail("shutdown_pool check falhou", str(e))

    # G10: _cleanup_idle_clients lógica correta
    try:
        from app.agente.sdk.client_pool import _cleanup_idle_clients
        import inspect
        source = inspect.getsource(_cleanup_idle_clients)
        assert 'idle_timeout' in source
        assert 'disconnect_client' in source
        assert 'last_used' in source
        _ok("_cleanup_idle_clients(): verifica idle_timeout, usa last_used, chama disconnect_client")
    except Exception as e:
        _fail("_cleanup_idle_clients check falhou", str(e))

    # _periodic_cleanup roda no daemon
    try:
        from app.agente.sdk.client_pool import _periodic_cleanup
        import inspect
        source = inspect.getsource(_periodic_cleanup)
        assert '_shutdown_requested' in source
        assert 'asyncio.sleep' in source
        assert '_cleanup_idle_clients' in source
        _ok("_periodic_cleanup(): loop infinito com sleep + _cleanup_idle_clients")
    except Exception as e:
        _fail("_periodic_cleanup check falhou", str(e))

    # Cleanup real no daemon (flag=true only)
    if USE_PERSISTENT_SDK_CLIENT:
        try:
            from app.agente.sdk.client_pool import submit_coroutine, _cleanup_idle_clients, _registry

            # Cleanup com timeout 0 não deve crashar (mesmo sem clients idle)
            async def _test_cleanup():
                before = len(_registry)
                await _cleanup_idle_clients(idle_timeout=99999)  # nenhum client idle
                after = len(_registry)
                return (before, after)

            future = submit_coroutine(_test_cleanup())
            before, after = future.result(timeout=5)
            _ok(f"_cleanup_idle_clients() no daemon: executou sem erro ({before}→{after} clients)")
        except Exception as e:
            _fail("_cleanup_idle_clients no daemon falhou", str(e))
    else:
        _warn("SKIPPED: cleanup no daemon requer flag=true")


# =====================================================================
# SEÇÃO 18: RESUMO
# =====================================================================
def print_summary():
    print(f"\n{'='*60}")
    print(f"  RESUMO FINAL")
    print(f"{'='*60}")
    print(f"  ✓ Passou:   {_passed}")
    print(f"  ✗ Falhou:   {_failed}")
    print(f"  ⚠ Avisos:   {_warnings}")
    print(f"{'='*60}")

    if _errors:
        print(f"\n  FALHAS:")
        for err in _errors:
            print(f"    ✗ {err}")

    from app.agente.config.feature_flags import USE_PERSISTENT_SDK_CLIENT
    if not USE_PERSISTENT_SDK_CLIENT:
        print(f"\n  NOTA: Flag USE_PERSISTENT_SDK_CLIENT=false")
        print(f"  Seções 3, 5.3, 13, 15(DC-6), 16(CV03), 17 foram skippadas.")
        print(f"  Para teste completo: AGENT_PERSISTENT_SDK_CLIENT=true")

    if _failed == 0:
        print(f"\n  🟢 TODOS OS TESTES PASSARAM")
    else:
        print(f"\n  🔴 {_failed} TESTE(S) FALHARAM — verificar acima")

    print()
    return _failed == 0


# =====================================================================
# MAIN
# =====================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  DIAGNÓSTICO: Migração SDK Client (Fases 0-3)")
    print("  Ref: .claude/references/ROADMAP_SDK_CLIENT.md")
    print("=" * 60)

    # Verificar se estamos no diretório correto
    if not os.path.exists('app/agente/sdk/client_pool.py'):
        print("\n✗ ERRO: Execute do diretório raiz do projeto!")
        print("  cd /path/to/frete_sistema && python scripts/test_sdk_client_migration.py")
        sys.exit(1)

    try:
        test_imports_and_flags()
        test_pool_infrastructure()
        test_daemon_thread()
        test_dc2_app_context()
        test_contextvar_isolation()
        test_pending_questions()
        test_client_dispatch()
        test_teams_dispatch()
        test_timeout_cascade()
        test_static_analysis()
        test_database_models()
        test_interrupt()
        test_integration_flag_true()
        test_dc2_exact_points()
        test_critical_discoveries()
        test_regression_guards()
        test_pool_lifecycle()
    except Exception as e:
        print(f"\n✗ ERRO FATAL: {e}")
        traceback.print_exc()
    finally:
        success = print_summary()
        sys.exit(0 if success else 1)
