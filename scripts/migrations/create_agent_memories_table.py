"""
Migração: Criar tabela agent_memories

Esta tabela implementa a Memory Tool da Anthropic para o Claude Agent SDK.
Armazena memórias persistentes por usuário (fatos, preferências, contexto).

Referência: https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool

Estrutura:
- path: Path virtual do arquivo (ex: /memories/preferences.xml)
- content: Conteúdo do arquivo
- is_directory: Flag para diretórios virtuais
- user_id: Isolamento por usuário

Executar:
    python scripts/migrations/create_agent_memories_table.py

Para Render (SQL Shell):
    -- Veja SQL no final deste arquivo
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_agent_memories():
    """Cria tabela agent_memories no PostgreSQL."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela já existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_memories'
                )
            """))

            if result.scalar():
                print("✅ Tabela agent_memories já existe")
                return True

            # Cria tabela
            print("📦 Criando tabela agent_memories...")

            db.session.execute(text("""
                CREATE TABLE agent_memories (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    path VARCHAR(500) NOT NULL,
                    content TEXT,
                    is_directory BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_user_memory_path UNIQUE (user_id, path)
                )
            """))

            # Cria índices para performance
            print("📦 Criando índices...")

            db.session.execute(text("""
                CREATE INDEX idx_agent_memories_user_id
                ON agent_memories(user_id)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_agent_memories_path
                ON agent_memories(path)
            """))

            # Índice para busca por path com LIKE (usado em list_directory)
            db.session.execute(text("""
                CREATE INDEX idx_agent_memories_path_pattern
                ON agent_memories(path varchar_pattern_ops)
            """))

            db.session.commit()
            print("✅ Tabela agent_memories criada com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar tabela: {e}")
            return False


def verificar_tabela():
    """Verifica estrutura da tabela."""
    app = create_app()

    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'agent_memories'
                ORDER BY ordinal_position
            """))

            print("\n📋 Estrutura da tabela agent_memories:")
            print("-" * 50)

            for row in result:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"  {row[0]}: {row[1]} {nullable}")

            # Verifica índices
            result_idx = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'agent_memories'
            """))

            print("\n📋 Índices:")
            print("-" * 50)
            for row in result_idx:
                print(f"  {row[0]}")

            return True

        except Exception as e:
            print(f"❌ Erro ao verificar tabela: {e}")
            return False


def mostrar_sql_render():
    """Mostra SQL para executar no Render Shell."""
    sql = """
-- =============================================================================
-- SQL PARA EXECUTAR NO RENDER SHELL (se não puder rodar o script Python)
-- =============================================================================

-- 1. Criar tabela
CREATE TABLE IF NOT EXISTS agent_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    path VARCHAR(500) NOT NULL,
    content TEXT,
    is_directory BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_memory_path UNIQUE (user_id, path)
);

-- 2. Criar índices
CREATE INDEX IF NOT EXISTS idx_agent_memories_user_id
ON agent_memories(user_id);

CREATE INDEX IF NOT EXISTS idx_agent_memories_path
ON agent_memories(path);

CREATE INDEX IF NOT EXISTS idx_agent_memories_path_pattern
ON agent_memories(path varchar_pattern_ops);

-- 3. Verificar criação
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agent_memories';
"""
    print(sql)


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRAÇÃO: Criar tabela agent_memories (Memory Tool)")
    print("=" * 60)

    if '--sql' in sys.argv:
        mostrar_sql_render()
    else:
        if criar_tabela_agent_memories():
            verificar_tabela()
        else:
            print("\n⚠️ Migração falhou. Verifique os logs acima.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Migração concluída!")
    print("=" * 60)
