# -*- coding: utf-8 -*-
"""
Migração: Adicionar campos OFX + Odoo na tabela comprovante_pagamento_boleto
=============================================================================

Adiciona 12 campos para vincular comprovantes com extrato OFX e linhas do Odoo.

Executar localmente:
    source .venv/bin/activate && python scripts/adicionar_campos_ofx_comprovante.py

SQL para Render Shell:
    ALTER TABLE comprovante_pagamento_boleto
        ADD COLUMN IF NOT EXISTS ofx_fitid VARCHAR(100),
        ADD COLUMN IF NOT EXISTS ofx_checknum VARCHAR(50),
        ADD COLUMN IF NOT EXISTS ofx_memo VARCHAR(500),
        ADD COLUMN IF NOT EXISTS ofx_valor NUMERIC(15,2),
        ADD COLUMN IF NOT EXISTS ofx_data DATE,
        ADD COLUMN IF NOT EXISTS ofx_arquivo_origem VARCHAR(255),
        ADD COLUMN IF NOT EXISTS odoo_statement_line_id INTEGER,
        ADD COLUMN IF NOT EXISTS odoo_move_id INTEGER,
        ADD COLUMN IF NOT EXISTS odoo_statement_id INTEGER,
        ADD COLUMN IF NOT EXISTS odoo_journal_id INTEGER,
        ADD COLUMN IF NOT EXISTS odoo_is_reconciled BOOLEAN,
        ADD COLUMN IF NOT EXISTS odoo_vinculado_em TIMESTAMP;

    CREATE INDEX IF NOT EXISTS idx_comp_ofx_fitid ON comprovante_pagamento_boleto(ofx_fitid);
    CREATE INDEX IF NOT EXISTS idx_comp_ofx_checknum ON comprovante_pagamento_boleto(ofx_checknum);
    CREATE INDEX IF NOT EXISTS idx_comp_odoo_statement_line ON comprovante_pagamento_boleto(odoo_statement_line_id);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campos_ofx_comprovante():
    """Adiciona campos OFX + Odoo à tabela comprovante_pagamento_boleto."""
    app = create_app()
    with app.app_context():
        try:
            # Adicionar colunas
            db.session.execute(text("""
                ALTER TABLE comprovante_pagamento_boleto
                    ADD COLUMN IF NOT EXISTS ofx_fitid VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS ofx_checknum VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS ofx_memo VARCHAR(500),
                    ADD COLUMN IF NOT EXISTS ofx_valor NUMERIC(15,2),
                    ADD COLUMN IF NOT EXISTS ofx_data DATE,
                    ADD COLUMN IF NOT EXISTS ofx_arquivo_origem VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS odoo_statement_line_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_move_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_statement_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_journal_id INTEGER,
                    ADD COLUMN IF NOT EXISTS odoo_is_reconciled BOOLEAN,
                    ADD COLUMN IF NOT EXISTS odoo_vinculado_em TIMESTAMP;
            """))
            print("[OK] Colunas adicionadas com sucesso")

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comp_ofx_fitid
                    ON comprovante_pagamento_boleto(ofx_fitid);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comp_ofx_checknum
                    ON comprovante_pagamento_boleto(ofx_checknum);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comp_odoo_statement_line
                    ON comprovante_pagamento_boleto(odoo_statement_line_id);
            """))
            print("[OK] Índices criados com sucesso")

            db.session.commit()
            print("\n[SUCESSO] Migração concluída!")

            # Verificar
            resultado = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'comprovante_pagamento_boleto'
                  AND column_name LIKE 'ofx_%' OR column_name LIKE 'odoo_%'
                ORDER BY ordinal_position;
            """))
            print("\nCampos adicionados:")
            for row in resultado:
                print(f"  - {row[0]}: {row[1]}")

        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_campos_ofx_comprovante()
