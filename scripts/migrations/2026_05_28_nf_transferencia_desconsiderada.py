"""Migration 2026-05-28: cria tabela nf_transferencia_desconsiderada.

Persiste flag por NF (account_move_id_origem) para EXCLUIR do calculo de
em_transito_*. Sobrevive ao DELETE+INSERT do refresh de NfTransferenciaSnapshot.

Idempotente: CREATE TABLE IF NOT EXISTS.

Usar:
  python scripts/migrations/2026_05_28_nf_transferencia_desconsiderada.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = Path(__file__).with_suffix('.sql')
TABELA = 'nf_transferencia_desconsiderada'


def _tabela_existe(conn, nome):
    row = conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :nome
        LIMIT 1
    """), {'nome': nome}).fetchone()
    return bool(row)


def _print_status(conn, label):
    existe = _tabela_existe(conn, TABELA)
    marker = 'OK' if existe else 'AUSENTE'
    print(f"=== {label} ===  {TABELA}: {marker}")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            _print_status(conn, 'ANTES')

            print(f"\n=== APLICANDO MIGRATION {TABELA} ===")
            sql = SQL_PATH.read_text(encoding='utf-8')
            # Remover comentarios SQL (-- ate fim de linha) ANTES do split
            # para evitar que 'empty statement' chegue ao psycopg2.
            limpo = '\n'.join(
                linha for linha in sql.splitlines()
                if linha.strip() and not linha.strip().startswith('--')
            )
            statements = [s.strip() for s in limpo.split(';') if s.strip()]
            for i, stmt in enumerate(statements, 1):
                conn.execute(text(stmt))
                print(f"  [{i}/{len(statements)}] executado")

            print()
            _print_status(conn, 'DEPOIS')
            print("\nMIGRATION APLICADA COM SUCESSO")


if __name__ == '__main__':
    main()
