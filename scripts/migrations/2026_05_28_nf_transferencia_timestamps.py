"""Migration 2026-05-28: adiciona timestamps em nf_transferencia_snapshot.

3 colunas DateTime nullable:
- data_emissao_hora           (NF origem — timestamp emissao)
- picking_data_hora           (picking destino — date_done)
- invoice_destino_data_hora   (invoice destino — create_date)

Idempotente: ADD COLUMN IF NOT EXISTS.

Usar:
  python scripts/migrations/2026_05_28_nf_transferencia_timestamps.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = Path(__file__).with_suffix('.sql')
COLUNAS = ('data_emissao_hora', 'picking_data_hora', 'invoice_destino_data_hora')


def _coluna_existe(conn, tabela, coluna):
    row = conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :tabela AND column_name = :coluna
        LIMIT 1
    """), {'tabela': tabela, 'coluna': coluna}).fetchone()
    return bool(row)


def _print_status(conn, label):
    print(f"=== {label} ===")
    for col in COLUNAS:
        existe = _coluna_existe(conn, 'nf_transferencia_snapshot', col)
        marker = 'OK' if existe else 'AUSENTE'
        print(f"  nf_transferencia_snapshot.{col}: {marker}")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            _print_status(conn, 'ANTES')

            print("\n=== APLICANDO MIGRATION nf_transferencia_timestamps ===")
            sql = SQL_PATH.read_text(encoding='utf-8')
            # SQL contem bloco DO $$ ... END $$ com `;` internos — split
            # naive por ';' quebraria. exec_driver_sql aceita multiplos
            # statements em psycopg2 num unico execute.
            conn.exec_driver_sql(sql)
            print("  bloco SQL completo executado (com guard DO $$)")

            print()
            _print_status(conn, 'DEPOIS')
            print("\nMIGRATION APLICADA COM SUCESSO")


if __name__ == '__main__':
    main()
