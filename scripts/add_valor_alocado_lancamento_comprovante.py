# -*- coding: utf-8 -*-
"""
Migration: Adicionar campo valor_alocado à tabela lancamento_comprovante
========================================================================

Suporte a Multi-NF: 1 comprovante → N títulos.
Quando um boleto agrupa 2+ NFs, valor_alocado indica quanto do comprovante
vai para cada título individualmente.

NULL = comportamento antigo (1:1, valor total do comprovante = 1 título).

Executar:
    python scripts/add_valor_alocado_lancamento_comprovante.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_valor_alocado():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'lancamento_comprovante'
                  AND column_name = 'valor_alocado'
            """))
            if resultado.fetchone():
                print("Coluna 'valor_alocado' já existe. Nenhuma alteração necessária.")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE lancamento_comprovante
                ADD COLUMN valor_alocado NUMERIC(15, 2) NULL
            """))
            db.session.commit()
            print("Coluna 'valor_alocado' adicionada com sucesso à tabela lancamento_comprovante.")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


# SQL para execução direta no Render Shell:
# ALTER TABLE lancamento_comprovante ADD COLUMN valor_alocado NUMERIC(15, 2) NULL;

if __name__ == '__main__':
    adicionar_valor_alocado()
