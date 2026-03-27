"""
Testes unitarios para app.agente.sdk.client_pool.

Cobre: PooledClient dataclass, inicializacao do pool, submit_coroutine,
get_or_create_client, disconnect_client, _force_kill_subprocess,
get_pooled_client, _cleanup_idle_clients, get_pool_status, shutdown_pool.

Todos os testes usam a fixture `pool_reset` para isolamento de estado
entre testes (reseta module globals apos cada teste).
"""
import asyncio
import time
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.agente.sdk.client_pool as cp
from app.agente.sdk.client_pool import (
    PooledClient,
    _force_kill_subprocess,
    _cleanup_idle_clients,
    _ensure_pool_initialized,
    submit_coroutine,
    get_or_create_client,
    disconnect_client,
    get_pooled_client,
    get_pool_status,
    shutdown_pool,
)


pytestmark = [pytest.mark.unit, pytest.mark.sdk_client]


# ─── 1. PooledClient dataclass ──────────────────────────────────────

class TestPooledClient:

    def test_pooled_client_defaults(self, pool_reset):
        """Verifica defaults do dataclass e que cada instancia tem Lock independente."""
        now = time.time()
        client_mock = MagicMock()

        p1 = PooledClient(client=client_mock, session_id='sess-aaa')
        p2 = PooledClient(client=client_mock, session_id='sess-bbb')

        # Defaults
        assert p1.user_id == 0
        assert p1.connected is False
        assert p1.created_at >= now
        assert p1.last_used >= now

        # Cada instancia tem Lock proprio (nao compartilhado)
        assert isinstance(p1.lock, asyncio.Lock)
        assert isinstance(p2.lock, asyncio.Lock)
        assert p1.lock is not p2.lock


# ─── 2. _ensure_pool_initialized ────────────────────────────────────

class TestEnsurePoolInitialized:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', False)
    def test_ensure_pool_initialized_flag_false(self, pool_reset):
        """Retorna False quando USE_PERSISTENT_SDK_CLIENT=false."""
        result = _ensure_pool_initialized()

        assert result is False
        assert cp._pool_initialized is False
        assert cp._sdk_loop is None
        assert cp._sdk_loop_thread is None

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_ensure_pool_initialized_flag_true(self, pool_reset):
        """Cria daemon thread e event loop quando flag=true."""
        result = _ensure_pool_initialized()

        assert result is True
        assert cp._pool_initialized is True
        assert cp._sdk_loop is not None
        assert cp._sdk_loop.is_running() is True
        assert cp._sdk_loop_thread is not None
        assert cp._sdk_loop_thread.is_alive() is True
        assert cp._sdk_loop_thread.daemon is True
        assert cp._sdk_loop_thread.name == 'sdk-pool-daemon'

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_ensure_pool_idempotent(self, pool_reset):
        """Segunda chamada retorna True sem recriar thread/loop (double-checked locking)."""
        result1 = _ensure_pool_initialized()
        loop_after_first = cp._sdk_loop
        thread_after_first = cp._sdk_loop_thread

        result2 = _ensure_pool_initialized()

        assert result1 is True
        assert result2 is True
        # Mesmos objetos — nao recriou
        assert cp._sdk_loop is loop_after_first
        assert cp._sdk_loop_thread is thread_after_first


# ─── 3. submit_coroutine ────────────────────────────────────────────

class TestSubmitCoroutine:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_submit_coroutine_round_trip(self, pool_reset):
        """Submete coroutine simples e verifica retorno via Future."""
        _ensure_pool_initialized()

        async def _add(a, b):
            return a + b

        future = submit_coroutine(_add(3, 7))
        result = future.result(timeout=5)

        assert result == 10

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_submit_coroutine_propagates_exception(self, pool_reset):
        """Excecao dentro da coroutine propaga para o Future."""
        _ensure_pool_initialized()

        async def _fail():
            raise ValueError("boom")

        future = submit_coroutine(_fail())

        with pytest.raises(ValueError, match="boom"):
            future.result(timeout=5)

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', False)
    def test_submit_coroutine_not_initialized(self, pool_reset):
        """RuntimeError quando pool nao esta inicializado."""
        async def _noop():
            pass

        with pytest.raises(RuntimeError, match="Pool"):
            submit_coroutine(_noop())


# ─── 4. get_pooled_client ───────────────────────────────────────────

class TestGetPooledClient:

    def test_get_pooled_client_nonexistent(self, pool_reset):
        """Retorna None para session_id inexistente."""
        result = get_pooled_client('nonexistent-session')
        assert result is None

    def test_get_pooled_client_existing(self, pool_reset):
        """Retorna PooledClient quando existe no registry."""
        client_mock = MagicMock()
        pooled = PooledClient(client=client_mock, session_id='sess-123', connected=True)
        cp._registry['sess-123'] = pooled

        result = get_pooled_client('sess-123')
        assert result is pooled
        assert result.session_id == 'sess-123'


