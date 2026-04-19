"""Migration: Features F1 (CPF/CNPJ), F2 (parcela — sem DDL), F4 (valor).

F1: Adiciona `cpf_cnpj_parte` em pessoal_transacoes e `cpf_cnpj_padrao`
    em pessoal_regras_categorizacao, ambos com index parcial.
F2: Nao requer DDL — usa coluna existente `identificador_parcela`.
F4: Adiciona `valor_min` e `valor_max` em pessoal_regras_categorizacao.

Idempotente: verifica existencia antes de criar.
Executar localmente: python scripts/migrations/pessoal_features_f1_f2_f4.py
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
            print("=== Migration Pessoal F1/F2/F4 ===")

            # --- F1: cpf_cnpj_parte em pessoal_transacoes ---
            if not _column_exists(conn, "pessoal_transacoes", "cpf_cnpj_parte"):
                conn.execute(text(
                    "ALTER TABLE pessoal_transacoes "
                    "ADD COLUMN cpf_cnpj_parte VARCHAR(20)"
                ))
                print("[F1] cpf_cnpj_parte adicionada em pessoal_transacoes")
            else:
                print("[F1] cpf_cnpj_parte ja existe em pessoal_transacoes")

            if not _index_exists(conn, "idx_pessoal_transacoes_cpf_cnpj"):
                conn.execute(text(
                    "CREATE INDEX idx_pessoal_transacoes_cpf_cnpj "
                    "ON pessoal_transacoes(cpf_cnpj_parte) "
                    "WHERE cpf_cnpj_parte IS NOT NULL"
                ))
                print("[F1] Index idx_pessoal_transacoes_cpf_cnpj criado")
            else:
                print("[F1] Index idx_pessoal_transacoes_cpf_cnpj ja existe")

            # --- F1: cpf_cnpj_padrao em pessoal_regras_categorizacao ---
            if not _column_exists(conn, "pessoal_regras_categorizacao", "cpf_cnpj_padrao"):
                conn.execute(text(
                    "ALTER TABLE pessoal_regras_categorizacao "
                    "ADD COLUMN cpf_cnpj_padrao VARCHAR(20)"
                ))
                print("[F1] cpf_cnpj_padrao adicionada em pessoal_regras_categorizacao")
            else:
                print("[F1] cpf_cnpj_padrao ja existe em pessoal_regras_categorizacao")

            if not _index_exists(conn, "idx_pessoal_regras_cpf_cnpj"):
                conn.execute(text(
                    "CREATE INDEX idx_pessoal_regras_cpf_cnpj "
                    "ON pessoal_regras_categorizacao(cpf_cnpj_padrao) "
                    "WHERE cpf_cnpj_padrao IS NOT NULL"
                ))
                print("[F1] Index idx_pessoal_regras_cpf_cnpj criado")
            else:
                print("[F1] Index idx_pessoal_regras_cpf_cnpj ja existe")

            # --- F4: valor_min / valor_max em pessoal_regras_categorizacao ---
            if not _column_exists(conn, "pessoal_regras_categorizacao", "valor_min"):
                conn.execute(text(
                    "ALTER TABLE pessoal_regras_categorizacao "
                    "ADD COLUMN valor_min NUMERIC(15, 2)"
                ))
                print("[F4] valor_min adicionada")
            else:
                print("[F4] valor_min ja existe")

            if not _column_exists(conn, "pessoal_regras_categorizacao", "valor_max"):
                conn.execute(text(
                    "ALTER TABLE pessoal_regras_categorizacao "
                    "ADD COLUMN valor_max NUMERIC(15, 2)"
                ))
                print("[F4] valor_max adicionada")
            else:
                print("[F4] valor_max ja existe")

            # Verificar resultado
            result = conn.execute(text(
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name IN ('pessoal_transacoes', 'pessoal_regras_categorizacao') "
                "  AND column_name IN ('cpf_cnpj_parte', 'cpf_cnpj_padrao', 'valor_min', 'valor_max') "
                "ORDER BY table_name, column_name"
            ))
            print("\n=== Colunas criadas ===")
            for row in result:
                print(f"  {row[0]}.{row[1]}: {row[2]}")

        print("\n=== Migration concluida ===")


if __name__ == "__main__":
    executar()
