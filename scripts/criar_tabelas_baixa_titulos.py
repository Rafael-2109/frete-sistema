#!/usr/bin/env python3
"""
Script para criar as tabelas de Baixa de Titulos via Excel.

Tabelas criadas:
- baixa_titulo_lote: Lotes de importacao
- baixa_titulo_item: Itens individuais de baixa

Uso:
    python scripts/criar_tabelas_baixa_titulos.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas de baixa de titulos"""
    app = create_app()
    with app.app_context():
        try:
            # SQL para criar tabela baixa_titulo_lote
            sql_lote = """
            CREATE TABLE IF NOT EXISTS baixa_titulo_lote (
                id SERIAL PRIMARY KEY,
                nome_arquivo VARCHAR(255) NOT NULL,
                hash_arquivo VARCHAR(64),
                total_linhas INTEGER DEFAULT 0,
                linhas_validas INTEGER DEFAULT 0,
                linhas_invalidas INTEGER DEFAULT 0,
                linhas_processadas INTEGER DEFAULT 0,
                linhas_sucesso INTEGER DEFAULT 0,
                linhas_erro INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'IMPORTADO' NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100),
                processado_em TIMESTAMP,
                processado_por VARCHAR(100)
            );

            CREATE INDEX IF NOT EXISTS idx_baixa_lote_status ON baixa_titulo_lote(status);
            """

            # SQL para criar tabela baixa_titulo_item
            sql_item = """
            CREATE TABLE IF NOT EXISTS baixa_titulo_item (
                id SERIAL PRIMARY KEY,
                lote_id INTEGER NOT NULL REFERENCES baixa_titulo_lote(id) ON DELETE CASCADE,
                linha_excel INTEGER NOT NULL,

                -- Dados do Excel
                nf_excel VARCHAR(50) NOT NULL,
                parcela_excel INTEGER NOT NULL,
                valor_excel FLOAT NOT NULL,
                journal_excel VARCHAR(100) NOT NULL,
                data_excel DATE NOT NULL,

                -- Dados resolvidos do Odoo
                titulo_odoo_id INTEGER,
                move_odoo_id INTEGER,
                move_odoo_name VARCHAR(100),
                partner_odoo_id INTEGER,
                journal_odoo_id INTEGER,
                journal_odoo_code VARCHAR(20),
                valor_titulo_odoo FLOAT,
                saldo_antes FLOAT,

                -- Controle
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
                mensagem TEXT,

                -- Resultado da operacao no Odoo
                payment_odoo_id INTEGER,
                payment_odoo_name VARCHAR(100),
                partial_reconcile_id INTEGER,
                saldo_depois FLOAT,

                -- Snapshots
                snapshot_antes TEXT,
                snapshot_depois TEXT,
                campos_alterados TEXT,

                -- Auditoria
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validado_em TIMESTAMP,
                processado_em TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_baixa_item_lote ON baixa_titulo_item(lote_id);
            CREATE INDEX IF NOT EXISTS idx_baixa_item_status ON baixa_titulo_item(status);
            CREATE INDEX IF NOT EXISTS idx_baixa_item_nf ON baixa_titulo_item(nf_excel);
            """

            print("=" * 60)
            print("CRIANDO TABELAS DE BAIXA DE TITULOS")
            print("=" * 60)

            # Executar criacao da tabela lote
            print("\n1. Criando tabela baixa_titulo_lote...")
            db.session.execute(text(sql_lote))
            db.session.commit()
            print("   OK - Tabela baixa_titulo_lote criada!")

            # Executar criacao da tabela item
            print("\n2. Criando tabela baixa_titulo_item...")
            db.session.execute(text(sql_item))
            db.session.commit()
            print("   OK - Tabela baixa_titulo_item criada!")

            # Verificar se as tabelas existem
            print("\n3. Verificando tabelas...")
            result = db.session.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('baixa_titulo_lote', 'baixa_titulo_item')
                ORDER BY table_name;
            """))
            tabelas = [row[0] for row in result]

            for tabela in tabelas:
                print(f"   OK - Tabela {tabela} existe!")

            print("\n" + "=" * 60)
            print("TABELAS CRIADAS COM SUCESSO!")
            print("=" * 60)

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabelas()
