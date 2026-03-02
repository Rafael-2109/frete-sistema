"""
Migration: Criar tabela carvia_despesas
========================================

Cria tabela para despesas operacionais do modulo CarVia.

Executar: python scripts/migrations/criar_tabela_carvia_despesas.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def criar_tabela():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        tabelas_antes = set(inspector.get_table_names())

        if 'carvia_despesas' in tabelas_antes:
            print("Tabela carvia_despesas ja existe. Migration ja foi executada.")
            return

        print("Criando tabela carvia_despesas...")

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS carvia_despesas (
                id SERIAL PRIMARY KEY,
                tipo_despesa VARCHAR(50) NOT NULL,
                descricao VARCHAR(500),
                valor NUMERIC(15, 2) NOT NULL,
                data_despesa DATE NOT NULL,
                data_vencimento DATE,
                status VARCHAR(20) DEFAULT 'PENDENTE',
                observacoes TEXT,
                criado_por VARCHAR(150),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Indices
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_despesas_tipo_despesa
            ON carvia_despesas (tipo_despesa);
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_despesas_status
            ON carvia_despesas (status);
        """))

        db.session.commit()

        # Verificacao
        inspector = inspect(db.engine)
        tabelas_depois = set(inspector.get_table_names())

        if 'carvia_despesas' in tabelas_depois:
            colunas = [c['name'] for c in inspector.get_columns('carvia_despesas')]
            print(f"Tabela carvia_despesas criada com {len(colunas)} colunas: {colunas}")
        else:
            print("ERRO: Tabela carvia_despesas NAO foi criada!")


if __name__ == '__main__':
    criar_tabela()
