# -*- coding: utf-8 -*-
"""
Script de migração para criar tabelas de baixa de pagamentos.

Tabelas criadas:
- baixa_pagamento_lote
- baixa_pagamento_item

Executar:
    python scripts/migrations/criar_tabelas_baixa_pagamentos.py

Autor: Sistema de Fretes
Data: 2025-12-13
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas de baixa de pagamentos."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabelas já existem
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'baixa_pagamento_lote'
                )
            """))
            existe = result.scalar()

            if existe:
                print("⚠️ Tabelas já existem. Pulando criação.")
                return True

            print("🔨 Criando tabelas de baixa de pagamentos...")

            # Criar tabela baixa_pagamento_lote
            db.session.execute(text("""
                CREATE TABLE baixa_pagamento_lote (
                    id SERIAL PRIMARY KEY,

                    -- Referência ao extrato
                    extrato_lote_id INTEGER REFERENCES extrato_lote(id),

                    -- Identificação
                    nome VARCHAR(255) NOT NULL,
                    descricao TEXT,

                    -- Journal/Conta bancária
                    journal_id INTEGER,
                    journal_code VARCHAR(20),
                    journal_name VARCHAR(100),

                    -- Período
                    data_inicio DATE,
                    data_fim DATE,

                    -- Estatísticas
                    total_linhas INTEGER DEFAULT 0,
                    linhas_com_match INTEGER DEFAULT 0,
                    linhas_sem_match INTEGER DEFAULT 0,
                    linhas_aprovadas INTEGER DEFAULT 0,
                    linhas_processadas INTEGER DEFAULT 0,
                    linhas_sucesso INTEGER DEFAULT 0,
                    linhas_erro INTEGER DEFAULT 0,
                    valor_total FLOAT DEFAULT 0,

                    -- Status
                    status VARCHAR(30) DEFAULT 'IMPORTADO' NOT NULL,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    processado_em TIMESTAMP,
                    processado_por VARCHAR(100)
                )
            """))
            print("   ✅ Tabela baixa_pagamento_lote criada")

            # Criar índices para baixa_pagamento_lote
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_lote_status ON baixa_pagamento_lote(status)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_lote_extrato ON baixa_pagamento_lote(extrato_lote_id)
            """))
            print("   ✅ Índices da tabela lote criados")

            # Criar tabela baixa_pagamento_item
            db.session.execute(text("""
                CREATE TABLE baixa_pagamento_item (
                    id SERIAL PRIMARY KEY,

                    -- FK para lote
                    lote_id INTEGER NOT NULL REFERENCES baixa_pagamento_lote(id) ON DELETE CASCADE,

                    -- Dados do extrato
                    statement_line_id INTEGER,
                    move_id_extrato INTEGER,
                    data_transacao DATE NOT NULL,
                    valor FLOAT NOT NULL,
                    payment_ref TEXT,
                    tipo_transacao VARCHAR(50),
                    nome_beneficiario VARCHAR(255),
                    cnpj_beneficiario VARCHAR(20),
                    debit_line_id_extrato INTEGER,

                    -- Matching - Título vinculado
                    status_match VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
                    titulo_id INTEGER,
                    titulo_move_id INTEGER,
                    titulo_move_name VARCHAR(100),
                    titulo_nf VARCHAR(50),
                    titulo_parcela INTEGER,
                    titulo_valor FLOAT,
                    titulo_vencimento DATE,
                    partner_id INTEGER,
                    partner_name VARCHAR(255),
                    company_id INTEGER,
                    match_score INTEGER,
                    match_criterio VARCHAR(100),
                    matches_candidatos TEXT,

                    -- Aprovação
                    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
                    aprovado_em TIMESTAMP,
                    aprovado_por VARCHAR(100),

                    -- Controle
                    status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
                    mensagem TEXT,

                    -- Resultado Odoo
                    payment_id INTEGER,
                    payment_name VARCHAR(100),
                    debit_line_id_payment INTEGER,
                    credit_line_id_payment INTEGER,
                    partial_reconcile_titulo_id INTEGER,
                    full_reconcile_titulo_id INTEGER,
                    partial_reconcile_extrato_id INTEGER,
                    full_reconcile_extrato_id INTEGER,
                    saldo_antes FLOAT,
                    saldo_depois FLOAT,

                    -- Snapshots
                    snapshot_antes TEXT,
                    snapshot_depois TEXT,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processado_em TIMESTAMP
                )
            """))
            print("   ✅ Tabela baixa_pagamento_item criada")

            # Criar índices para baixa_pagamento_item
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_lote ON baixa_pagamento_item(lote_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_status ON baixa_pagamento_item(status)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_status_match ON baixa_pagamento_item(status_match)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_cnpj ON baixa_pagamento_item(cnpj_beneficiario)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_titulo ON baixa_pagamento_item(titulo_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_baixa_pag_item_statement ON baixa_pagamento_item(statement_line_id)
            """))
            print("   ✅ Índices da tabela item criados")

            db.session.commit()
            print("\n✅ Todas as tabelas criadas com sucesso!")
            return True

        except Exception as e:
            print(f"\n❌ Erro ao criar tabelas: {e}")
            db.session.rollback()
            return False


