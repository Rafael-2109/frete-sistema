"""Migration 2026-05-28: cria tabelas de snapshot de NF inter-company.

Cria 2 tabelas:
- nf_transferencia_snapshot       (cabecalho — 1 linha por NF inter-company)
- nf_transferencia_produto_snapshot (linhas de produto)

Idempotente: usa CREATE TABLE IF NOT EXISTS + indexes idempotentes.

Usar:
  python scripts/migrations/2026_05_28_nf_transferencia_snapshot.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = Path(__file__).with_suffix('.sql')


def _tabela_existe(conn, nome):
    row = conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :nome
        LIMIT 1
    """), {'nome': nome}).fetchone()
    return bool(row)


def _print_status(conn, label):
    print(f"=== {label} ===")
    for tabela in ('nf_transferencia_snapshot', 'nf_transferencia_produto_snapshot'):
        existe = _tabela_existe(conn, tabela)
        marker = 'OK' if existe else 'AUSENTE'
        print(f"  {tabela}: {marker}")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            _print_status(conn, 'ANTES')

            print("\n=== APLICANDO MIGRATION nf_transferencia_snapshot ===")
            sql = SQL_PATH.read_text(encoding='utf-8')
            # Split em statements (psycopg2 nao roda multiplos statements
            # num execute() generico — separar por ';' funciona pra DDL).
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for i, stmt in enumerate(statements, 1):
                conn.execute(text(stmt))
                print(f"  [{i}/{len(statements)}] executado")

            print()
            _print_status(conn, 'DEPOIS')
            print("\nMIGRATION APLICADA COM SUCESSO")


if __name__ == '__main__':
    main()
