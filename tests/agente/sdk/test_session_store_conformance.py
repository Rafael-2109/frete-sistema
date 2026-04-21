"""
Conformance test: PostgresSessionStore vs harness oficial do SDK 0.1.64.

Roda os 13 contratos behavioral de `claude_agent_sdk.testing.run_session_store_conformance`
contra nosso adapter. Usa tabela TEST_TABLE separada (claude_session_store_test)
com TRUNCATE entre contratos para isolamento.

GATE: 13/13 contratos PASSANDO antes de habilitar flag em producao.

Usage:
    pytest tests/agente/sdk/test_session_store_conformance.py -v

Requer DATABASE_URL apontando para Postgres (pode ser o DB de dev local).
NAO usa Render prod — tabela e sempre TEST_TABLE.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

# Skip modulo inteiro se asyncpg nao instalado (ex: CI sem extras)
asyncpg = pytest.importorskip("asyncpg")

# Skip se SDK 0.1.64+ nao disponivel
pytest.importorskip(
    "claude_agent_sdk.testing",
    reason="requer claude-agent-sdk>=0.1.64 (SessionStore conformance harness)",
)

from claude_agent_sdk.testing import run_session_store_conformance  # noqa: E402

from app.agente.sdk.session_store_adapter import (  # noqa: E402
    PostgresSessionStore,
    _prepare_dsn,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

TEST_TABLE = "claude_session_store_test"


@pytest_asyncio.fixture
async def test_pool():
    """Pool asyncpg isolado + tabela TEST efemera.

    Cria tabela TEST no setup, dropa no teardown. Nao colide com producao
    (tabela separada) nem com outros testes (fresh fixture por test).
    """
    dsn_raw = os.environ.get("DATABASE_URL")
    if not dsn_raw:
        pytest.skip("DATABASE_URL nao setado — pule ou configure PG de dev")

    pool = await asyncpg.create_pool(_prepare_dsn(dsn_raw), min_size=1, max_size=2)

    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TEST_TABLE} (
              project_key text   NOT NULL,
              session_id  text   NOT NULL,
              subpath     text   NOT NULL DEFAULT '',
              seq         bigserial,
              entry       jsonb  NOT NULL,
              mtime       bigint NOT NULL,
              PRIMARY KEY (project_key, session_id, subpath, seq)
            )
        """)
        # Garante tabela vazia na entrada do teste (mesmo que TRUNCATE dentro falhe)
        await conn.execute(f"TRUNCATE {TEST_TABLE} RESTART IDENTITY")

    try:
        yield pool
    finally:
        async with pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        await pool.close()


async def test_conformance_13_contracts(test_pool):
    """Valida os 13 contratos do harness oficial.

    Cada chamada a `make_store()` (uma por contrato) faz TRUNCATE da tabela
    para isolamento. Fresh store instance por contrato.
    """

    async def make_store():
        async with test_pool.acquire() as conn:
            await conn.execute(f"TRUNCATE {TEST_TABLE} RESTART IDENTITY")
        return PostgresSessionStore(pool=test_pool, table=TEST_TABLE)

    # NAO passa skip_optional — queremos validar TODOS os metodos implementados
    # (list_sessions, delete, list_subkeys). list_session_summaries nao e
    # implementado, mas o harness so roda contratos desse metodo se o store
    # overridem (ele nao faz — Protocol default raise NotImplementedError).
    await run_session_store_conformance(make_store)


async def test_adapter_rejects_bad_table_name(test_pool):
    """Identifier guard deve rejeitar nomes de tabela invalidos (SQL injection defense)."""
    with pytest.raises(ValueError, match=r"deve bater"):
        PostgresSessionStore(pool=test_pool, table="drop table users;--")
    with pytest.raises(ValueError, match=r"deve bater"):
        PostgresSessionStore(pool=test_pool, table="123invalid")
    with pytest.raises(ValueError, match=r"deve bater"):
        PostgresSessionStore(pool=test_pool, table="")


async def test_adapter_requires_pool():
    """Construtor deve falhar sem pool."""
    with pytest.raises(ValueError, match=r"pool"):
        PostgresSessionStore(pool=None)  # type: ignore[arg-type]


def test_prepare_dsn_removes_psycopg2_specific_params():
    """_prepare_dsn deve remover client_encoding e options=... que asyncpg nao entende.

    Preserva sslmode (Render Postgres usa sslmode=require).
    """
    # Caso Render tipico
    dsn = (
        "postgresql://user:pw@host:5432/db"
        "?sslmode=require&client_encoding=utf8"
        "&options=-c%20timezone=America/Sao_Paulo"
    )
    cleaned = _prepare_dsn(dsn)
    assert "client_encoding" not in cleaned
    assert "options=" not in cleaned
    assert "sslmode=require" in cleaned
    assert "postgresql://user:pw@host:5432/db" in cleaned

    # DSN sem params extras
    simple = "postgresql://localhost:5432/mydb"
    assert _prepare_dsn(simple) == simple

    # DSN apenas com params a remover → volta para base limpo
    only_bad = "postgresql://localhost:5432/db?client_encoding=utf8"
    cleaned_only = _prepare_dsn(only_bad)
    assert cleaned_only == "postgresql://localhost:5432/db"
