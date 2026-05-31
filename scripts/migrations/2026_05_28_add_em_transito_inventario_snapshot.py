"""Migration 2026-05-28: adiciona em_transito_fb/cd/lf em inventario_snapshot_odoo.

Captura estoque NFs inter-company emitidas mas ainda nao escrituradas no destino.
Calculado a partir de NfTransferenciaSnapshot quando refresh do inventario roda.

Idempotente: ADD COLUMN IF NOT EXISTS.

Usar:
  python scripts/migrations/2026_05_28_add_em_transito_inventario_snapshot.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


COLUNAS = ('em_transito_fb', 'em_transito_cd', 'em_transito_lf')


def _print_colunas(conn, label):
    print(f"=== {label} ===")
    rows = conn.execute(text("""
        SELECT column_name, data_type, numeric_precision, numeric_scale, column_default
        FROM information_schema.columns
        WHERE table_name = 'inventario_snapshot_odoo'
          AND column_name = ANY(:cols)
        ORDER BY column_name
    """), {'cols': list(COLUNAS)}).fetchall()
    if not rows:
        print("  (nenhuma coluna em_transito_* presente)")
        return
    for r in rows:
        print(f"  {r.column_name}: {r.data_type}({r.numeric_precision},{r.numeric_scale}) default={r.column_default}")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            _print_colunas(conn, 'ANTES')

            print("\n=== APLICANDO MIGRATION em_transito_inventario_snapshot ===")
            for col in COLUNAS:
                conn.execute(text(
                    f"ALTER TABLE inventario_snapshot_odoo "
                    f"ADD COLUMN IF NOT EXISTS {col} NUMERIC(15, 3) DEFAULT 0"
                ))
                print(f"  + {col} OK")

            print()
            _print_colunas(conn, 'DEPOIS')
            print("\nMIGRATION APLICADA COM SUCESSO")


if __name__ == '__main__':
    main()
