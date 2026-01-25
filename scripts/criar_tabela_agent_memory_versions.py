"""
Script para criar tabela agent_memory_versions.
Histórico de versões das memórias do agente.

Para ambiente de DESENVOLVIMENTO local:
    python scripts/criar_tabela_agent_memory_versions.py

Para ambiente de PRODUÇÃO (Shell do Render):
    Executar o SQL direto no shell (veja final deste arquivo)

Uso:
    python scripts/criar_tabela_agent_memory_versions.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_tabela_existe():
    """Verifica se a tabela já existe"""
    try:
        resultado = db.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'agent_memory_versions'
            );
        """))
        existe = resultado.scalar()
        return existe
    except Exception as e:
        print(f"❌ Erro ao verificar tabela: {e}")
        return False


def criar_tabela():
    """Cria a tabela agent_memory_versions"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔄 CRIANDO TABELA agent_memory_versions")
            print("   (Histórico de versões das memórias do agente)")
            print("=" * 80)

            # Verificar se já existe
            if verificar_tabela_existe():
                print("⚠️  Tabela agent_memory_versions JÁ EXISTE")
                print("    Nenhuma alteração será feita.")
                return True

            # Criar tabela
            print("\n📦 Criando tabela agent_memory_versions...")

            db.session.execute(text("""
                CREATE TABLE agent_memory_versions (
                    id SERIAL PRIMARY KEY,
                    memory_id INTEGER NOT NULL REFERENCES agent_memories(id) ON DELETE CASCADE,
                    content TEXT,
                    version INTEGER NOT NULL,
                    changed_at TIMESTAMP DEFAULT NOW(),
                    changed_by VARCHAR(50),
                    CONSTRAINT uq_memory_version UNIQUE (memory_id, version)
                );
            """))

            # Criar índice
            print("📊 Criando índice idx_memory_version_memory_id...")
            db.session.execute(text("""
                CREATE INDEX idx_memory_version_memory_id
                ON agent_memory_versions (memory_id);
            """))

            # Adicionar comentários
            print("📝 Adicionando comentários...")
            db.session.execute(text("""
                COMMENT ON TABLE agent_memory_versions IS
                'Histórico de versões das memórias do agente. Cada update salva versão anterior.';
            """))
            db.session.execute(text("""
                COMMENT ON COLUMN agent_memory_versions.memory_id IS
                'FK para agent_memories.id - memória versionada';
            """))
            db.session.execute(text("""
                COMMENT ON COLUMN agent_memory_versions.content IS
                'Conteúdo da versão anterior da memória';
            """))
            db.session.execute(text("""
                COMMENT ON COLUMN agent_memory_versions.version IS
                'Número da versão (1, 2, 3...). Incrementa a cada update.';
            """))
            db.session.execute(text("""
                COMMENT ON COLUMN agent_memory_versions.changed_by IS
                'Quem fez a mudança: user, haiku, claude';
            """))

            db.session.commit()

            print("\n" + "=" * 80)
            print("✅ TABELA agent_memory_versions CRIADA COM SUCESSO!")
            print("=" * 80)

            # Verificar estrutura
            print("\n📋 Estrutura da tabela:")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'agent_memory_versions'
                ORDER BY ordinal_position;
            """))
            for row in resultado:
                print(f"   {row[0]:20} {row[1]:15} NULL={row[2]:5} DEFAULT={row[3] or '-'}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao criar tabela: {e}")
            return False


if __name__ == "__main__":
    criar_tabela()


# =============================================================================
# SQL PARA RODAR NO SHELL DO RENDER (Produção)
# =============================================================================
"""
-- Copie e cole este SQL no Shell do Render:

-- 1. Verificar se tabela existe
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'agent_memory_versions'
);

-- 2. Criar tabela (se não existir)
CREATE TABLE IF NOT EXISTS agent_memory_versions (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER NOT NULL REFERENCES agent_memories(id) ON DELETE CASCADE,
    content TEXT,
    version INTEGER NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(50),
    CONSTRAINT uq_memory_version UNIQUE (memory_id, version)
);

-- 3. Criar índice
CREATE INDEX IF NOT EXISTS idx_memory_version_memory_id
ON agent_memory_versions (memory_id);

-- 4. Verificar criação
SELECT * FROM information_schema.columns
WHERE table_name = 'agent_memory_versions';
"""
