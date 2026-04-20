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

    # Idempotency guard: skip se tabela DESTINO ja existe (rename ja ocorreu).
    # Sentry PYTHON-FLASK-HR: ambas tabelas podem coexistir se outra migration
    # (ex: carvia_aprovacao_conta_corrente.py com CREATE TABLE IF NOT EXISTS)
    # recriou a source. Cleanup automatico da source vazia.
    destino_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_aprovacoes_frete'
        )
    """)).scalar()

    source_existe = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_aprovacoes_subcontrato'
        )
    """)).scalar()

    if destino_existe:
        print("Migration ja aplicada (tabela carvia_aprovacoes_frete existe).")
        if source_existe:
            # Cleanup: source orfa recriada por outra migration. Drop se vazia.
            count_source = db.session.execute(text(
                "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato"
            )).scalar() or 0
            if count_source == 0:
                print("Source carvia_aprovacoes_subcontrato existe vazia — DROP cleanup.")
                db.session.execute(text(
                    "DROP TABLE IF EXISTS carvia_aprovacoes_subcontrato CASCADE"
                ))
                db.session.commit()
            else:
                print(f"AVISO: source tem {count_source} registros — investigar manualmente.")
        print("Saltando.")
        return 0

    if not source_existe:
        print("Nem source nem destino existem — nada a fazer.")
        return 0

    total = db.session.execute(text(
        "SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato"
    )).scalar() or 0
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
