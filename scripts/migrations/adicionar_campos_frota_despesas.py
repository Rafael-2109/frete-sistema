"""
Migration: Adicionar arquivo_path e fornecedor em frota_despesas
Data: 2026-04-06
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text, inspect


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_before = [c["name"] for c in inspector.get_columns("frota_despesas")]

        print("=" * 60)
        print(f"BEFORE: colunas ({len(cols_before)}): {', '.join(cols_before)}")
        print(f"  arquivo_path existe: {'arquivo_path' in cols_before}")
        print(f"  fornecedor existe: {'fornecedor' in cols_before}")
        print("=" * 60)

        sql_path = os.path.join(os.path.dirname(__file__), "adicionar_campos_frota_despesas.sql")
        with open(sql_path, "r") as f:
            sql_content = f.read()

        with db.engine.begin() as conn:
            conn.execute(text(sql_content))

        print("\n✅ Migration executada!")

        inspector = inspect(db.engine)
        cols_after = [c["name"] for c in inspector.get_columns("frota_despesas")]

        print(f"\nAFTER: colunas ({len(cols_after)}): {', '.join(cols_after)}")
        print(f"  arquivo_path existe: {'arquivo_path' in cols_after}")
        print(f"  fornecedor existe: {'fornecedor' in cols_after}")
        print("=" * 60)

        if "arquivo_path" not in cols_after or "fornecedor" not in cols_after:
            print("❌ ERRO: Colunas nao foram adicionadas!")
            sys.exit(1)

        print("✅ Validacao OK.")


if __name__ == "__main__":
    main()
