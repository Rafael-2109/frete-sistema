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

    print("Step 1: ADD COLUMN frete_id (idempotent)")
    db.session.execute(text("""
        ALTER TABLE carvia_conta_corrente_transportadoras
          ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id)
    """))
    db.session.commit()

    # GUARD: cc.subcontrato_id pode ter sido droppado por migration posterior.
    # Em re-execucoes (cada deploy roda este script), pular Step 2 e Step 3
    # se a coluna source ja nao existe. Sentry PYTHON-FLASK-HS rastreava esse erro.
    sub_col_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'carvia_conta_corrente_transportadoras'
              AND column_name = 'subcontrato_id'
        )
    """)).scalar()

    if sub_col_existe:
        print("Step 2: Backfill frete_id via sub")
        result = db.session.execute(text("""
            UPDATE carvia_conta_corrente_transportadoras cc
            SET frete_id = s.frete_id
            FROM carvia_subcontratos s
            WHERE cc.subcontrato_id = s.id
              AND cc.frete_id IS NULL
              AND s.frete_id IS NOT NULL
        """))
        print(f"  Backfill: {result.rowcount} linhas")
        db.session.commit()

        orfaos = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras WHERE frete_id IS NULL"
        )).scalar() or 0
        if orfaos > 0:
            print(f"AVISO: {orfaos} movimentacoes sem frete_id (legado pre-CarviaFrete).")
            print("  Nao bloqueante: listar_extrato usa OUTER JOIN.")

        print("Step 3: Afrouxar subcontrato_id NOT NULL (model ja afrouxado em Phase 5)")
        db.session.execute(text("""
            ALTER TABLE carvia_conta_corrente_transportadoras
              ALTER COLUMN subcontrato_id DROP NOT NULL
        """))
        db.session.commit()
    else:
        print("Step 2/3: skip — cc.subcontrato_id ja foi droppado (migration finalizada)")

    print("Step 4: Index (idempotent)")
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_carvia_cc_frete_id
          ON carvia_conta_corrente_transportadoras (frete_id)
    """))
    db.session.commit()

    print()
    print("RESULTADO: frete_id adicionado + subcontrato_id afrouxado.")
    print("DROP subcontrato_id sera feito pela migration Phase 14.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
