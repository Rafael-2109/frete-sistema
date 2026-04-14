"""Migration: adiciona origem em entregas_monitoradas (NACOM | CARVIA).

Contexto: NFs do subsistema CarVia (frete subcontratado) passam a coexistir
com NFs Nacom em EntregaMonitorada. O discriminador `origem` evita colisao
de numero_nf entre os dois dominios (emitentes CarVia tem numeracao propria).

Operacoes:
1. ADD COLUMN origem VARCHAR(10) NOT NULL DEFAULT 'NACOM'
2. CREATE INDEX idx_em_origem ON entregas_monitoradas(origem)

Default 'NACOM' preserva todos os registros existentes; o backfill CarVia
(scripts/migrations/backfill_entrega_monitorada_carvia.py) popula os novos.

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
                WHERE table_name = 'entregas_monitoradas'
                  AND column_name = 'origem'
            """)).fetchone()

            if col_exists:
                print("[skip] Coluna origem ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE entregas_monitoradas "
                    "ADD COLUMN origem VARCHAR(10) NOT NULL DEFAULT 'NACOM'"
                ))
                conn.commit()
                print("[ok] Coluna origem adicionada (default='NACOM')")

            idx_exists = conn.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'entregas_monitoradas'
                  AND indexname = 'idx_em_origem'
            """)).fetchone()

            if idx_exists:
                print("[skip] Index idx_em_origem ja existe")
            else:
                conn.execute(text(
                    "CREATE INDEX idx_em_origem "
                    "ON entregas_monitoradas(origem)"
                ))
                conn.commit()
                print("[ok] Index idx_em_origem criado")

            total = conn.execute(text(
                "SELECT COUNT(*) FROM entregas_monitoradas"
            )).scalar()
            por_origem = conn.execute(text(
                "SELECT origem, COUNT(*) AS qtd "
                "FROM entregas_monitoradas GROUP BY origem ORDER BY origem"
            )).fetchall()

            print(f"\n[resumo]")
            print(f"  Total entregas monitoradas: {total}")
            for row in por_origem:
                print(f"    {row.origem}: {row.qtd}")


if __name__ == '__main__':
    main()
