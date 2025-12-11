# -*- coding: utf-8 -*-
"""
Script para adicionar campos de statement_id à tabela extrato_lote.

Execução local:
    source venv/bin/activate
    python scripts/adicionar_statement_id_extrato_lote.py

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_colunas():
    """Adiciona colunas statement_id, statement_name e data_extrato à tabela extrato_lote."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se colunas já existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'extrato_lote'
                AND column_name IN ('statement_id', 'statement_name', 'data_extrato')
            """))
            colunas_existentes = [row[0] for row in resultado]

            if 'statement_id' not in colunas_existentes:
                print("Adicionando coluna statement_id...")
                db.session.execute(text("""
                    ALTER TABLE extrato_lote
                    ADD COLUMN statement_id INTEGER UNIQUE
                """))
                print("  ✓ statement_id adicionado")
            else:
                print("  - statement_id já existe")

            if 'statement_name' not in colunas_existentes:
                print("Adicionando coluna statement_name...")
                db.session.execute(text("""
                    ALTER TABLE extrato_lote
                    ADD COLUMN statement_name VARCHAR(255)
                """))
                print("  ✓ statement_name adicionado")
            else:
                print("  - statement_name já existe")

            if 'data_extrato' not in colunas_existentes:
                print("Adicionando coluna data_extrato...")
                db.session.execute(text("""
                    ALTER TABLE extrato_lote
                    ADD COLUMN data_extrato DATE
                """))
                print("  ✓ data_extrato adicionado")
            else:
                print("  - data_extrato já existe")

            # Criar índice para statement_id
            print("Criando índice para statement_id...")
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_extrato_lote_statement_id
                    ON extrato_lote (statement_id)
                """))
                print("  ✓ índice criado")
            except Exception as e:
                print(f"  - índice já existe ou erro: {e}")

            db.session.commit()
            print("\n✅ Migração concluída com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro na migração: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_colunas()
