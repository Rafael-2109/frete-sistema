"""
Session Pool para ClaudeSDKClient.

Gerencia instancias de ClaudeSDKClient com:
- Pool bounded (max_clients) com evicao LRU
- Cleanup periodico de clients inativos
- Health check antes de reutilizar
- Lock por client para serializar queries (obrigatorio pelo SDK)
- Metricas para observabilidade

Referencia: https://platform.claude.com/docs/en/agent-sdk/python
CRITICO: Nunca usar break dentro de receive_response() — causa deadlock asyncio.
"""

import asyncio
import atexit
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    ProcessError,
    CLINotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class PooledClient:
    """
    Wrapper de um ClaudeSDKClient com metadados de sessao.

    Atributos:
        client: Instancia do ClaudeSDKClient
        session_id: Nosso session_id (NAO o do SDK)
        user_id: ID do usuario dono desta sessao
        options: Options usadas na criacao (para recriacao se necessario)
        created_at: Quando o client foi criado
        last_used: Ultima vez que uma query foi feita
        connected: Se o client esta conectado
        lock: asyncio.Lock para serializar queries (1 por vez, obrigatorio pelo SDK)
    """
    client: ClaudeSDKClient
    session_id: str
    user_id: int
    options: ClaudeAgentOptions
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    connected: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self):
        """Atualiza last_used para agora."""
        self.last_used = datetime.now(timezone.utc)

    @property
    def idle_seconds(self) -> float:
        """Segundos desde a ultima utilizacao."""
        return (datetime.now(timezone.utc) - self.last_used).total_seconds()


