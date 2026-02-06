"""
Migration: Criar tabelas recebimento_lf e recebimento_lf_lote
==============================================================

Tabelas para o fluxo de Recebimento LF (La Famiglia -> Nacom Goya).
Processo automatizado: DFe -> PO -> Picking -> Invoice.

Executar:
    source .venv/bin/activate
    python scripts/recebimento/003_add_recebimento_lf_tables.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


SQL_RECEBIMENTO_LF = """
CREATE TABLE IF NOT EXISTS recebimento_lf (
    id SERIAL PRIMARY KEY,

    -- DFe / NF de entrada
    odoo_dfe_id INTEGER NOT NULL,
    numero_nf VARCHAR(50),
    chave_nfe VARCHAR(44),
    cnpj_emitente VARCHAR(20),

    -- PO gerado
    odoo_po_id INTEGER,
    odoo_po_name VARCHAR(50),

    -- Picking gerado
    odoo_picking_id INTEGER,
    odoo_picking_name VARCHAR(50),

    -- Invoice gerada
    odoo_invoice_id INTEGER,
    odoo_invoice_name VARCHAR(50),

    -- Company (FB = 1)
    company_id INTEGER NOT NULL DEFAULT 1,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    fase_atual INTEGER NOT NULL DEFAULT 0,
    etapa_atual INTEGER NOT NULL DEFAULT 0,
    total_etapas INTEGER NOT NULL DEFAULT 18,

    -- Erro e retentativas
    erro_mensagem TEXT,
    tentativas INTEGER NOT NULL DEFAULT 0,
    max_tentativas INTEGER NOT NULL DEFAULT 3,

    -- Job RQ
    job_id VARCHAR(100),

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP,
    usuario VARCHAR(100)
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_recebimento_lf_status ON recebimento_lf (status);
CREATE UNIQUE INDEX IF NOT EXISTS ix_recebimento_lf_odoo_dfe_id ON recebimento_lf (odoo_dfe_id);
CREATE INDEX IF NOT EXISTS ix_recebimento_lf_chave_nfe ON recebimento_lf (chave_nfe);
"""

SQL_RECEBIMENTO_LF_LOTE = """
CREATE TABLE IF NOT EXISTS recebimento_lf_lote (
    id SERIAL PRIMARY KEY,
    recebimento_lf_id INTEGER NOT NULL REFERENCES recebimento_lf(id) ON DELETE CASCADE,

    -- Produto (Odoo)
    odoo_product_id INTEGER NOT NULL,
    odoo_product_name VARCHAR(255),
    odoo_dfe_line_id INTEGER,

    -- CFOP da linha DFe
    cfop VARCHAR(10),

    -- Tipo do preenchimento: 'manual' (CFOP!=1902) ou 'auto' (CFOP=1902)
    tipo VARCHAR(10) NOT NULL,

    -- Lote e quantidade
    lote_nome VARCHAR(100),
    quantidade NUMERIC(15, 3) NOT NULL,
    data_validade DATE,

    -- Tracking do produto
    produto_tracking VARCHAR(20) DEFAULT 'lot',

    -- IDs no Odoo (preenchidos apos processamento)
    odoo_lot_id INTEGER,
    odoo_move_line_id INTEGER,

    -- Status
    processado BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_recebimento_lf_lote_recebimento_id
    ON recebimento_lf_lote (recebimento_lf_id);
"""


def criar_tabelas():
    """Cria tabelas recebimento_lf e recebimento_lf_lote."""
    app = create_app()
    with app.app_context():
        try:
            # Criar recebimento_lf
            print("Criando tabela recebimento_lf...")
            db.session.execute(text(SQL_RECEBIMENTO_LF))
            db.session.commit()
            print("  OK - recebimento_lf criada")

            # Criar recebimento_lf_lote
            print("Criando tabela recebimento_lf_lote...")
            db.session.execute(text(SQL_RECEBIMENTO_LF_LOTE))
            db.session.commit()
            print("  OK - recebimento_lf_lote criada")

            print("\nMigration concluida com sucesso!")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabelas()
