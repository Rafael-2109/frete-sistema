#!/usr/bin/env python3
"""
Migration Fase 4: Adicionar colunas Pluggy em PessoalTransacao e PessoalConta.

Dependencia: scripts/migrations/pluggy_staging_tables.py executada antes.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/pluggy_campos_transacao.py

Data: 2026-04-21
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db
from sqlalchemy import text


COLUNAS_ESPERADAS = {
    "pessoal_contas": [
        "pluggy_account_id",
        "pluggy_item_pk",
    ],
    "pessoal_transacoes": [
        "pluggy_transaction_id",
        "origem_import",
        "operation_type",
        "merchant_nome",
        "merchant_cnpj",
        "categoria_pluggy_id",
        "categoria_pluggy_sugerida",
    ],
}


def verificar_colunas() -> dict[str, dict[str, bool]]:
    resultado: dict[str, dict[str, bool]] = {}
    for tabela, cols in COLUNAS_ESPERADAS.items():
        resultado[tabela] = {}
        for col in cols:
            existe = db.session.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:t AND column_name=:c)"
                ),
                {"t": tabela, "c": col},
            ).scalar()
            resultado[tabela][col] = bool(existe)
    return resultado


def executar_migration():
    app = create_app()
    with app.app_context():
        print("=" * 78)
        print("MIGRATION: Pluggy Campos em PessoalTransacao/PessoalConta (Fase 4)")
        print("=" * 78)

        print("\n[BEFORE]")
        antes = verificar_colunas()
        for tabela, cols in antes.items():
            for col, existe in cols.items():
                simbolo = "OK" if existe else "--"
                print(f"  [{simbolo}] {tabela}.{col}")

        sql_path = Path(__file__).parent / "pluggy_campos_transacao.sql"
        print(f"\n[EXEC] Executando {sql_path.name}...")
        sql_content = sql_path.read_text(encoding="utf-8")

        try:
            db.session.execute(text(sql_content))
            db.session.commit()
            print("[EXEC] OK — SQL executado com sucesso.")
        except Exception as exc:
            db.session.rollback()
            print(f"[ERRO] {exc}")
            raise

        print("\n[AFTER]")
        depois = verificar_colunas()
        todas_ok = True
        for tabela, cols in depois.items():
            for col, existe in cols.items():
                simbolo = "OK" if existe else "FAIL"
                print(f"  [{simbolo}] {tabela}.{col}")
                if not existe:
                    todas_ok = False

        print("\n" + "=" * 78)
        if todas_ok:
            print("SUCESSO — todas as colunas criadas (ou ja existentes).")
        else:
            print("FALHA — alguma coluna nao foi criada. Verificar erros acima.")
            sys.exit(1)
        print("=" * 78)


if __name__ == "__main__":
    executar_migration()