class SessionPool:
    """
    Pool bounded de ClaudeSDKClient com evicao LRU.

    Cada ClaudeSDKClient consome ~300-500MB (subprocesso CLI).
    O pool limita instancias simultaneas e evicta as menos usadas
    quando o limite e atingido.

    Thread-safety:
    - _global_lock (asyncio.Lock) para operacoes no dict do pool
    - PooledClient.lock (asyncio.Lock) para serializar queries no mesmo client
    - Pool e acessado APENAS dentro de asyncio.run() (thread separada)

    Uso:
        pool = SessionPool(max_clients=5, idle_timeout=300)

        # Obter ou criar client
        pooled = await pool.get_or_create(session_id, user_id, options)

        # Usar (dentro do lock do client)
        async with pooled.lock:
            await pooled.client.query("prompt")
            async for msg in pooled.client.receive_response():
                ...

        # Interrupt
        await pool.interrupt(session_id)

        # Cleanup
        await pool.destroy_all()
    """

    def __init__(
        self,
        max_clients: int = 5,
        idle_timeout: int = 300,
        cleanup_interval: int = 60,
    ):
        self.max_clients = max_clients
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval

        self._pool: Dict[str, PooledClient] = {}
        self._global_lock = asyncio.Lock()

        # Metricas
        self._total_created = 0
        self._total_evicted = 0
        self._total_destroyed = 0
        self._created_at = datetime.now(timezone.utc)

        # Background cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_stop_event = threading.Event()
        self._start_cleanup_thread()

        # Registrar cleanup no shutdown
        atexit.register(self._atexit_cleanup)

        logger.info(
            f"[SESSION_POOL] Inicializado: max_clients={max_clients}, "
            f"idle_timeout={idle_timeout}s, cleanup_interval={cleanup_interval}s"
        )

    # ================================================================
    # METODOS PUBLICOS (async — rodam dentro de asyncio.run())
    # ================================================================

    async def get_or_create(
        self,
        session_id: str,
        user_id: int,
        options: ClaudeAgentOptions,
    ) -> PooledClient:
        """
        Obtem client existente ou cria novo.

        Se o pool esta cheio, evicta o client menos usado (LRU).
        Se o client existente falhar no health check, destroi e cria novo.

        Args:
            session_id: Nosso session_id (NAO o do SDK)
            user_id: ID do usuario
            options: ClaudeAgentOptions para criacao

        Returns:
            PooledClient pronto para uso

        Raises:
            ProcessError: Se nao conseguir criar/conectar o client
        """
        async with self._global_lock:
            # Tentar reutilizar existente
            if session_id in self._pool:
                pooled = self._pool[session_id]

                # Health check: verificar se processo esta vivo
                if await self._health_check(pooled):
                    pooled.touch()
                    logger.info(
                        f"[SESSION_POOL] Reutilizando client: session={session_id[:8]}... "
                        f"(idle={pooled.idle_seconds:.0f}s)"
                    )
                    return pooled
                else:
                    # Client morreu — destruir e recriar
                    logger.warning(
                        f"[SESSION_POOL] Client morto detectado: session={session_id[:8]}... "
                        f"Destruindo e recriando."
                    )
                    await self._destroy_unlocked(session_id)

            # Verificar se pool esta cheio
            if len(self._pool) >= self.max_clients:
                logger.info(
                    f"[SESSION_POOL] Pool cheio ({len(self._pool)}/{self.max_clients}). "
                    f"Evictando LRU..."
                )
                await self._evict_lru()

            # Criar novo client
            pooled = await self._create_client(session_id, user_id, options)
            self._pool[session_id] = pooled
            self._total_created += 1

            logger.info(
                f"[SESSION_POOL] Novo client criado: session={session_id[:8]}... "
                f"pool={len(self._pool)}/{self.max_clients}"
            )
            return pooled

    async def destroy(self, session_id: str) -> bool:
        """
        Desconecta e remove client do pool.

        Returns:
            True se encontrou e destruiu, False se nao existia
        """
        async with self._global_lock:
            return await self._destroy_unlocked(session_id)

    async def destroy_all(self):
        """Desconecta e remove TODOS os clients. Usar no shutdown."""
        async with self._global_lock:
            session_ids = list(self._pool.keys())
            for sid in session_ids:
                await self._destroy_unlocked(sid)
            logger.info(f"[SESSION_POOL] Todos os clients destruidos ({len(session_ids)} total)")

    async def interrupt(self, session_id: str) -> bool:
        """
        Interrompe operacao em andamento no client.

        Returns:
            True se interrompeu, False se sessao nao encontrada
        """
        pooled = self._pool.get(session_id)
        if not pooled or not pooled.connected:
            return False

        try:
            await pooled.client.interrupt()
            logger.info(f"[SESSION_POOL] Interrupt enviado: session={session_id[:8]}...")
            return True
        except Exception as e:
            logger.warning(f"[SESSION_POOL] Erro no interrupt: session={session_id[:8]}... {e}")
            return False

    async def cleanup_idle(self):
        """Remove clients inativos alem do idle_timeout."""
        async with self._global_lock:
            to_destroy = [
                sid for sid, pooled in self._pool.items()
                if pooled.idle_seconds > self.idle_timeout
            ]

            for sid in to_destroy:
                logger.info(
                    f"[SESSION_POOL] Cleanup: removendo client inativo "
                    f"session={sid[:8]}... (idle={self._pool[sid].idle_seconds:.0f}s)"
                )
                await self._destroy_unlocked(sid)

            if to_destroy:
                logger.info(
                    f"[SESSION_POOL] Cleanup: {len(to_destroy)} clients removidos. "
                    f"Pool: {len(self._pool)}/{self.max_clients}"
                )

    def get_if_exists(self, session_id: str) -> Optional[PooledClient]:
        """
        Retorna PooledClient se existir no pool (sem lock async).

        NOTA: Este metodo e sync para uso em endpoints Flask.
        Nao modifica o pool, apenas leitura.
        """
        return self._pool.get(session_id)

    def get_stats(self) -> dict:
        """Retorna metricas do pool para observabilidade."""
        now = datetime.now(timezone.utc)
        active = sum(1 for p in self._pool.values() if p.connected)
        idle = len(self._pool) - active

        return {
            "max_clients": self.max_clients,
            "total_clients": len(self._pool),
            "active_clients": active,
            "idle_clients": idle,
            "total_created": self._total_created,
            "total_evicted": self._total_evicted,
            "total_destroyed": self._total_destroyed,
            "idle_timeout_seconds": self.idle_timeout,
            "uptime_seconds": int((now - self._created_at).total_seconds()),
            "sessions": [
                {
                    "session_id": sid[:8] + "...",
                    "user_id": p.user_id,
                    "connected": p.connected,
                    "idle_seconds": int(p.idle_seconds),
                    "created_at": p.created_at.isoformat(),
                }
                for sid, p in self._pool.items()
            ],
        }

    # ================================================================
    # METODOS PRIVADOS
    # ================================================================

    async def _create_client(
        self,
        session_id: str,
        user_id: int,
        options: ClaudeAgentOptions,
    ) -> PooledClient:
        """Cria e conecta um novo ClaudeSDKClient."""
        client = ClaudeSDKClient(options=options)

        try:
            await client.connect()
            logger.info(f"[SESSION_POOL] Client conectado: session={session_id[:8]}...")
        except Exception as e:
            logger.error(f"[SESSION_POOL] Falha ao conectar client: session={session_id[:8]}... {e}")
            # Tentar cleanup do client que falhou
            try:
                await client.disconnect()
            except Exception:
                pass
            raise

        return PooledClient(
            client=client,
            session_id=session_id,
            user_id=user_id,
            options=options,
            connected=True,
        )

    async def _destroy_unlocked(self, session_id: str) -> bool:
        """
        Destroi client SEM adquirir _global_lock (chamador ja tem o lock).
        """
        pooled = self._pool.pop(session_id, None)
        if not pooled:
            return False

        try:
            if pooled.connected:
                await pooled.client.disconnect()
                pooled.connected = False
            self._total_destroyed += 1
            logger.info(f"[SESSION_POOL] Client destruido: session={session_id[:8]}...")
        except Exception as e:
            self._total_destroyed += 1
            logger.warning(
                f"[SESSION_POOL] Erro ao destruir client: session={session_id[:8]}... {e}"
            )

        return True

    async def _evict_lru(self):
        """
        Evicta o client menos recentemente usado.

        Chamado SEM _global_lock (chamador ja tem o lock).
        """
        if not self._pool:
            return

        # Encontrar o client com last_used mais antigo
        lru_sid = min(self._pool, key=lambda sid: self._pool[sid].last_used)
        lru = self._pool[lru_sid]

        logger.info(
            f"[SESSION_POOL] Evictando LRU: session={lru_sid[:8]}... "
            f"(idle={lru.idle_seconds:.0f}s, user={lru.user_id})"
        )

        await self._destroy_unlocked(lru_sid)
        self._total_evicted += 1

    async def _health_check(self, pooled: PooledClient) -> bool:
        """
        Verifica se o subprocesso CLI do client esta vivo.

        Returns:
            True se saudavel, False se morto/desconectado
        """
        if not pooled.connected:
            return False

        try:
            # Tentar obter info do servidor — se falhar, processo morreu
            info = await pooled.client.get_server_info()
            return info is not None
        except (ProcessError, CLINotFoundError, Exception) as e:
            logger.warning(
                f"[SESSION_POOL] Health check falhou: session={pooled.session_id[:8]}... {e}"
            )
            pooled.connected = False
            return False

    # ================================================================
    # BACKGROUND CLEANUP
    # ================================================================

    def _start_cleanup_thread(self):
        """Inicia thread daemon para cleanup periodico."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._cleanup_stop_event.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="session-pool-cleanup",
        )
        self._cleanup_thread.start()
        logger.debug("[SESSION_POOL] Cleanup thread iniciada")

    def _cleanup_loop(self):
        """Loop de cleanup que roda em thread daemon."""
        while not self._cleanup_stop_event.is_set():
            self._cleanup_stop_event.wait(timeout=self.cleanup_interval)

            if self._cleanup_stop_event.is_set():
                break

            # Executar cleanup async em novo event loop
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup_idle())
                loop.close()
            except Exception as e:
                logger.warning(f"[SESSION_POOL] Erro no cleanup loop: {e}")

    def _atexit_cleanup(self):
        """Cleanup no shutdown da aplicacao (registrado via atexit)."""
        logger.info("[SESSION_POOL] Shutdown: destruindo todos os clients...")

        # Parar thread de cleanup
        self._cleanup_stop_event.set()

        # Destruir todos os clients
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.destroy_all())
            loop.close()
        except Exception as e:
            logger.warning(f"[SESSION_POOL] Erro no atexit cleanup: {e}")

    def stop(self):
        """Para a thread de cleanup (para testes)."""
        self._cleanup_stop_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
