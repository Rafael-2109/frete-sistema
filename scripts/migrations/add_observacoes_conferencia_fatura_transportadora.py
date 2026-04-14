"""Migration: adiciona observacoes_conferencia em carvia_faturas_transportadora.

Paridade Nacom: espelha FaturaFrete.observacoes_conferencia usada no fluxo
de "Aprovar Conferencia da Fatura" (visualizar_fatura.html + conferir_fatura.html).

Operacoes:
1. ADD COLUMN observacoes_conferencia TEXT NULL

Idempotente: verifica information_schema antes da alteracao.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            col_exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_faturas_transportadora'
                  AND column_name = 'observacoes_conferencia'
            """)).fetchone()

            if col_exists:
                print("[skip] Coluna observacoes_conferencia ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_faturas_transportadora "
                    "ADD COLUMN observacoes_conferencia TEXT NULL"
                ))
                conn.commit()
                print("[ok] Coluna observacoes_conferencia adicionada")

            total = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_faturas_transportadora"
            )).scalar()
            com_obs = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_faturas_transportadora "
                "WHERE observacoes_conferencia IS NOT NULL"
            )).scalar()
            print(f"\n[resumo]")
            print(f"  Total faturas transportadora: {total}")
            print(f"  Com observacoes_conferencia preenchido: {com_obs}")


if __name__ == '__main__':
    main()
