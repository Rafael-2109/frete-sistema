"""
Migração: Criar tabela agent_sessions

Esta tabela armazena sessões do Agente SDK com:
- Dados da sessão em JSONB
- Índices para busca por usuário e data
- Timestamps automáticos

Executar:
    python scripts/migrations/create_agent_sessions_table.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_agent_sessions():
    """Cria tabela agent_sessions no PostgreSQL."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela já existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_sessions'
                )
            """))

            if result.scalar():
                print("✅ Tabela agent_sessions já existe")
                return True

            # Cria tabela
            print("📦 Criando tabela agent_sessions...")

            db.session.execute(text("""
                CREATE TABLE agent_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) UNIQUE NOT NULL,
                    user_id INTEGER,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Cria índices
            print("📦 Criando índices...")

            db.session.execute(text("""
                CREATE INDEX idx_agent_sessions_user_id
                ON agent_sessions(user_id)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_agent_sessions_updated
                ON agent_sessions(updated_at)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_agent_sessions_data_gin
                ON agent_sessions USING gin(data)
            """))

            db.session.commit()
            print("✅ Tabela agent_sessions criada com sucesso!")
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
                WHERE table_name = 'agent_sessions'
                ORDER BY ordinal_position
            """))

            print("\n📋 Estrutura da tabela agent_sessions:")
            print("-" * 50)

            for row in result:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"  {row[0]}: {row[1]} {nullable}")

            return True

        except Exception as e:
            print(f"❌ Erro ao verificar tabela: {e}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRAÇÃO: Criar tabela agent_sessions")
    print("=" * 60)

    if criar_tabela_agent_sessions():
        verificar_tabela()
    else:
        print("\n⚠️ Migração falhou. Verifique os logs acima.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Migração concluída!")
    print("=" * 60)
