# -*- coding: utf-8 -*-
"""
Script para criar tabelas de extrato bancário localmente.

Uso:
    source venv/bin/activate && python scripts/criar_tabelas_extrato.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    app = create_app()
    with app.app_context():
        try:
            # Criar tabela extrato_lote
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS extrato_lote (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    journal_code VARCHAR(20),
                    journal_id INTEGER,
                    data_inicio DATE,
                    data_fim DATE,
                    total_linhas INTEGER DEFAULT 0,
                    linhas_com_match INTEGER DEFAULT 0,
                    linhas_sem_match INTEGER DEFAULT 0,
                    linhas_conciliadas INTEGER DEFAULT 0,
                    linhas_erro INTEGER DEFAULT 0,
                    valor_total FLOAT DEFAULT 0,
                    status VARCHAR(30) DEFAULT 'IMPORTADO' NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    processado_em TIMESTAMP,
                    processado_por VARCHAR(100)
                )
            """))
            print("Tabela extrato_lote criada com sucesso!")

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_extrato_lote_status ON extrato_lote(status)
            """))

            # Criar tabela extrato_item
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS extrato_item (
                    id SERIAL PRIMARY KEY,
                    lote_id INTEGER NOT NULL REFERENCES extrato_lote(id) ON DELETE CASCADE,
                    statement_line_id INTEGER NOT NULL,
                    move_id INTEGER,
                    move_name VARCHAR(100),
                    credit_line_id INTEGER,
                    data_transacao DATE NOT NULL,
                    valor FLOAT NOT NULL,
                    payment_ref TEXT,
                    tipo_transacao VARCHAR(50),
                    nome_pagador VARCHAR(255),
                    cnpj_pagador VARCHAR(20),
                    journal_id INTEGER,
                    journal_code VARCHAR(20),
                    journal_name VARCHAR(100),
                    status_match VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
                    titulo_id INTEGER,
                    titulo_nf VARCHAR(50),
                    titulo_parcela INTEGER,
                    titulo_valor FLOAT,
                    titulo_vencimento DATE,
                    titulo_cliente VARCHAR(255),
                    matches_candidatos TEXT,
                    match_score INTEGER,
                    match_criterio VARCHAR(100),
                    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
                    aprovado_em TIMESTAMP,
                    aprovado_por VARCHAR(100),
                    status VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
                    mensagem TEXT,
                    partial_reconcile_id INTEGER,
                    full_reconcile_id INTEGER,
                    titulo_saldo_antes FLOAT,
                    titulo_saldo_depois FLOAT,
                    snapshot_antes TEXT,
                    snapshot_depois TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processado_em TIMESTAMP
                )
            """))
            print("Tabela extrato_item criada com sucesso!")

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_extrato_item_lote ON extrato_item(lote_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_extrato_item_status ON extrato_item(status)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_extrato_item_cnpj ON extrato_item(cnpj_pagador)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_extrato_item_statement_line ON extrato_item(statement_line_id)
            """))
            print("Índices criados com sucesso!")

            db.session.commit()
            print("\n=== TABELAS CRIADAS COM SUCESSO! ===")

            # Verificar criação
            result = db.session.execute(text("""
                SELECT 'extrato_lote' as tabela, count(*) as registros FROM extrato_lote
                UNION ALL
                SELECT 'extrato_item' as tabela, count(*) as registros FROM extrato_item
            """))
            for row in result:
                print(f"  {row[0]}: {row[1]} registros")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabelas()
