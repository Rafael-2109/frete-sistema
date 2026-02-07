# -*- coding: utf-8 -*-
"""
Migration: Adicionar campo 'tipo' na tabela comprovante_pagamento_boleto
========================================================================

Suporta tipos: 'boleto' (existente), 'pix' (novo).
Faz backfill de todos os registros existentes com tipo='boleto'.

Executar:
    source .venv/bin/activate
    python scripts/migrations/add_tipo_comprovante.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        try:
            # 1. Adicionar coluna com default 'boleto'
            db.session.execute(text("""
                ALTER TABLE comprovante_pagamento_boleto
                ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'boleto'
            """))
            print("[OK] Coluna 'tipo' adicionada (ou já existia)")

            # 2. Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comp_tipo
                ON comprovante_pagamento_boleto(tipo)
            """))
            print("[OK] Índice idx_comp_tipo criado (ou já existia)")

            # 3. Backfill: garantir que todos os registros existentes tenham tipo='boleto'
            result = db.session.execute(text("""
                UPDATE comprovante_pagamento_boleto
                SET tipo = 'boleto'
                WHERE tipo IS NULL OR tipo = ''
            """))
            print(f"[OK] Backfill: {result.rowcount} registro(s) atualizados com tipo='boleto'")

            db.session.commit()
            print("\n[SUCESSO] Migration concluída!")

        except Exception as e:
            print(f"\n[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
