"""
Migration: Criar tabelas do Knowledge Graph para memórias do agente.

T3-3: Knowledge Graph Simplificado — 3 tabelas novas:
  - agent_memory_entities: Nós do grafo (entidades canônicas)
  - agent_memory_entity_links: Entidade <-> Memória
  - agent_memory_entity_relations: Entidade <-> Entidade

Executar:
    source .venv/bin/activate
    python scripts/migrations/criar_tabelas_knowledge_graph.py

Verificar:
    python scripts/migrations/criar_tabelas_knowledge_graph.py --verificar
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def _execute_safe(engine, sql_str, description):
    """Executa SQL em transação isolada. Retorna True se sucesso."""
    try:
        with engine.begin() as conn:
            conn.execute(text(sql_str))
        print(f"   {description}: OK")
        return True
    except Exception as e:
        print(f"   {description}: FALHOU — {e}")
        return False


def _table_exists(conn, table_name):
    """Verifica se tabela existe."""
    result = conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :table_name
    """), {"table_name": table_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name):
    """Verifica se índice existe."""
    result = conn.execute(text("""
        SELECT 1 FROM pg_indexes
        WHERE indexname = :index_name
    """), {"index_name": index_name})
    return result.fetchone() is not None


def _constraint_exists(conn, constraint_name):
    """Verifica se constraint existe."""
    result = conn.execute(text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = :constraint_name
    """), {"constraint_name": constraint_name})
    return result.fetchone() is not None


def _count_rows(conn, table_name):
    """Conta registros em tabela."""
    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


# =========================================================================
# SQL DE CRIAÇÃO
# =========================================================================

SQL_CREATE_ENTITIES = """
CREATE TABLE IF NOT EXISTS agent_memory_entities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_name VARCHAR(200) NOT NULL,
    entity_key VARCHAR(100),
    mention_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_entity UNIQUE(user_id, entity_type, entity_name)
);
"""

SQL_CREATE_LINKS = """
CREATE TABLE IF NOT EXISTS agent_memory_entity_links (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES agent_memories(id) ON DELETE CASCADE,
    relation_type VARCHAR(30) NOT NULL DEFAULT 'mentions',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entity_memory_link UNIQUE(entity_id, memory_id, relation_type)
);
"""

SQL_CREATE_RELATIONS = """
CREATE TABLE IF NOT EXISTS agent_memory_entity_relations (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES agent_memory_entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL DEFAULT 'co_occurs',
    weight FLOAT NOT NULL DEFAULT 1.0,
    memory_id INTEGER REFERENCES agent_memories(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entity_relation UNIQUE(source_entity_id, target_entity_id, relation_type)
);
"""

SQL_INDEXES = [
    ("idx_ame_user_type", "CREATE INDEX IF NOT EXISTS idx_ame_user_type ON agent_memory_entities(user_id, entity_type);"),
    ("idx_ame_entity_key", "CREATE INDEX IF NOT EXISTS idx_ame_entity_key ON agent_memory_entities(entity_key) WHERE entity_key IS NOT NULL;"),
    ("idx_amel_entity", "CREATE INDEX IF NOT EXISTS idx_amel_entity ON agent_memory_entity_links(entity_id);"),
    ("idx_amel_memory", "CREATE INDEX IF NOT EXISTS idx_amel_memory ON agent_memory_entity_links(memory_id);"),
    ("idx_amer_source", "CREATE INDEX IF NOT EXISTS idx_amer_source ON agent_memory_entity_relations(source_entity_id);"),
    ("idx_amer_target", "CREATE INDEX IF NOT EXISTS idx_amer_target ON agent_memory_entity_relations(target_entity_id);"),
]


def migrate():
    """Executa migration: cria tabelas e índices."""
    app = create_app()

    with app.app_context():
        engine = db.engine
        ok_count = 0
        fail_count = 0

        print("\n=== T3-3: Knowledge Graph — Criando tabelas ===\n")

        # 1. Tabela de entidades
        if _execute_safe(engine, SQL_CREATE_ENTITIES, "Tabela agent_memory_entities"):
            ok_count += 1
        else:
            fail_count += 1

        # 2. Tabela de links
        if _execute_safe(engine, SQL_CREATE_LINKS, "Tabela agent_memory_entity_links"):
            ok_count += 1
        else:
            fail_count += 1

        # 3. Tabela de relações
        if _execute_safe(engine, SQL_CREATE_RELATIONS, "Tabela agent_memory_entity_relations"):
            ok_count += 1
        else:
            fail_count += 1

        # 4. Índices
        print("\n--- Índices ---")
        for idx_name, idx_sql in SQL_INDEXES:
            if _execute_safe(engine, idx_sql, f"Índice {idx_name}"):
                ok_count += 1
            else:
                fail_count += 1

        print(f"\n=== Resultado: {ok_count} OK, {fail_count} falhas ===\n")
        return fail_count == 0


def verificar():
    """Verifica se tabelas e índices foram criados corretamente."""
    app = create_app()

    with app.app_context():
        with db.engine.connect() as conn:
            print("\n=== T3-3: Knowledge Graph — Verificação ===\n")

            # Tabelas
            tables = [
                'agent_memory_entities',
                'agent_memory_entity_links',
                'agent_memory_entity_relations',
            ]
            for table in tables:
                exists = _table_exists(conn, table)
                count = _count_rows(conn, table) if exists else 0
                status = "OK" if exists else "NAO EXISTE"
                print(f"  Tabela {table}: {status} ({count} registros)")

            # Constraints
            print()
            constraints = [
                'uq_user_entity',
                'uq_entity_memory_link',
                'uq_entity_relation',
            ]
            for constraint in constraints:
                exists = _constraint_exists(conn, constraint)
                status = "OK" if exists else "NAO EXISTE"
                print(f"  Constraint {constraint}: {status}")

            # Índices
            print()
            indexes = [idx_name for idx_name, _ in SQL_INDEXES]
            for idx in indexes:
                exists = _index_exists(conn, idx)
                status = "OK" if exists else "NAO EXISTE"
                print(f"  Índice {idx}: {status}")

            # FKs
            print()
            fk_check = conn.execute(text("""
                SELECT tc.constraint_name, tc.table_name, kcu.column_name,
                       ccu.table_name AS foreign_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name IN (
                        'agent_memory_entity_links',
                        'agent_memory_entity_relations'
                    )
                ORDER BY tc.table_name, tc.constraint_name
            """))
            fks = fk_check.fetchall()
            if fks:
                print("  Foreign Keys:")
                for fk in fks:
                    print(f"    {fk[1]}.{fk[2]} → {fk[3]} ({fk[0]})")
            else:
                print("  Foreign Keys: NENHUMA ENCONTRADA")

            print("\n=== Verificação concluída ===\n")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--verificar':
        verificar()
    else:
        success = migrate()
        if success:
            print("Migration executada com sucesso. Execute --verificar para confirmar.")
        else:
            print("ERRO: Migration teve falhas. Verifique o log acima.")
            sys.exit(1)
