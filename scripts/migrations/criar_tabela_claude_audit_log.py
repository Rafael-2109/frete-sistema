#!/usr/bin/env python3
"""
Migração: Criar tabela claude_audit_log

Esta tabela armazena logs de auditoria das operações do Claude Code,
incluindo separações, notificações e outras alterações importantes.

Uso:
    python scripts/migrations/criar_tabela_claude_audit_log.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria a tabela claude_audit_log no banco de dados."""
    app = create_app()
    with app.app_context():
        try:
            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS claude_audit_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    tool VARCHAR(50),
                    file_path TEXT,
                    user_name VARCHAR(100),
                    session_id VARCHAR(100),
                    operation_type VARCHAR(50),
                    details JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            print("✓ Tabela claude_audit_log criada/verificada")

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_audit_timestamp
                ON claude_audit_log(timestamp DESC);
            """))
            print("✓ Índice idx_claude_audit_timestamp criado/verificado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_audit_operation_type
                ON claude_audit_log(operation_type);
            """))
            print("✓ Índice idx_claude_audit_operation_type criado/verificado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_audit_file_path
                ON claude_audit_log(file_path);
            """))
            print("✓ Índice idx_claude_audit_file_path criado/verificado")

            # Adicionar comentários na tabela
            db.session.execute(text("""
                COMMENT ON TABLE claude_audit_log IS
                'Logs de auditoria das operações do Claude Code (hooks)';
            """))

            db.session.execute(text("""
                COMMENT ON COLUMN claude_audit_log.operation_type IS
                'Tipo: separacao, notificacao_info, notificacao_warning, notificacao_critical';
            """))

            db.session.commit()
            print("\n✅ Migração concluída com sucesso!")

            # Mostrar estrutura criada
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'claude_audit_log'
                ORDER BY ordinal_position;
            """))

            print("\n📋 Estrutura da tabela:")
            print("-" * 50)
            for row in result:
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                print(f"  {row[0]:<20} {row[1]:<20} {nullable}")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False

    return True


if __name__ == "__main__":
    criar_tabela()
