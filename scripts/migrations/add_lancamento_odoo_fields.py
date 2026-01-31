# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos de lançamento Odoo ao lancamento_comprovante
========================================================================

Novos campos para suportar o fluxo CONFIRMADO → LANCADO:
- lancado_em, lancado_por: auditoria do lançamento
- odoo_payment_id, odoo_payment_name: account.payment criado
- odoo_debit_line_id, odoo_credit_line_id: linhas do payment
- odoo_full_reconcile_id: reconciliação com título
- odoo_full_reconcile_extrato_id: reconciliação com extrato
- erro_lancamento: mensagem de erro se falhar

SQL para rodar no Render:
--------------------------
ALTER TABLE lancamento_comprovante
    ADD COLUMN IF NOT EXISTS lancado_em TIMESTAMP,
    ADD COLUMN IF NOT EXISTS lancado_por VARCHAR(100),
    ADD COLUMN IF NOT EXISTS odoo_payment_id INTEGER,
    ADD COLUMN IF NOT EXISTS odoo_payment_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS odoo_debit_line_id INTEGER,
    ADD COLUMN IF NOT EXISTS odoo_credit_line_id INTEGER,
    ADD COLUMN IF NOT EXISTS odoo_full_reconcile_id INTEGER,
    ADD COLUMN IF NOT EXISTS odoo_full_reconcile_extrato_id INTEGER,
    ADD COLUMN IF NOT EXISTS erro_lancamento TEXT;

CREATE INDEX IF NOT EXISTS idx_lanc_odoo_payment ON lancamento_comprovante (odoo_payment_id);
CREATE INDEX IF NOT EXISTS idx_lanc_status_lancado ON lancamento_comprovante (status) WHERE status = 'LANCADO';
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            # Adicionar colunas
            db.session.execute(text("""
                ALTER TABLE lancamento_comprovante
                    ADD COLUMN IF NOT EXISTS lancado_em TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS lancado_por VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS odoo_payment_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_payment_name VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS odoo_debit_line_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_credit_line_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_full_reconcile_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_full_reconcile_extrato_id INTEGER,
                    ADD COLUMN IF NOT EXISTS erro_lancamento TEXT;
            """))

            # Índice para busca por payment_id
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_odoo_payment
                ON lancamento_comprovante (odoo_payment_id);
            """))

            # Índice parcial para lançados (otimiza queries de verificação)
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_lanc_status_lancado
                ON lancamento_comprovante (status) WHERE status = 'LANCADO';
            """))

            db.session.commit()
            print("✅ Migration executada com sucesso!")
            print("   - 9 colunas adicionadas à tabela lancamento_comprovante")
            print("   - 2 índices criados")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
