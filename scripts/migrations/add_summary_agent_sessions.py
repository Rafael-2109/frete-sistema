"""
Migracao: Adicionar campos de summary a tabela agent_sessions
P0-2: Sumarizacao Estruturada de Sessoes

Adiciona 3 colunas:
- summary (JSONB) - Resumo estruturado gerado pelo Haiku
- summary_updated_at (TIMESTAMP) - Quando o summary foi gerado
- summary_message_count (INTEGER) - message_count quando o summary foi gerado

Executar:
    python scripts/migrations/add_summary_agent_sessions.py

Para Render Shell (SQL direto):
    python scripts/migrations/add_summary_agent_sessions.py --sql
"""

import sys
import os

# Adiciona o diretorio raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campos_summary():
    """Adiciona campos de summary a tabela agent_sessions."""
    app = create_app()

    with app.app_context():
        try:
            # Lista de colunas a adicionar
            colunas = [
                ('summary', 'JSONB DEFAULT NULL'),
                ('summary_updated_at', 'TIMESTAMP DEFAULT NULL'),
                ('summary_message_count', 'INTEGER DEFAULT 0'),
            ]

            alteracoes = 0

            for col_name, col_type in colunas:
                # Verifica se coluna ja existe
                result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'agent_sessions' AND column_name = :col
                    )
                """), {'col': col_name})

                if result.scalar():
                    print(f"  ✓ Coluna ja existe: {col_name}")
                else:
                    print(f"  ➕ Adicionando coluna: {col_name} ({col_type})")
                    db.session.execute(text(
                        f'ALTER TABLE agent_sessions ADD COLUMN {col_name} {col_type}'
                    ))
                    alteracoes += 1

            db.session.commit()

            if alteracoes > 0:
                print(f"\n✅ {alteracoes} coluna(s) adicionada(s) com sucesso!")
            else:
                print("\n✅ Todas as colunas ja existiam. Nada a fazer.")

            # Mostra estrutura dos campos de summary
            print("\n📋 Campos de summary na tabela:")
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'agent_sessions'
                AND column_name IN ('summary', 'summary_updated_at', 'summary_message_count')
                ORDER BY ordinal_position
            """))

            for row in result:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                default = f" DEFAULT {row[3]}" if row[3] else ""
                print(f"  {row[0]}: {row[1]} {nullable}{default}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")
            return False


def mostrar_sql_render():
    """Mostra SQL para executar diretamente no Render Shell."""
    sql = """
-- ============================================================
-- P0-2: Adicionar campos de summary a agent_sessions
-- Executar no Render Shell (psql)
-- ============================================================

ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS summary JSONB DEFAULT NULL;
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS summary_updated_at TIMESTAMP DEFAULT NULL;
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS summary_message_count INTEGER DEFAULT 0;

-- Verificar resultado
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'agent_sessions'
AND column_name IN ('summary', 'summary_updated_at', 'summary_message_count')
ORDER BY ordinal_position;
"""
    print(sql)


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: summary em agent_sessions (P0-2)")
    print("=" * 60)

    if '--sql' in sys.argv:
        mostrar_sql_render()
    else:
        if adicionar_campos_summary():
            print("\n✅ Migracao concluida com sucesso!")
        else:
            print("\n❌ Migracao falhou!")
            sys.exit(1)
