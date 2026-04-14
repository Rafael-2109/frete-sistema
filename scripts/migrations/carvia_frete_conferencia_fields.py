"""Migration: Add campos de conferencia em carvia_fretes + backfill.

Data: 2026-04-14
Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    from app.carvia.models import CarviaFrete, CarviaSubcontrato

    print("=" * 70)
    print("MIGRATION: CarviaFrete ganha campos de conferencia")
    print("=" * 70)

    # ANTES
    total_fretes = CarviaFrete.query.count()
    total_subs = CarviaSubcontrato.query.count()
    subs_aprovados = CarviaSubcontrato.query.filter_by(
        status_conferencia='APROVADO'
    ).count()
    subs_divergentes = CarviaSubcontrato.query.filter_by(
        status_conferencia='DIVERGENTE'
    ).count()

    print(f"Total fretes: {total_fretes}")
    print(f"Total subs: {total_subs}")
    print(f"  Subs APROVADO: {subs_aprovados}")
    print(f"  Subs DIVERGENTE: {subs_divergentes}")
    print()

    # DDL
    sql_ddl = [
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20)
           NOT NULL DEFAULT 'PENDENTE'""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100)""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS detalhes_conferencia JSON""",
        """ALTER TABLE carvia_fretes
           ADD COLUMN IF NOT EXISTS requer_aprovacao BOOLEAN
           NOT NULL DEFAULT FALSE""",
        """CREATE INDEX IF NOT EXISTS idx_carvia_fretes_status_conferencia
           ON carvia_fretes (status_conferencia)""",
    ]
    for sql in sql_ddl:
        print(f"Executando: {sql[:60]}...")
        db.session.execute(text(sql))
    db.session.commit()
    print("DDL concluido.")
    print()

    # Backfill 1: consolidar status_conferencia
    print("Backfill 1: consolidar status_conferencia sub -> frete")
    result = db.session.execute(text("""
        WITH consolidacao AS (
          SELECT
            s.frete_id,
            COUNT(*) AS total,
            SUM(CASE WHEN s.status_conferencia = 'APROVADO' THEN 1 ELSE 0 END) AS aprovados,
            SUM(CASE WHEN s.status_conferencia = 'DIVERGENTE' THEN 1 ELSE 0 END) AS divergentes,
            MAX(s.conferido_por) AS conferido_por_any,
            MAX(s.conferido_em) AS conferido_em_max,
            BOOL_OR(s.requer_aprovacao) AS algum_requer_aprovacao
          FROM carvia_subcontratos s
          WHERE s.frete_id IS NOT NULL
          GROUP BY s.frete_id
        )
        UPDATE carvia_fretes f
        SET
          status_conferencia = CASE
            WHEN c.divergentes > 0 THEN 'DIVERGENTE'
            WHEN c.aprovados = c.total THEN 'APROVADO'
            ELSE 'PENDENTE'
          END,
          conferido_por = CASE WHEN c.aprovados = c.total THEN c.conferido_por_any ELSE NULL END,
          conferido_em  = CASE WHEN c.aprovados = c.total THEN c.conferido_em_max ELSE NULL END,
          requer_aprovacao = COALESCE(c.algum_requer_aprovacao, FALSE)
        FROM consolidacao c
        WHERE f.id = c.frete_id
          AND f.status_conferencia = 'PENDENTE'
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    # Backfill 2: valor_considerado agregado
    print("Backfill 2: valor_considerado agregado")
    result = db.session.execute(text("""
        UPDATE carvia_fretes f
        SET valor_considerado = COALESCE(f.valor_considerado, subtotal.soma)
        FROM (
          SELECT frete_id, SUM(valor_considerado) AS soma
          FROM carvia_subcontratos
          WHERE frete_id IS NOT NULL AND valor_considerado IS NOT NULL
          GROUP BY frete_id
        ) subtotal
        WHERE f.id = subtotal.frete_id
          AND f.valor_considerado IS NULL
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    # Backfill 3: valor_pago agregado
    print("Backfill 3: valor_pago agregado")
    result = db.session.execute(text("""
        UPDATE carvia_fretes f
        SET valor_pago = COALESCE(f.valor_pago, subtotal.soma)
        FROM (
          SELECT frete_id, SUM(valor_pago) AS soma
          FROM carvia_subcontratos
          WHERE frete_id IS NOT NULL AND valor_pago IS NOT NULL
          GROUP BY frete_id
        ) subtotal
        WHERE f.id = subtotal.frete_id
          AND f.valor_pago IS NULL
    """))
    print(f"  Fretes atualizados: {result.rowcount}")

    db.session.commit()
    print()

    # DEPOIS
    fretes_aprovados = CarviaFrete.query.filter_by(
        status_conferencia='APROVADO'
    ).count()
    fretes_divergentes = CarviaFrete.query.filter_by(
        status_conferencia='DIVERGENTE'
    ).count()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print(f"Fretes APROVADO: {fretes_aprovados}")
    print(f"Fretes DIVERGENTE: {fretes_divergentes}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_migration()
