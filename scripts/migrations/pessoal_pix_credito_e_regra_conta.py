"""Migration: Pessoal — Caso 1 (Pix no Credito) + Caso 2 (regra por conta).

C2: `contas_ids` (TEXT, JSON array) em pessoal_regras_categorizacao — condicao por
    conta de DESTINO (NULL = vale para qualquer conta).
C1: `eh_pix_credito` (BOOLEAN) + `pix_credito_grupo` (VARCHAR) em pessoal_transacoes —
    marcam/agrupam as pernas do trio "Pix no Credito" do Nubank.

Idempotente: verifica existencia antes de criar.
Executar localmente: python scripts/migrations/pessoal_pix_credito_e_regra_conta.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text

from app import create_app, db


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :i"
    ), {"i": index_name})
    return result.fetchone() is not None


def executar():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=== Migration Pessoal Pix no Credito + Regra por Conta ===")

            # --- C2: contas_ids em pessoal_regras_categorizacao ---
            if not _column_exists(conn, "pessoal_regras_categorizacao", "contas_ids"):
                conn.execute(text(
                    "ALTER TABLE pessoal_regras_categorizacao "
                    "ADD COLUMN contas_ids TEXT"
                ))
                print("[C2] contas_ids adicionada em pessoal_regras_categorizacao")
            else:
                print("[C2] contas_ids ja existe em pessoal_regras_categorizacao")

            # --- C1: eh_pix_credito em pessoal_transacoes ---
            if not _column_exists(conn, "pessoal_transacoes", "eh_pix_credito"):
                conn.execute(text(
                    "ALTER TABLE pessoal_transacoes "
                    "ADD COLUMN eh_pix_credito BOOLEAN DEFAULT FALSE"
                ))
                print("[C1] eh_pix_credito adicionada em pessoal_transacoes")
            else:
                print("[C1] eh_pix_credito ja existe em pessoal_transacoes")

            # --- C1: pix_credito_grupo em pessoal_transacoes ---
            if not _column_exists(conn, "pessoal_transacoes", "pix_credito_grupo"):
                conn.execute(text(
                    "ALTER TABLE pessoal_transacoes "
                    "ADD COLUMN pix_credito_grupo VARCHAR(40)"
                ))
                print("[C1] pix_credito_grupo adicionada em pessoal_transacoes")
            else:
                print("[C1] pix_credito_grupo ja existe em pessoal_transacoes")

            if not _index_exists(conn, "idx_pessoal_transacoes_pix_credito_grupo"):
                conn.execute(text(
                    "CREATE INDEX idx_pessoal_transacoes_pix_credito_grupo "
                    "ON pessoal_transacoes(pix_credito_grupo) "
                    "WHERE pix_credito_grupo IS NOT NULL"
                ))
                print("[C1] Index idx_pessoal_transacoes_pix_credito_grupo criado")
            else:
                print("[C1] Index idx_pessoal_transacoes_pix_credito_grupo ja existe")

            # Verificar resultado
            result = conn.execute(text(
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE (table_name = 'pessoal_regras_categorizacao' AND column_name = 'contas_ids') "
                "   OR (table_name = 'pessoal_transacoes' "
                "       AND column_name IN ('eh_pix_credito', 'pix_credito_grupo')) "
                "ORDER BY table_name, column_name"
            ))
            print("\n=== Colunas criadas ===")
            for row in result:
                print(f"  {row[0]}.{row[1]}: {row[2]}")

        print("\n=== Migration concluida ===")


if __name__ == "__main__":
    executar()
