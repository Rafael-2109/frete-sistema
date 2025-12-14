# -*- coding: utf-8 -*-
"""
Script para adicionar campo tipo_transacao na tabela extrato_lote
=================================================================

Execução local:
    source venv/bin/activate && python scripts/migrations/adicionar_tipo_transacao_extrato_lote.py

Execução no Render (Shell):
    Copie e execute o SQL gerado abaixo.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

SQL_MIGRATION = """
-- Adicionar campo tipo_transacao na tabela extrato_lote
ALTER TABLE extrato_lote
ADD COLUMN IF NOT EXISTS tipo_transacao VARCHAR(20) DEFAULT 'entrada' NOT NULL;

-- Criar índice para tipo_transacao
CREATE INDEX IF NOT EXISTS idx_extrato_lote_tipo_transacao ON extrato_lote (tipo_transacao);

-- Atualizar registros existentes para 'entrada' (recebimentos)
UPDATE extrato_lote SET tipo_transacao = 'entrada' WHERE tipo_transacao IS NULL;
"""


def executar_migracao():
    """Executa a migração"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("ADICIONANDO CAMPO tipo_transacao EM extrato_lote")
            print("=" * 60)

            # Executar SQL
            for statement in SQL_MIGRATION.split(';'):
                statement = statement.strip()
                if statement:
                    db.session.execute(text(statement))

            db.session.commit()
            print("✅ Campo tipo_transacao adicionado com sucesso!")

            # Verificar
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'extrato_lote' AND column_name = 'tipo_transacao'"
            ))
            if result.fetchone():
                print("✅ Verificação: Campo existe no banco")
            else:
                print("❌ Erro: Campo não foi criado")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQL PARA EXECUÇÃO MANUAL NO RENDER:")
    print("=" * 60)
    print(SQL_MIGRATION)
    print("=" * 60 + "\n")

    executar_migracao()
