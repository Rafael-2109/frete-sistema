"""
PostgresSessionStore adapter para claude-agent-sdk 0.1.64+.

Fase A dual-run: roda em paralelo com session_persistence.py. Substitui o ciclo
manual backup/restore JSONL ↔ AgentSession.sdk_session_transcript (TEXT blob)
pelo contrato SessionStore oficial (append/load/list_sessions/delete/list_subkeys
sob tabela claude_session_store).

Schema: copia fiel de examples/session_stores/postgres_session_store.py (SDK 0.1.64,
PR 842) — nao divergir sem revisar conformance harness.

Arquitetura:
- Pool asyncpg LAZY per-worker (NAO module-level eager) para compatibilidade com
  gunicorn fork. Lock evita double-init em corridas async.
- Pool separado do SQLAlchemy/psycopg2 sync usado no resto do app — nao ha
  interacao. min_size=1, max_size=3 por worker (4 workers = 12 conexoes asyncpg
  adicionais, bem dentro do limite 100 do Render Starter).
- DSN parsed para remover client_encoding e options= que asyncpg nao entende
  (psycopg2-specific).

Conformance: tests/agente/sdk/test_session_store_conformance.py roda o harness
oficial do SDK (13 contratos) contra este adapter. GATE antes de habilitar em
producao.

FONTES:
- /tmp/sdk-164/extracted/claude_agent_sdk/_internal/session_store.py (InMemory ref)
- /tmp/sdk-164/extracted/claude_agent_sdk/testing/session_store_conformance.py
- /tmp/postgres_store_ref.py (reference adapter oficial)
- /tmp/subagent-findings/20260421-sessionstore-60ddbe70/phase3/plan-v2-final.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import TYPE_CHECKING, Optional

from claude_agent_sdk import (
    SessionKey,
    SessionListSubkeysKey,
    SessionStore,
    SessionStoreEntry,
    SessionStoreListEntry,
)

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

__all__ = [
    "PostgresSessionStore",
    "get_or_create_session_store",
    "close_session_store_pool",
    "_store_implements",  # util publico, replica de SDK._internal
]

# -----------------------------------------------------------------------------
# Identifier guard
# -----------------------------------------------------------------------------

#: Identificador valido para nome de tabela — interpolado em SQL (asyncpg nao
#: parametriza identificadores). Rejeita qualquer coisa fora de [A-Za-z_][A-Za-z0-9_]*.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# -----------------------------------------------------------------------------
# Pool lifecycle (LAZY per-worker)
# -----------------------------------------------------------------------------

_pool: Optional["asyncpg.Pool"] = None
_pool_lock: asyncio.Lock = asyncio.Lock()


def _prepare_dsn(url: str) -> str:
    """Converte DSN SQLAlchemy/psycopg2 para formato asyncpg.

    Remove query params que asyncpg nao entende:
    - client_encoding: psycopg2-specific, asyncpg sempre usa UTF-8.
    - options=-c timezone=...: psycopg2-specific (-c flag), asyncpg usa
      ``server_settings`` no create_pool se precisarmos.

    Preserva sslmode=require e demais params validos.
    """
    url = re.sub(r"[?&]client_encoding=[^&]*", "", url)
    url = re.sub(r"[?&]options=[^&]*", "", url)
    # Limpa `?&` ou `?` orfao
    url = re.sub(r"\?&", "?", url).rstrip("?").rstrip("&")
    return url


async def _get_pool() -> "asyncpg.Pool":
    """Retorna pool asyncpg (lazy init). Thread-safe via asyncio.Lock.

    CRITICAL: pool NAO e criado em module import (module-level eager quebra
    gunicorn fork — sockets compartilhados entre workers).

    Raises:
        RuntimeError: se DATABASE_URL nao setado.
        ImportError: se asyncpg nao instalado (requirements.txt desatualizado).
    """
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        # Double-check apos aquirir lock
        if _pool is not None:
            return _pool

        import asyncpg  # import local: so importa quando flag ON

        dsn_raw = os.environ.get("DATABASE_URL")
        if not dsn_raw:
            raise RuntimeError(
                "[SESSION_STORE] DATABASE_URL nao definido — nao posso criar pool asyncpg"
            )
        dsn = _prepare_dsn(dsn_raw)

        _pool = await asyncpg.create_pool(
            dsn,
            min_size=1,
            max_size=3,  # conservador: 4 workers * 3 = 12 conn asyncpg adicionais
            command_timeout=30,  # match psycopg2 connect_args.command_timeout
        )
        logger.info(
            f"[SESSION_STORE] pool asyncpg criado (min=1 max=3 timeout=30s) "
            f"— worker pid={os.getpid()}"
        )
        return _pool


async def close_session_store_pool() -> None:
    """Fecha o pool asyncpg (best-effort, chamado em shutdown)."""
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
            logger.info(f"[SESSION_STORE] pool asyncpg fechado — worker pid={os.getpid()}")
        except Exception as e:
            logger.warning(f"[SESSION_STORE] erro fechando pool (ignorado): {e}")
        finally:
            _pool = None


# -----------------------------------------------------------------------------
# SessionStore protocol check (replica de _internal/session_store_validation.py)
# -----------------------------------------------------------------------------

def _store_implements(store: SessionStore, method: str) -> bool:
    """True se ``store`` override ``method`` (vs inheritar Protocol default que raise).

    Replica de claude_agent_sdk._internal.session_store_validation._store_implements
    (privado no SDK). Replicamos aqui para evitar import de _internal.

    Uso: pre-flight checks antes de chamar metodos opcionais (list_sessions,
    delete, list_subkeys) que lancam NotImplementedError por default no Protocol.
    """
    default = getattr(SessionStore, method, None)
    return getattr(type(store), method, None) is not default


# -----------------------------------------------------------------------------
# Adapter
# -----------------------------------------------------------------------------

class PostgresSessionStore(SessionStore):
    """Postgres-backed :class:`~claude_agent_sdk.SessionStore`.

    Uma linha por transcript entry. append() e single multi-row INSERT com
    unnest() + WITH ORDINALITY (atomico, ordem preservada). load() e
    SELECT ORDER BY seq ASC.

    Implementa 5 dos 6 metodos do protocol:
    - append() — required
    - load() — required
    - list_sessions() — optional, implementado (GROUP BY)
    - delete() — optional, implementado (cascade para subkeys se main)
    - list_subkeys() — optional, implementado (SELECT DISTINCT)
    - list_session_summaries() — optional, NAO implementado (harness 0.1.64 nao testa;
      helpers *_from_store caem para slow-path via list_sessions + load per-session)

    Args:
        pool: Pre-configurado ``asyncpg.Pool``. Use :func:`get_or_create_session_store`
            para obter instancia com pool lazy gerenciado.
        table: Nome da tabela. Default "claude_session_store". Validado contra
            ``[A-Za-z_][A-Za-z0-9_]*`` (interpolado em SQL).
    """

    def __init__(
        self,
        pool: "asyncpg.Pool",
        table: str = "claude_session_store",
    ) -> None:
        if pool is None:
            raise ValueError("PostgresSessionStore requer 'pool'")
        if not _IDENT_RE.match(table):
            raise ValueError(
                f"table {table!r} deve bater [A-Za-z_][A-Za-z0-9_]* "
                "(e interpolado em SQL)"
            )
        self._pool = pool
        self._table = table

    # ------------------------------------------------------------------
    # Protocol — required
    # ------------------------------------------------------------------

    async def append(
        self, key: SessionKey, entries: list[SessionStoreEntry]
    ) -> None:
        """Grava batch de entries. Preserva ordem via WITH ORDINALITY.

        Contrato at-most-once: falha levanta excecao, batcher trata via on_error.
        Contrato no-op em lista vazia.
        """
        if not entries:
            return  # Contract 4: append([]) e no-op
        subpath = key.get("subpath") or ""
        await self._pool.execute(
            f"""
            INSERT INTO {self._table} (project_key, session_id, subpath, entry, mtime)
            SELECT $1, $2, $3, e,
                   (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint
            FROM unnest($4::jsonb[]) WITH ORDINALITY AS t(e, ord)
            ORDER BY ord
            """,
            key["project_key"],
            key["session_id"],
            subpath,
            [json.dumps(e) for e in entries],
        )

    async def load(
        self, key: SessionKey
    ) -> list[SessionStoreEntry] | None:
        """Retorna entries na ordem de insercao (seq ASC) ou None se key nunca escrita.

        Contrato: retorno deep-equal ao appended, NAO byte-equal (JSONB reordena
        keys alfabeticamente — SDK tolera explicitamente).
        """
        rows = await self._pool.fetch(
            f"""
            SELECT entry FROM {self._table}
            WHERE project_key = $1 AND session_id = $2 AND subpath = $3
            ORDER BY seq
            """,
            key["project_key"],
            key["session_id"],
            key.get("subpath") or "",
        )
        if not rows:
            return None  # Contract 2: unknown key retorna None
        # asyncpg retorna jsonb como str/bytes por default (sem codec registrado).
        # json.loads preserva ordem de insercao (Python 3.7+).
        out: list[SessionStoreEntry] = []
        for row in rows:
            v = row["entry"]
            out.append(json.loads(v) if isinstance(v, (str, bytes)) else v)
        return out

    # ------------------------------------------------------------------
    # Protocol — optional (implementados)
    # ------------------------------------------------------------------

    async def list_sessions(
        self, project_key: str
    ) -> list[SessionStoreListEntry]:
        """Lista main transcripts de um project_key com mtime (epoch-ms).

        Contract 8: subagent subpaths sao excluidos (filter subpath='').
        Index parcial (subpath='') torna query O(log n).
        """
        rows = await self._pool.fetch(
            f"""
            SELECT session_id, MAX(mtime) AS mtime FROM {self._table}
            WHERE project_key = $1 AND subpath = ''
            GROUP BY session_id
            """,
            project_key,
        )
        return [
            {"session_id": r["session_id"], "mtime": int(r["mtime"])}
            for r in rows
        ]

    async def delete(self, key: SessionKey) -> None:
        """Deleta session.

        Contract 9/10: delete main (sem subpath) cascade para todos subkeys.
        Contract 11: delete com subpath remove apenas aquele subpath.
        Contract 9 (sub): no-op em key inexistente (idempotente).
        """
        subpath = key.get("subpath")
        if subpath:
            await self._pool.execute(
                f"""
                DELETE FROM {self._table}
                WHERE project_key = $1 AND session_id = $2 AND subpath = $3
                """,
                key["project_key"],
                key["session_id"],
                subpath,
            )
            return
        # Cascade: main + todos subkeys (inclusive subpath='')
        await self._pool.execute(
            f"""
            DELETE FROM {self._table}
            WHERE project_key = $1 AND session_id = $2
            """,
            key["project_key"],
            key["session_id"],
        )

    async def list_subkeys(
        self, key: SessionListSubkeysKey
    ) -> list[str]:
        """Lista subpaths (!= '') de uma session.

        Contract 13: main transcript (subpath='') e excluido.
        """
        rows = await self._pool.fetch(
            f"""
            SELECT DISTINCT subpath FROM {self._table}
            WHERE project_key = $1 AND session_id = $2 AND subpath <> ''
            """,
            key["project_key"],
            key["session_id"],
        )
        return [r["subpath"] for r in rows]


# -----------------------------------------------------------------------------
# Factory publica
# -----------------------------------------------------------------------------

async def get_or_create_session_store() -> PostgresSessionStore:
    """Retorna instancia PostgresSessionStore. Pool lazy inicializado na primeira chamada.

    Uso esperado: chamar em `_stream_response_persistent` (async) apos
    `options = self._build_options(...)` e antes de `get_or_create_client`.

    Raises:
        RuntimeError: DATABASE_URL ausente.
        ImportError: asyncpg nao instalado.
    """
    pool = await _get_pool()
    return PostgresSessionStore(pool=pool)
