"""
Migration: Adicionar coluna `divergencia_cnpj_cotacao` em carvia_nfs.

Data: 2026-05-11
Motivo:
    Sinalizar NFs CarVia cujo `cnpj_destinatario` diverge do `cnpj` do
    endereco destino da cotacao vinculada. Setado automaticamente em
    EmbarqueCarViaService.expandir_provisorio (Fase B2). Limpo apos
    operador decidir via UI (Fase B4: atualizar cotacao OU descartar
    divergencia).

Index parcial:
    - ix_carvia_nfs_divergencia_cnpj (apenas linhas com TRUE)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db # noqa: E402 # type: ignore
from sqlalchemy import text # noqa: E402 # type: ignore


def check_before(conn):
    """Verifica estado antes."""
    print("=== BEFORE ===")

    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'carvia_nfs' AND column_name = 'divergencia_cnpj_cotacao'"
    ))
    existe = result.scalar() is not None
    print(f"  carvia_nfs.divergencia_cnpj_cotacao existe? {existe}")

    result = conn.execute(text("SELECT COUNT(*) FROM carvia_nfs"))
    print(f"  carvia_nfs total: {result.scalar()}")

    print()


def run_migration(conn):
    """Executa migration idempotente."""

    conn.execute(text(
        "ALTER TABLE carvia_nfs "
        "ADD COLUMN IF NOT EXISTS divergencia_cnpj_cotacao "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    print("[1/2] carvia_nfs.divergencia_cnpj_cotacao: coluna garantida")

    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_carvia_nfs_divergencia_cnpj "
        "ON carvia_nfs (divergencia_cnpj_cotacao) "
        "WHERE divergencia_cnpj_cotacao = TRUE"
    ))
    print("[2/2] ix_carvia_nfs_divergencia_cnpj: index parcial garantido")


def check_after(conn):
    """Verifica estado depois."""
    print("\n=== AFTER ===")

    result = conn.execute(text(
        "SELECT divergencia_cnpj_cotacao, COUNT(*) "
        "FROM carvia_nfs GROUP BY divergencia_cnpj_cotacao "
        "ORDER BY divergencia_cnpj_cotacao"
    ))
    rows = result.fetchall()
    print("  carvia_nfs (por divergencia_cnpj_cotacao):")
    for flag, total in rows:
        print(f"    {flag}: {total}")


def main():
    app = create_app()

    with app.app_context():
        with db.engine.begin() as conn:
            check_before(conn)
            run_migration(conn)
            check_after(conn)

    print("\n=== MIGRATION CONCLUIDA ===")


if __name__ == '__main__':
    main()
