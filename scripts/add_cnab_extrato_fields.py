"""
Migration: Adicionar campos de vinculação CNAB → Extrato

Este script adiciona os campos necessários para vincular itens do CNAB400
com linhas de extrato bancário, permitindo baixa unificada.

Uso:
    python scripts/add_cnab_extrato_fields.py

Ou no Render Shell:
    Execute o SQL diretamente.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_MIGRATION = """
-- Adicionar campos de vinculação CNAB → Extrato
-- Data: 2026-01-20

-- 1. Adicionar FK para extrato_item
ALTER TABLE cnab_retorno_item
    ADD COLUMN IF NOT EXISTS extrato_item_id INTEGER REFERENCES extrato_item(id);

-- 2. Adicionar status do match com extrato
ALTER TABLE cnab_retorno_item
    ADD COLUMN IF NOT EXISTS status_match_extrato VARCHAR(30) DEFAULT 'PENDENTE';

-- 3. Adicionar score do match com extrato
ALTER TABLE cnab_retorno_item
    ADD COLUMN IF NOT EXISTS match_score_extrato INTEGER;

-- 4. Adicionar critério do match com extrato
ALTER TABLE cnab_retorno_item
    ADD COLUMN IF NOT EXISTS match_criterio_extrato VARCHAR(100);

-- 5. Criar índice para busca por extrato_item_id
CREATE INDEX IF NOT EXISTS idx_cnab_item_extrato ON cnab_retorno_item(extrato_item_id);

-- 6. Criar índice para busca por status_match_extrato
CREATE INDEX IF NOT EXISTS idx_cnab_item_status_extrato ON cnab_retorno_item(status_match_extrato);
"""


def run_migration():
    """Executa a migration"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Adicionando campos CNAB → Extrato")
            print("=" * 60)

            # Executar cada comando separadamente para melhor controle de erros
            commands = [
                ("extrato_item_id", "ALTER TABLE cnab_retorno_item ADD COLUMN IF NOT EXISTS extrato_item_id INTEGER REFERENCES extrato_item(id)"),
                ("status_match_extrato", "ALTER TABLE cnab_retorno_item ADD COLUMN IF NOT EXISTS status_match_extrato VARCHAR(30) DEFAULT 'PENDENTE'"),
                ("match_score_extrato", "ALTER TABLE cnab_retorno_item ADD COLUMN IF NOT EXISTS match_score_extrato INTEGER"),
                ("match_criterio_extrato", "ALTER TABLE cnab_retorno_item ADD COLUMN IF NOT EXISTS match_criterio_extrato VARCHAR(100)"),
                ("idx_cnab_item_extrato", "CREATE INDEX IF NOT EXISTS idx_cnab_item_extrato ON cnab_retorno_item(extrato_item_id)"),
                ("idx_cnab_item_status_extrato", "CREATE INDEX IF NOT EXISTS idx_cnab_item_status_extrato ON cnab_retorno_item(status_match_extrato)"),
            ]

            for nome, sql in commands:
                try:
                    db.session.execute(text(sql))
                    print(f"  ✅ {nome}")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"  ⏭️  {nome} (já existe)")
                    else:
                        print(f"  ❌ {nome}: {e}")

            db.session.commit()
            print()
            print("=" * 60)
            print("✅ Migration concluída com sucesso!")
            print("=" * 60)

            # Verificar se campos foram criados
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cnab_retorno_item'
                AND column_name IN ('extrato_item_id', 'status_match_extrato', 'match_score_extrato', 'match_criterio_extrato')
            """))
            columns = [row[0] for row in result]
            print(f"\nCampos verificados: {columns}")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


def print_sql():
    """Imprime o SQL para execução manual"""
    print("=" * 60)
    print("SQL PARA EXECUÇÃO MANUAL (Render Shell)")
    print("=" * 60)
    print(SQL_MIGRATION)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--sql':
        print_sql()
    else:
        run_migration()
