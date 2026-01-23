#!/usr/bin/env python3
"""
Migration: Adicionar indice em po_consolidado_id na tabela validacao_nf_po_dfe
==============================================================================

Necessario para a validacao cross-phase (Fase 4 verifica Fases 1→2→3).
O indice parcial (WHERE NOT NULL) otimiza o lookup por PO consolidado.

SQL para Render Shell:
    CREATE INDEX IF NOT EXISTS idx_validacao_nf_po_po_consolidado
    ON validacao_nf_po_dfe (po_consolidado_id)
    WHERE po_consolidado_id IS NOT NULL;
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_indice():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_nf_po_po_consolidado
                ON validacao_nf_po_dfe (po_consolidado_id)
                WHERE po_consolidado_id IS NOT NULL;
            """))
            db.session.commit()
            print("✅ Indice idx_validacao_nf_po_po_consolidado criado com sucesso")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_indice()
