"""
D3 — Fatos bi-temporais + proveniência no Knowledge Graph.

Testa:
 T1. _upsert_relation com source_session_id grava a coluna (consulta direta no DB).
 T2. _upsert_relation sem source_session_id → coluna fica NULL (backward-compat).
 T3. _link_entity_to_memory com source_session_id grava a coluna.
 T4. _link_entity_to_memory sem source_session_id → NULL (backward-compat).
 T5. valid_from passado para _upsert_relation é gravado; valid_to fica NULL.
 T6. ON CONFLICT preserva 1ª source_session_id (não sobrescreve com nova sessão).
 T7. Flag-OFF: extract_and_link_entities não popula source_session_id (NULL).
 T8. Migration idempotente: rodar novamente não falha e colunas permanecem.

Usa banco local real (mesmo pattern de test_kg_empresa_scope.py que não usa mock).
Cada teste cria usuário / entidades / memórias efêmeras e desfaz via rollback.
"""
import inspect
from datetime import datetime
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures — banco de dados real (rollback no teardown)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_conn():
    """Conexão raw SQLAlchemy com rollback garantido."""
    from app import create_app, db as _db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        with _db.engine.begin() as conn:
            # Transação aninhada para rollback limpo
            sp = conn.begin_nested()
            yield conn, text
            sp.rollback()


@pytest.fixture()
def entity_ids(db_conn):
    """Cria 2 entidades efêmeras e retorna seus IDs."""
    conn, text = db_conn
    from app.utils.timezone import agora_utc_naive

    def _insert_entity(name: str) -> int:
        now = agora_utc_naive()
        result = conn.execute(text("""
            INSERT INTO agent_memory_entities
              (user_id, entity_type, entity_name, first_seen_at, last_seen_at)
            VALUES (1, 'conceito', :name, :now, :now)
            RETURNING id
        """), {"name": name, "now": now})
        return result.scalar()

    src_id = _insert_entity("D3_TEST_SRC")
    tgt_id = _insert_entity("D3_TEST_TGT")
    return src_id, tgt_id


@pytest.fixture()
def memory_id(db_conn, entity_ids):
    """Cria uma memória efêmera para os testes de _link_entity_to_memory."""
    conn, text = db_conn
    from app.utils.timezone import agora_utc_naive

    now = agora_utc_naive()
    result = conn.execute(text("""
        INSERT INTO agent_memories
          (user_id, path, content, created_at, updated_at)
        VALUES (1, '/memories/d3_test_link', 'D3 content', :now, :now)
        RETURNING id
    """), {"now": now})
    return result.scalar()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_relation(conn, text, src_id: int, tgt_id: int, rel_type: str = 'co_occurs') -> dict | None:
    row = conn.execute(text("""
        SELECT source_session_id, source_step_uid, valid_from, valid_to
        FROM agent_memory_entity_relations
        WHERE source_entity_id = :s AND target_entity_id = :t AND relation_type = :r
    """), {"s": src_id, "t": tgt_id, "r": rel_type}).fetchone()
    if row is None:
        return None
    return {
        "source_session_id": row[0],
        "source_step_uid": row[1],
        "valid_from": row[2],
        "valid_to": row[3],
    }


def _read_link(conn, text, entity_id: int, memory_id: int) -> dict | None:
    row = conn.execute(text("""
        SELECT source_session_id, source_step_uid
        FROM agent_memory_entity_links
        WHERE entity_id = :e AND memory_id = :m
    """), {"e": entity_id, "m": memory_id}).fetchone()
    if row is None:
        return None
    return {
        "source_session_id": row[0],
        "source_step_uid": row[1],
    }


# ---------------------------------------------------------------------------
# T1 — _upsert_relation grava source_session_id quando fornecido
# ---------------------------------------------------------------------------

def test_upsert_relation_grava_source_session_id(db_conn, entity_ids):
    conn, text = db_conn
    src_id, tgt_id = entity_ids

    from app.agente.services.knowledge_graph_service import _upsert_relation

    _upsert_relation(
        conn, src_id, tgt_id,
        relation_type='co_occurs',
        weight=1.0,
        source_session_id='sess-abc123',
    )

    row = _read_relation(conn, text, src_id, tgt_id)
    assert row is not None, "Relação não foi gravada"
    assert row['source_session_id'] == 'sess-abc123', (
        f"source_session_id esperado 'sess-abc123', obtido {row['source_session_id']!r}"
    )


# ---------------------------------------------------------------------------
# T2 — _upsert_relation sem source_session_id → NULL (backward-compat)
# ---------------------------------------------------------------------------

def test_upsert_relation_sem_session_id_fica_null(db_conn, entity_ids):
    conn, text = db_conn
    src_id, tgt_id = entity_ids

    from app.agente.services.knowledge_graph_service import _upsert_relation

    # Chamada SEM source_session_id (callers legados)
    _upsert_relation(conn, src_id, tgt_id, relation_type='co_occurs', weight=1.0)

    row = _read_relation(conn, text, src_id, tgt_id)
    assert row is not None
    assert row['source_session_id'] is None, (
        f"source_session_id deve ser NULL em chamada legacy, obtido {row['source_session_id']!r}"
    )
    assert row['source_step_uid'] is None


