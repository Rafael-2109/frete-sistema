"""
Migration: Adicionar valor_proposto e valor_contra_proposta em carvia_sessao_demandas
=====================================================================================

Campos por DEMANDA (nao por sessao) para proposta comercial granular.

Executar: python scripts/migrations/adicionar_campos_demanda_cotacao_carvia.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def run_migration():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # ---- BEFORE ----
        result = conn.execute(db.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'carvia_sessao_demandas' "
            "AND column_name IN ('valor_proposto', 'valor_contra_proposta')"
        ))
        existing = [row[0] for row in result]
        print(f"[BEFORE] Colunas existentes: {existing}")

        # ---- ADD valor_proposto ----
        if 'valor_proposto' not in existing:
            conn.execute(db.text(
                "ALTER TABLE carvia_sessao_demandas "
                "ADD COLUMN valor_proposto NUMERIC(15,2)"
            ))
            conn.commit()
            print("[OK] valor_proposto adicionado")
        else:
            print("[SKIP] valor_proposto ja existe")

        # ---- ADD valor_contra_proposta ----
        if 'valor_contra_proposta' not in existing:
            conn.execute(db.text(
                "ALTER TABLE carvia_sessao_demandas "
                "ADD COLUMN valor_contra_proposta NUMERIC(15,2)"
            ))
            conn.commit()
            print("[OK] valor_contra_proposta adicionado")
        else:
            print("[SKIP] valor_contra_proposta ja existe")

        # ---- AFTER ----
        result = conn.execute(db.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'carvia_sessao_demandas' "
            "AND column_name IN ('valor_proposto', 'valor_contra_proposta')"
        ))
        print(f"[AFTER] Colunas: {[row[0] for row in result]}")

        conn.close()
        print("\n[DONE] Migration concluida.")


if __name__ == '__main__':
    run_migration()