# ─── 5. get_or_create_client ────────────────────────────────────────

class TestGetOrCreateClient:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_get_or_create_creates_new(self, pool_reset, mock_claude_sdk_client):
        """Cria novo ClaudeSDKClient e conecta quando nao existe no pool."""
        _ensure_pool_initialized()

        mock_cls = MagicMock(return_value=mock_claude_sdk_client)

        with patch('claude_agent_sdk.ClaudeSDKClient', mock_cls, create=True):
            future = submit_coroutine(
                get_or_create_client('sess-new', options=MagicMock(), user_id=42)
            )
            pooled = future.result(timeout=5)

        assert pooled.session_id == 'sess-new'
        assert pooled.user_id == 42
        assert pooled.connected is True
        mock_claude_sdk_client.connect.assert_awaited_once()
        # Deve estar no registry
        assert 'sess-new' in cp._registry

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_get_or_create_reuses_existing(self, pool_reset):
        """Retorna PooledClient existente se conectado (fast path)."""
        _ensure_pool_initialized()

        client_mock = MagicMock()
        existing = PooledClient(
            client=client_mock, session_id='sess-reuse',
            user_id=1, connected=True,
        )
        cp._registry['sess-reuse'] = existing
        original_last_used = existing.last_used

        # Pequena pausa para que last_used mude
        time.sleep(0.01)

        future = submit_coroutine(
            get_or_create_client('sess-reuse', options=MagicMock(), user_id=1)
        )
        result = future.result(timeout=5)

        # Mesmo objeto retornado
        assert result is existing
        # last_used atualizado
        assert result.last_used > original_last_used

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_get_or_create_replaces_disconnected(self, pool_reset, mock_claude_sdk_client):
        """Client desconectado e substituido por novo."""
        _ensure_pool_initialized()

        old_client = MagicMock()
        old_pooled = PooledClient(
            client=old_client, session_id='sess-disc',
            connected=False,
        )
        cp._registry['sess-disc'] = old_pooled

        mock_cls = MagicMock(return_value=mock_claude_sdk_client)

        with patch('claude_agent_sdk.ClaudeSDKClient', mock_cls, create=True):
            future = submit_coroutine(
                get_or_create_client('sess-disc', options=MagicMock())
            )
            result = future.result(timeout=5)

        # Novo client, nao o antigo
        assert result is not old_pooled
        assert result.connected is True
        assert result.client is mock_claude_sdk_client
        mock_claude_sdk_client.connect.assert_awaited_once()


# ─── 6. disconnect_client ───────────────────────────────────────────

class TestDisconnectClient:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_disconnect_client_normal(self, pool_reset):
        """disconnect() normal remove do registry e chama client.disconnect()."""
        _ensure_pool_initialized()

        client_mock = AsyncMock()
        pooled = PooledClient(
            client=client_mock, session_id='sess-dc',
            connected=True,
        )
        cp._registry['sess-dc'] = pooled

        future = submit_coroutine(disconnect_client('sess-dc'))
        result = future.result(timeout=5)

        assert result is True
        assert 'sess-dc' not in cp._registry
        client_mock.disconnect.assert_awaited_once()
        assert pooled.connected is False

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_disconnect_force_kill_fallback(self, pool_reset):
        """disconnect() falha com RuntimeError e fallback para force kill."""
        _ensure_pool_initialized()

        client_mock = AsyncMock()
        client_mock.disconnect = AsyncMock(
            side_effect=RuntimeError("cross-task cancel scope")
        )
        # Transport para force kill funcionar
        transport_mock = AsyncMock()
        transport_mock.close = AsyncMock()
        client_mock._transport = transport_mock

        pooled = PooledClient(
            client=client_mock, session_id='sess-fk',
            connected=True,
        )
        cp._registry['sess-fk'] = pooled

        future = submit_coroutine(disconnect_client('sess-fk'))
        result = future.result(timeout=5)

        assert result is True
        assert 'sess-fk' not in cp._registry
        # disconnect foi tentado
        client_mock.disconnect.assert_awaited_once()
        # force kill via transport.close
        transport_mock.close.assert_awaited_once()
        assert pooled.connected is False

    def test_disconnect_client_not_found(self, pool_reset):
        """Retorna False se session_id nao esta no registry."""
        # Rodar a coroutine diretamente (nao precisa do pool inicializado)
        result = asyncio.get_event_loop().run_until_complete(
            disconnect_client('nonexistent')
        )
        assert result is False


# ─── 7. _force_kill_subprocess ──────────────────────────────────────

