"""Migration: Rename carvia_aprovacoes_subcontrato → carvia_aprovacoes_frete.

Data: 2026-04-14
Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    print("=" * 70)
    print("MIGRATION: Rename aprovacoes_subcontrato → aprovacoes_frete")
    print("=" * 70)

    total = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato"
    )).scalar()
    print(f"Total aprovacoes: {total}")
    print()

    print("Step 1: ADD COLUMN frete_id (nullable)")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_subcontrato
          ADD COLUMN IF NOT EXISTS frete_id INTEGER
          REFERENCES carvia_fretes(id)
    """))
    db.session.commit()

    print("Step 2: Backfill frete_id via sub.frete_id")
    result = db.session.execute(text("""
        UPDATE carvia_aprovacoes_subcontrato aps
        SET frete_id = s.frete_id
        FROM carvia_subcontratos s
        WHERE aps.subcontrato_id = s.id
          AND aps.frete_id IS NULL
          AND s.frete_id IS NOT NULL
    """))
    print(f"  Backfill: {result.rowcount} linhas atualizadas")
    db.session.commit()

    orfaos = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato WHERE frete_id IS NULL"
    )).scalar() or 0
    if orfaos > 0:
        print(f"ERRO: {orfaos} aprovacoes orfas — investigar manualmente")
        print("Abortar migration.")
        return 1
    print("  Sem orfaos, prosseguindo.")

    print("Step 3: NOT NULL em frete_id + index")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_subcontrato
          ALTER COLUMN frete_id SET NOT NULL
    """))
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_carvia_aprovacoes_frete_id
          ON carvia_aprovacoes_subcontrato (frete_id)
    """))
    db.session.commit()

    print("Step 4: RENAME TABLE")
    db.session.execute(text("""
        ALTER TABLE IF EXISTS carvia_aprovacoes_subcontrato
          RENAME TO carvia_aprovacoes_frete
    """))
    db.session.commit()

    print("Step 5: DROP COLUMN subcontrato_id")
    db.session.execute(text("""
        ALTER TABLE carvia_aprovacoes_frete
          DROP COLUMN IF EXISTS subcontrato_id
    """))
    db.session.commit()

    total_final = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_frete"
    )).scalar()
    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print(f"carvia_aprovacoes_frete: {total_final} registros")
    return 0


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        sys.exit(run_migration())
