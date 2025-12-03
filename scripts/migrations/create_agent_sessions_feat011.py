"""
Migração: Criar/Atualizar tabela agent_sessions
FEAT-011: Lista de Sessões

Executar:
    python scripts/migrations/create_agent_sessions_feat011.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_ou_atualizar_tabela():
    """Cria ou atualiza tabela agent_sessions."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se tabela existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'agent_sessions'
                )
            """))
            tabela_existe = result.scalar()

            if not tabela_existe:
                print("📦 Criando tabela agent_sessions...")

                db.session.execute(text("""
                    CREATE TABLE agent_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(100) UNIQUE NOT NULL,
                        user_id INTEGER REFERENCES usuarios(id),

                        -- Campos para UI (FEAT-011)
                        title VARCHAR(200),
                        message_count INTEGER DEFAULT 0,
                        total_cost_usd DECIMAL(10, 6) DEFAULT 0,
                        last_message TEXT,
                        model VARCHAR(100),

                        -- Dados extras
                        data JSONB DEFAULT '{}',

                        -- Timestamps
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # Cria índices
                db.session.execute(text("""
                    CREATE INDEX idx_agent_sessions_user_id ON agent_sessions(user_id)
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_agent_sessions_updated ON agent_sessions(updated_at DESC)
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_agent_sessions_session_id ON agent_sessions(session_id)
                """))

                db.session.commit()
                print("✅ Tabela agent_sessions criada com sucesso!")

            else:
                print("📋 Tabela agent_sessions já existe. Verificando colunas...")

                # Lista de colunas que precisam existir
                colunas_necessarias = [
                    ('title', 'VARCHAR(200)'),
                    ('message_count', 'INTEGER DEFAULT 0'),
                    ('total_cost_usd', 'DECIMAL(10, 6) DEFAULT 0'),
                    ('last_message', 'TEXT'),
                    ('model', 'VARCHAR(100)'),
                ]

                for col_name, col_type in colunas_necessarias:
                    result = db.session.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_name = 'agent_sessions' AND column_name = :col
                        )
                    """), {'col': col_name})

                    if not result.scalar():
                        print(f"  ➕ Adicionando coluna: {col_name}")
                        db.session.execute(text(f'ALTER TABLE agent_sessions ADD COLUMN {col_name} {col_type}'))
                    else:
                        print(f"  ✓ Coluna existe: {col_name}")

                db.session.commit()
                print("✅ Verificação de colunas concluída!")

            # Mostra estrutura final
            print("\n📋 Estrutura final da tabela:")
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'agent_sessions'
                ORDER BY ordinal_position
            """))

            for row in result:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"  {row[0]}: {row[1]} {nullable}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRAÇÃO: agent_sessions (FEAT-011)")
    print("=" * 60)

    if criar_ou_atualizar_tabela():
        print("\n✅ Migração concluída com sucesso!")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)
