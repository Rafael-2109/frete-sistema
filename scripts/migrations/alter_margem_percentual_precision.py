"""
Script para alterar precisão dos campos de margem percentual
============================================================

Problema: Campos margem_bruta_percentual e margem_liquida_percentual
têm NUMERIC(5,2) que suporta apenas ±999.99

Solução: Alterar para NUMERIC(7,2) que suporta até ±99999.99%

Data: 2026-01-06
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def alterar_precisao_margem():
    app = create_app()
    with app.app_context():
        try:
            print("🔄 Alterando precisão dos campos de margem percentual...")

            # Alterar margem_bruta_percentual
            db.session.execute(text("""
                ALTER TABLE carteira_principal
                ALTER COLUMN margem_bruta_percentual TYPE NUMERIC(7, 2)
            """))
            print("✅ margem_bruta_percentual alterado para NUMERIC(7,2)")

            # Alterar margem_liquida_percentual
            db.session.execute(text("""
                ALTER TABLE carteira_principal
                ALTER COLUMN margem_liquida_percentual TYPE NUMERIC(7, 2)
            """))
            print("✅ margem_liquida_percentual alterado para NUMERIC(7,2)")

            db.session.commit()
            print("✅ Migração concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    alterar_precisao_margem()
