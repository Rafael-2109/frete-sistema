"""
Migration: Criar tabelas frota_veiculos e frota_despesas
Data: 2026-04-06
Descricao: Modulo de controle de despesas da frota propria
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
        existing_tables = inspector.get_table_names()

        # ── BEFORE ──
        print("=" * 60)
        print("BEFORE: Verificando estado atual")
        print(f"  frota_veiculos existe: {'frota_veiculos' in existing_tables}")
        print(f"  frota_despesas existe: {'frota_despesas' in existing_tables}")
        print("=" * 60)

        # ── APPLY ──
        sql_path = os.path.join(os.path.dirname(__file__), "criar_frota_veiculos.sql")
        with open(sql_path, "r") as f:
            sql_content = f.read()

        with db.engine.begin() as conn:
            conn.execute(text(sql_content))

        print("\n✅ Migration executada com sucesso!")

        # ── AFTER ──
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        print("\n" + "=" * 60)
        print("AFTER: Verificando resultado")
        print(f"  frota_veiculos existe: {'frota_veiculos' in existing_tables}")
        print(f"  frota_despesas existe: {'frota_despesas' in existing_tables}")

        if "frota_veiculos" in existing_tables:
            cols = [c["name"] for c in inspector.get_columns("frota_veiculos")]
            print(f"  frota_veiculos colunas ({len(cols)}): {', '.join(cols)}")

        if "frota_despesas" in existing_tables:
            cols = [c["name"] for c in inspector.get_columns("frota_despesas")]
            print(f"  frota_despesas colunas ({len(cols)}): {', '.join(cols)}")

        print("=" * 60)

        # Validacao
        if "frota_veiculos" not in existing_tables or "frota_despesas" not in existing_tables:
            print("\n❌ ERRO: Tabelas nao foram criadas!")
            sys.exit(1)

        print("\n✅ Validacao OK — ambas as tabelas existem.")


if __name__ == "__main__":
    main()