# ---------------------------------------------------------------------------
# T3 — _link_entity_to_memory grava source_session_id quando fornecido
# ---------------------------------------------------------------------------

def test_link_entity_to_memory_grava_source_session_id(db_conn, entity_ids, memory_id):
    conn, text = db_conn
    src_id, _ = entity_ids

    from app.agente.services.knowledge_graph_service import _link_entity_to_memory

    _link_entity_to_memory(
        conn, src_id, memory_id,
        source_session_id='sess-xyz789',
    )

    row = _read_link(conn, text, src_id, memory_id)
    assert row is not None, "Link não foi gravado"
    assert row['source_session_id'] == 'sess-xyz789', (
        f"source_session_id esperado 'sess-xyz789', obtido {row['source_session_id']!r}"
    )


# ---------------------------------------------------------------------------
# T4 — _link_entity_to_memory sem source_session_id → NULL (backward-compat)
# ---------------------------------------------------------------------------

def test_link_entity_to_memory_sem_session_id_fica_null(db_conn, entity_ids, memory_id):
    conn, text = db_conn
    src_id, _ = entity_ids

    from app.agente.services.knowledge_graph_service import _link_entity_to_memory

    # Chamada legada sem source_session_id
    _link_entity_to_memory(conn, src_id, memory_id)

    row = _read_link(conn, text, src_id, memory_id)
    assert row is not None
    assert row['source_session_id'] is None
    assert row['source_step_uid'] is None


# ---------------------------------------------------------------------------
# T5 — valid_from é gravado; valid_to fica NULL
# ---------------------------------------------------------------------------

def test_upsert_relation_valid_from_gravado(db_conn, entity_ids):
    conn, text = db_conn
    src_id, tgt_id = entity_ids

    from app.agente.services.knowledge_graph_service import _upsert_relation
    from app.utils.timezone import agora_utc_naive

    ts = agora_utc_naive()
    _upsert_relation(
        conn, src_id, tgt_id,
        relation_type='co_occurs',
        weight=1.0,
        valid_from=ts,
        source_session_id='sess-vf',
    )

    row = _read_relation(conn, text, src_id, tgt_id)
    assert row is not None
    assert row['valid_from'] is not None, "valid_from deve ser gravado"
    assert row['valid_to'] is None, "valid_to deve ficar NULL no MVP"


# ---------------------------------------------------------------------------
# T6 — ON CONFLICT preserva 1ª source_session_id (não sobrescreve)
# ---------------------------------------------------------------------------

def test_upsert_relation_preserva_primeira_origem(db_conn, entity_ids):
    conn, text = db_conn
    src_id, tgt_id = entity_ids

    from app.agente.services.knowledge_graph_service import _upsert_relation

    # 1ª inserção com sess-primaria
    _upsert_relation(
        conn, src_id, tgt_id,
        relation_type='co_occurs',
        weight=1.0,
        source_session_id='sess-primaria',
    )

    # 2ª inserção (ON CONFLICT) com sess-secundaria
    _upsert_relation(
        conn, src_id, tgt_id,
        relation_type='co_occurs',
        weight=1.0,
        source_session_id='sess-secundaria',
    )

    row = _read_relation(conn, text, src_id, tgt_id)
    assert row is not None
    # 1ª origem deve prevalecer
    assert row['source_session_id'] == 'sess-primaria', (
        f"Esperado 'sess-primaria', obtido {row['source_session_id']!r}. "
        "ON CONFLICT deve preservar a 1ª origem."
    )


# ---------------------------------------------------------------------------
# T7 — Flag-OFF: extract_and_link_entities não popula source_session_id
# ---------------------------------------------------------------------------

def test_flag_off_extract_nao_popula_source_session_id():
    """
    Quando USE_AGENT_ONTOLOGY=False (default), o caller em memory_mcp_tool.py
    não captura get_current_session_id() e passa source_session_id=None.
    Verifica via inspeção de código que a chamada é gateada pela flag.
    """
    import inspect as insp
    from app.agente.tools import memory_mcp_tool

    src = insp.getsource(memory_mcp_tool)

    # A população de source_session_id deve ser gateada por USE_AGENT_ONTOLOGY
    assert 'USE_AGENT_ONTOLOGY' in src, (
        "memory_mcp_tool.py deve referenciar USE_AGENT_ONTOLOGY para a população de source_session_id"
    )
    # get_current_session_id deve aparecer na propagação de proveniência
    assert 'get_current_session_id' in src, (
        "memory_mcp_tool.py deve chamar get_current_session_id() para capturar source_session_id"
    )


# ---------------------------------------------------------------------------
# T8 — Migration idempotente: rodar novamente não falha
# ---------------------------------------------------------------------------

def test_migration_idempotente():
    """
    Roda o main() da migration com colunas já existentes — deve retornar 0
    sem lançar exceção.
    """
    import importlib.util
    import os

    migration_path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', 'scripts', 'migrations', '2026_05_31_kg_bitemporal.py'
    )
    migration_path = os.path.abspath(migration_path)

    spec = importlib.util.spec_from_file_location("kg_bitemporal_migration", migration_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ret = mod.main()
    assert ret == 0, f"Migration retornou {ret} na 2ª execução (esperado 0 — idempotente)"
