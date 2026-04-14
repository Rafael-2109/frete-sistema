"""Migration: Add frete_id em carvia_conta_corrente_transportadoras + backfill.

Data: 2026-04-14
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    print("=" * 70)
    print("MIGRATION: Add frete_id em CC + backfill")
    print("=" * 70)

    total = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras"
    )).scalar() or 0
    print(f"Total movimentacoes CC: {total}")
    print()

    print("Step 1: ADD COLUMN frete_id")
    db.session.execute(text("""
        ALTER TABLE carvia_conta_corrente_transportadoras
          ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id)
    """))
    db.session.commit()

    print("Step 2: Backfill")
    result = db.session.execute(text("""
        UPDATE carvia_conta_corrente_transportadoras cc
        SET frete_id = s.frete_id
        FROM carvia_subcontratos s
        WHERE cc.subcontrato_id = s.id
          AND cc.frete_id IS NULL
          AND s.frete_id IS NOT NULL
    """))
    print(f"  Backfill: {result.rowcount}")
    db.session.commit()

    orfaos = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras WHERE frete_id IS NULL"
    )).scalar() or 0
    if orfaos > 0:
        print(f"AVISO: {orfaos} movimentacoes sem frete_id")

    print("Step 3: Index")
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_carvia_cc_frete_id
          ON carvia_conta_corrente_transportadoras (frete_id)
    """))
    db.session.commit()

    print()
    print("RESULTADO: frete_id adicionado. DROP subcontrato_id deve ser feito")
    print("manualmente apos deploy do codigo migrado (Phase 14).")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