def gerar_sql():
    """Gera o SQL para execução manual no Render."""
    sql = """
-- =============================================================================
-- BAIXA DE PAGAMENTOS - Criação de Tabelas
-- Executar no Shell do Render (psql)
-- =============================================================================

-- Tabela de lotes
CREATE TABLE IF NOT EXISTS baixa_pagamento_lote (
    id SERIAL PRIMARY KEY,
    extrato_lote_id INTEGER REFERENCES extrato_lote(id),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    journal_id INTEGER,
    journal_code VARCHAR(20),
    journal_name VARCHAR(100),
    data_inicio DATE,
    data_fim DATE,
    total_linhas INTEGER DEFAULT 0,
    linhas_com_match INTEGER DEFAULT 0,
    linhas_sem_match INTEGER DEFAULT 0,
    linhas_aprovadas INTEGER DEFAULT 0,
    linhas_processadas INTEGER DEFAULT 0,
    linhas_sucesso INTEGER DEFAULT 0,
    linhas_erro INTEGER DEFAULT 0,
    valor_total FLOAT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'IMPORTADO' NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    processado_em TIMESTAMP,
    processado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_baixa_pag_lote_status ON baixa_pagamento_lote(status);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_lote_extrato ON baixa_pagamento_lote(extrato_lote_id);

-- Tabela de itens
CREATE TABLE IF NOT EXISTS baixa_pagamento_item (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES baixa_pagamento_lote(id) ON DELETE CASCADE,
    statement_line_id INTEGER,
    move_id_extrato INTEGER,
    data_transacao DATE NOT NULL,
    valor FLOAT NOT NULL,
    payment_ref TEXT,
    tipo_transacao VARCHAR(50),
    nome_beneficiario VARCHAR(255),
    cnpj_beneficiario VARCHAR(20),
    debit_line_id_extrato INTEGER,
    status_match VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
    titulo_id INTEGER,
    titulo_move_id INTEGER,
    titulo_move_name VARCHAR(100),
    titulo_nf VARCHAR(50),
    titulo_parcela INTEGER,
    titulo_valor FLOAT,
    titulo_vencimento DATE,
    partner_id INTEGER,
    partner_name VARCHAR(255),
    company_id INTEGER,
    match_score INTEGER,
    match_criterio VARCHAR(100),
    matches_candidatos TEXT,
    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
    aprovado_em TIMESTAMP,
    aprovado_por VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
    mensagem TEXT,
    payment_id INTEGER,
    payment_name VARCHAR(100),
    debit_line_id_payment INTEGER,
    credit_line_id_payment INTEGER,
    partial_reconcile_titulo_id INTEGER,
    full_reconcile_titulo_id INTEGER,
    partial_reconcile_extrato_id INTEGER,
    full_reconcile_extrato_id INTEGER,
    saldo_antes FLOAT,
    saldo_depois FLOAT,
    snapshot_antes TEXT,
    snapshot_depois TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_lote ON baixa_pagamento_item(lote_id);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_status ON baixa_pagamento_item(status);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_status_match ON baixa_pagamento_item(status_match);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_cnpj ON baixa_pagamento_item(cnpj_beneficiario);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_titulo ON baixa_pagamento_item(titulo_id);
CREATE INDEX IF NOT EXISTS idx_baixa_pag_item_statement ON baixa_pagamento_item(statement_line_id);
"""
    print(sql)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas de baixa de pagamentos')
    parser.add_argument('--sql', action='store_true', help='Apenas gerar SQL (não executar)')
    args = parser.parse_args()

    if args.sql:
        gerar_sql()
    else:
        criar_tabelas()
