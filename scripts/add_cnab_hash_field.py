"""
Migration: Adicionar campo hash_arquivo para verificação de duplicação

Este script adiciona o campo hash_arquivo à tabela cnab_retorno_lote
para evitar importação duplicada de arquivos CNAB400.

Uso:
    python scripts/add_cnab_hash_field.py

Ou no Render Shell:
    Execute o SQL diretamente (ver função print_sql).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_MIGRATION = """
-- Adicionar campo hash_arquivo para verificação de duplicação
-- Data: 2026-01-20

-- 1. Adicionar campo hash_arquivo (SHA256 = 64 caracteres)
ALTER TABLE cnab_retorno_lote
    ADD COLUMN IF NOT EXISTS hash_arquivo VARCHAR(64);

-- 2. Criar índice único para garantir que não haja duplicação
CREATE UNIQUE INDEX IF NOT EXISTS idx_cnab_lote_hash_unique
    ON cnab_retorno_lote(hash_arquivo)
    WHERE hash_arquivo IS NOT NULL;

-- 3. Criar índice normal para busca rápida
CREATE INDEX IF NOT EXISTS idx_cnab_lote_hash
    ON cnab_retorno_lote(hash_arquivo);
"""


def run_migration():
    """Executa a migration"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Adicionando campo hash_arquivo")
            print("=" * 60)

            # Executar cada comando separadamente para melhor controle de erros
            commands = [
                ("hash_arquivo", "ALTER TABLE cnab_retorno_lote ADD COLUMN IF NOT EXISTS hash_arquivo VARCHAR(64)"),
                ("idx_cnab_lote_hash_unique", "CREATE UNIQUE INDEX IF NOT EXISTS idx_cnab_lote_hash_unique ON cnab_retorno_lote(hash_arquivo) WHERE hash_arquivo IS NOT NULL"),
                ("idx_cnab_lote_hash", "CREATE INDEX IF NOT EXISTS idx_cnab_lote_hash ON cnab_retorno_lote(hash_arquivo)"),
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

            # Verificar se campo foi criado
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cnab_retorno_lote'
                AND column_name = 'hash_arquivo'
            """))
            columns = [row[0] for row in result]

            if 'hash_arquivo' in columns:
                print(f"\n✅ Campo 'hash_arquivo' verificado na tabela")
            else:
                print(f"\n⚠️  Campo 'hash_arquivo' NÃO encontrado - verifique manualmente")

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