class TestForceKillSubprocess:

    def test_force_kill_via_transport(self):
        """transport.close() e chamado quando client._transport existe."""
        client = MagicMock()
        transport = AsyncMock()
        transport.close = AsyncMock()
        client._transport = transport

        result = asyncio.get_event_loop().run_until_complete(
            _force_kill_subprocess(client)
        )

        assert result is True
        transport.close.assert_awaited_once()

    def test_force_kill_via_query_transport(self):
        """Fallback: usa client._query.transport quando _transport nao existe."""
        client = MagicMock(spec=[])  # sem _transport
        query = MagicMock()
        transport = AsyncMock()
        transport.close = AsyncMock()
        query.transport = transport
        client._query = query

        result = asyncio.get_event_loop().run_until_complete(
            _force_kill_subprocess(client)
        )

        assert result is True
        transport.close.assert_awaited_once()

    def test_force_kill_no_transport(self):
        """Retorna False quando nenhum transport e encontrado."""
        client = MagicMock(spec=[])  # sem _transport nem _query

        result = asyncio.get_event_loop().run_until_complete(
            _force_kill_subprocess(client)
        )

        assert result is False


# ─── 8. _cleanup_idle_clients ───────────────────────────────────────

class TestCleanupIdleClients:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_cleanup_removes_idle(self, pool_reset):
        """Client com last_used antigo e removido pelo cleanup."""
        _ensure_pool_initialized()

        client_mock = AsyncMock()
        client_mock.disconnect = AsyncMock()
        pooled = PooledClient(
            client=client_mock, session_id='sess-idle',
            connected=True,
        )
        # Forcar last_used no passado (600s atras)
        pooled.last_used = time.time() - 600
        cp._registry['sess-idle'] = pooled

        future = submit_coroutine(_cleanup_idle_clients(idle_timeout=300))
        future.result(timeout=5)

        # Client idle deve ter sido removido
        assert 'sess-idle' not in cp._registry
        assert pooled.connected is False

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_cleanup_keeps_active(self, pool_reset):
        """Client com last_used recente NAO e removido."""
        _ensure_pool_initialized()

        client_mock = AsyncMock()
        pooled = PooledClient(
            client=client_mock, session_id='sess-active',
            connected=True,
        )
        # last_used agora (default)
        cp._registry['sess-active'] = pooled

        future = submit_coroutine(_cleanup_idle_clients(idle_timeout=300))
        future.result(timeout=5)

        # Client ativo deve permanecer
        assert 'sess-active' in cp._registry
        assert pooled.connected is True


# ─── 9. get_pool_status ─────────────────────────────────────────────

class TestGetPoolStatus:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', False)
    def test_pool_status_disabled(self, pool_reset):
        """Retorna status 'disabled' quando flag esta false."""
        status = get_pool_status()

        assert status['enabled'] is False
        assert status['status'] == 'disabled'
        assert 'total_clients' not in status

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_pool_status_healthy(self, pool_reset):
        """Retorna dict com chaves esperadas quando pool esta saudavel."""
        _ensure_pool_initialized()

        # Adicionar um client no registry para verificar clients_info
        client_mock = MagicMock()
        pooled = PooledClient(
            client=client_mock, session_id='sess-status-12345678',
            user_id=5, connected=True,
        )
        cp._registry['sess-status-12345678'] = pooled

        status = get_pool_status()

        assert status['enabled'] is True
        assert status['status'] == 'healthy'
        assert status['daemon_thread_alive'] is True
        assert status['event_loop_running'] is True
        assert status['total_clients'] == 1
        assert len(status['clients']) == 1

        client_info = status['clients'][0]
        assert client_info['session_id'] == 'sess-sta...'
        assert client_info['user_id'] == 5
        assert client_info['connected'] is True
        assert 'idle_seconds' in client_info
        assert 'age_seconds' in client_info


# ─── 10. shutdown_pool ──────────────────────────────────────────────

class TestShutdownPool:

    @patch('app.agente.config.feature_flags.USE_PERSISTENT_SDK_CLIENT', True)
    def test_shutdown_pool(self, pool_reset):
        """Shutdown desconecta todos os clients, para loop e join thread."""
        _ensure_pool_initialized()

        # Adicionar clients ao registry
        client1 = AsyncMock()
        client1.disconnect = AsyncMock()
        p1 = PooledClient(client=client1, session_id='sess-shut-1', connected=True)

        client2 = AsyncMock()
        client2.disconnect = AsyncMock()
        p2 = PooledClient(client=client2, session_id='sess-shut-2', connected=True)

        cp._registry['sess-shut-1'] = p1
        cp._registry['sess-shut-2'] = p2

        loop_before = cp._sdk_loop
        thread_before = cp._sdk_loop_thread

        shutdown_pool()

        assert cp._pool_initialized is False
        assert cp._shutdown_requested is True
        # Registry esvaziado pelo disconnect_client
        assert 'sess-shut-1' not in cp._registry
        assert 'sess-shut-2' not in cp._registry
        # Loop parado
        assert not loop_before.is_running()
        # Thread encerrada
        assert not thread_before.is_alive()

    def test_shutdown_pool_noop_when_not_initialized(self, pool_reset):
        """Shutdown sem inicializacao nao faz nada (sem crash)."""
        assert cp._pool_initialized is False

        shutdown_pool()  # Nao deve levantar excecao

        assert cp._pool_initialized is False
