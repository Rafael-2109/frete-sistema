"""Migration v17 (2026-05-25): UK em RecebimentoLf.odoo_lf_invoice_id

Origem: CRITICAL-3 do code-review do Skill 8 ETAPA E (sessao v17 2026-05-25).

Garante idempotencia (G-RECLF-3): duas chamadas concorrentes (ou re-entrada
apos crash) NAO podem criar 2 RecebimentoLf para a mesma invoice da LF.

Verifica duplicatas before/after. Idempotente.

Uso:
    python scripts/migrations/2026_05_25_v17_uk_recebimento_lf_invoice_id.py

Em Render Shell, prefira o .sql (idempotente).
"""
import os
import sys

# sys.path.insert obrigatorio (regra CLAUDE.md em ~/.claude/CLAUDE.md)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        print('=== Migration v17 — UK RecebimentoLf.odoo_lf_invoice_id ===\n')

        # BEFORE: detectar duplicatas
        print('[BEFORE] Verificando duplicatas em odoo_lf_invoice_id...')
        dup_query = text("""
            SELECT odoo_lf_invoice_id, COUNT(*) as n
            FROM recebimento_lf
            WHERE odoo_lf_invoice_id IS NOT NULL
            GROUP BY odoo_lf_invoice_id
            HAVING COUNT(*) > 1
            LIMIT 20
        """)
        dups = db.session.execute(dup_query).fetchall()
        if dups:
            print(f'  X DUPLICATAS DETECTADAS ({len(dups)} invoices):')
            for row in dups:
                print(f'    invoice {row[0]}: {row[1]} ocorrencias')
            print('  Resolver duplicatas ANTES de aplicar UK!')
            return 1

        print('  ✓ Sem duplicatas — UK pode ser criada.')

        # Verificar se UK ja existe
        check_query = text("""
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_recebimento_lf_invoice_id'
              AND conrelid = 'recebimento_lf'::regclass
        """)
        exists = db.session.execute(check_query).fetchone()
        if exists:
            print('\n[SKIP] Constraint uq_recebimento_lf_invoice_id ja existe.\n')
            return 0

        # Aplicar UK
        print('\n[APLICANDO] ALTER TABLE ADD CONSTRAINT UNIQUE...')
        db.session.execute(text("""
            ALTER TABLE recebimento_lf
            ADD CONSTRAINT uq_recebimento_lf_invoice_id
            UNIQUE (odoo_lf_invoice_id)
        """))
        db.session.commit()

        # AFTER: verificar
        print('\n[AFTER] Verificando UK criada...')
        exists = db.session.execute(check_query).fetchone()
        if exists:
            print('  ✓ Constraint uq_recebimento_lf_invoice_id criada.\n')
            return 0

        print('  X UK nao detectada apos ALTER — investigar.\n')
        return 1


if __name__ == '__main__':
    sys.exit(main())
