# -*- coding: utf-8 -*-
"""
Script de migração para adicionar campo batch_id na tabela cnab_retorno_lote.

O campo batch_id permite agrupar múltiplos arquivos CNAB enviados
em um único upload para processamento assíncrono.

Uso:
    # Local
    python scripts/migrations/add_batch_id_cnab_lote.py

    # Render Shell (executar SQL diretamente)
    # Ver SQL no final deste arquivo
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_batch_id():
    """Adiciona campo batch_id na tabela cnab_retorno_lote."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cnab_retorno_lote'
                AND column_name = 'batch_id';
            """))
            exists = result.fetchone()

            if exists:
                print("✅ Campo batch_id já existe na tabela cnab_retorno_lote")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE cnab_retorno_lote
                ADD COLUMN batch_id VARCHAR(36);
            """))
            print("✅ Campo batch_id adicionado")

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_cnab_retorno_lote_batch_id
                ON cnab_retorno_lote(batch_id);
            """))
            print("✅ Índice ix_cnab_retorno_lote_batch_id criado")

            db.session.commit()
            print("\n🎉 Migração concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


def verificar_campo():
    """Verifica se o campo batch_id foi criado corretamente."""
    app = create_app()
    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'cnab_retorno_lote'
                AND column_name = 'batch_id';
            """))
            row = result.fetchone()

            if row:
                print(f"✅ Campo encontrado: {row[0]} ({row[1]}, nullable={row[2]})")
            else:
                print("⚠️ Campo batch_id não encontrado na tabela cnab_retorno_lote")

        except Exception as e:
            print(f"❌ Erro ao verificar: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Migração batch_id CNAB')
    parser.add_argument('--check', action='store_true', help='Apenas verifica se campo existe')
    args = parser.parse_args()

    if args.check:
        verificar_campo()
    else:
        adicionar_batch_id()
        verificar_campo()


# =============================================================================
# SQL PARA RENDER SHELL
# =============================================================================
"""
-- Copie e cole no Render Shell do PostgreSQL:

ALTER TABLE cnab_retorno_lote ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36);
CREATE INDEX IF NOT EXISTS ix_cnab_retorno_lote_batch_id ON cnab_retorno_lote(batch_id);
"""
