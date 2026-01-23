"""
Migration: Criar tabelas para Recebimento Fisico (Fase 4)

Cria 3 tabelas:
- recebimento_fisico: Registro principal do recebimento
- recebimento_lote: Lotes + quantidades por produto
- recebimento_quality_check: Quality checks preenchidos

Uso:
    source .venv/bin/activate && python scripts/create_recebimento_fisico_tables.py

Ou no Render Shell:
    Execute o SQL diretamente (SQL_MIGRATION abaixo).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


SQL_MIGRATION = """
-- =====================================================
-- Fase 4: Recebimento Fisico (Lotes + Quality Check)
-- Data: 2026-01-23
-- =====================================================

-- 1. Tabela principal: recebimento_fisico
CREATE TABLE IF NOT EXISTS recebimento_fisico (
    id SERIAL PRIMARY KEY,

    -- Vinculo com Odoo
    odoo_picking_id INTEGER NOT NULL,
    odoo_picking_name VARCHAR(50),
    odoo_purchase_order_id INTEGER,
    odoo_purchase_order_name VARCHAR(50),
    odoo_partner_id INTEGER,
    odoo_partner_name VARCHAR(255),
    company_id INTEGER NOT NULL,

    -- Vinculo com Validacao NF x PO (Fase 2) - opcional
    validacao_id INTEGER REFERENCES validacao_nf_po_dfe(id),
    numero_nf VARCHAR(50),

    -- Status do processamento
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    erro_mensagem TEXT,
    tentativas INTEGER NOT NULL DEFAULT 0,
    max_tentativas INTEGER NOT NULL DEFAULT 3,

    -- Job RQ
    job_id VARCHAR(100),

    -- Timestamps
    criado_em TIMESTAMP DEFAULT NOW(),
    processado_em TIMESTAMP,
    usuario VARCHAR(100),

    -- Constraints
    CONSTRAINT chk_recebimento_status CHECK (
        status IN ('pendente', 'processando', 'processado', 'erro', 'cancelado')
    )
);

-- Indices para recebimento_fisico
CREATE INDEX IF NOT EXISTS idx_recebimento_fisico_status
    ON recebimento_fisico(status);
CREATE INDEX IF NOT EXISTS idx_recebimento_fisico_picking
    ON recebimento_fisico(odoo_picking_id);
CREATE INDEX IF NOT EXISTS idx_recebimento_fisico_company
    ON recebimento_fisico(company_id);
CREATE INDEX IF NOT EXISTS idx_recebimento_fisico_criado
    ON recebimento_fisico(criado_em DESC);


-- 2. Tabela de lotes: recebimento_lote
CREATE TABLE IF NOT EXISTS recebimento_lote (
    id SERIAL PRIMARY KEY,
    recebimento_id INTEGER NOT NULL REFERENCES recebimento_fisico(id) ON DELETE CASCADE,

    -- Produto
    odoo_product_id INTEGER NOT NULL,
    odoo_product_name VARCHAR(255),
    odoo_move_line_id INTEGER,
    odoo_move_id INTEGER,

    -- Lote
    lote_nome VARCHAR(100) NOT NULL,
    quantidade NUMERIC(15, 3) NOT NULL,
    data_validade DATE,

    -- Tracking
    produto_tracking VARCHAR(20) DEFAULT 'lot',

    -- Status de processamento individual
    processado BOOLEAN NOT NULL DEFAULT FALSE,
    odoo_lot_id INTEGER,
    odoo_move_line_criado_id INTEGER
);

-- Indices para recebimento_lote
CREATE INDEX IF NOT EXISTS idx_recebimento_lote_recebimento
    ON recebimento_lote(recebimento_id);
CREATE INDEX IF NOT EXISTS idx_recebimento_lote_produto
    ON recebimento_lote(odoo_product_id);


-- 3. Tabela de quality checks: recebimento_quality_check
CREATE TABLE IF NOT EXISTS recebimento_quality_check (
    id SERIAL PRIMARY KEY,
    recebimento_id INTEGER NOT NULL REFERENCES recebimento_fisico(id) ON DELETE CASCADE,

    -- Referencia ao check do Odoo
    odoo_check_id INTEGER NOT NULL,
    odoo_point_id INTEGER,
    odoo_product_id INTEGER,

    -- Tipo do check
    test_type VARCHAR(20) NOT NULL,
    titulo VARCHAR(255),

    -- Resultado
    resultado VARCHAR(10) NOT NULL,

    -- Para tipo 'measure'
    valor_medido NUMERIC(15, 4),
    unidade VARCHAR(20),
    tolerancia_min NUMERIC(15, 4),
    tolerancia_max NUMERIC(15, 4),

    -- Status
    processado BOOLEAN NOT NULL DEFAULT FALSE,

    -- Constraints
    CONSTRAINT chk_qc_test_type CHECK (test_type IN ('passfail', 'measure')),
    CONSTRAINT chk_qc_resultado CHECK (resultado IN ('pass', 'fail'))
);

-- Indices para recebimento_quality_check
CREATE INDEX IF NOT EXISTS idx_recebimento_qc_recebimento
    ON recebimento_quality_check(recebimento_id);
CREATE INDEX IF NOT EXISTS idx_recebimento_qc_check
    ON recebimento_quality_check(odoo_check_id);
"""


def executar_migration():
    """Executa a migration para criar tabelas de recebimento fisico."""
    app = create_app()
    with app.app_context():
        try:
            print("Criando tabelas de Recebimento Fisico (Fase 4)...")
            print("=" * 60)

            db.session.execute(text(SQL_MIGRATION))
            db.session.commit()

            print("SUCESSO: Tabelas criadas!")
            print()
            print("Tabelas criadas:")
            print("  - recebimento_fisico")
            print("  - recebimento_lote")
            print("  - recebimento_quality_check")
            print()

            # Verificar criacao
            result = db.session.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('recebimento_fisico', 'recebimento_lote', 'recebimento_quality_check')
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"Verificacao: {len(tables)} tabelas encontradas: {tables}")

            if len(tables) == 3:
                print("OK: Todas as tabelas criadas com sucesso!")
            else:
                print("AVISO: Nem todas as tabelas foram encontradas!")

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
