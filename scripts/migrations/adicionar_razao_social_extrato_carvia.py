"""
Migration: Adicionar razao_social e observacao em carvia_extrato_linhas
=====================================================================

Campos para enriquecer extrato bancário OFX com dados do CSV bancário:
- razao_social: nome da contraparte (importado do CSV)
- observacao: notas livres do usuário

Executar: python scripts/migrations/adicionar_razao_social_extrato_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import text


def coluna_existe(conn, tabela, coluna):
    result = conn.execute(
        text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :tabela AND column_name = :coluna
        """),
        {"tabela": tabela, "coluna": coluna}
    )
    return result.fetchone() is not None


def main():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        # --- BEFORE ---
        antes_razao = coluna_existe(conn, 'carvia_extrato_linhas', 'razao_social')
        antes_obs = coluna_existe(conn, 'carvia_extrato_linhas', 'observacao')
        print(f"BEFORE: razao_social={antes_razao}, observacao={antes_obs}")

        # --- APPLY ---
        if not antes_razao:
            conn.execute(
                text("ALTER TABLE carvia_extrato_linhas ADD COLUMN razao_social VARCHAR(255)")
            )
            print("  + razao_social VARCHAR(255) adicionado")
        else:
            print("  ~ razao_social ja existe (skip)")

        if not antes_obs:
            conn.execute(
                text("ALTER TABLE carvia_extrato_linhas ADD COLUMN observacao TEXT")
            )
            print("  + observacao TEXT adicionado")
        else:
            print("  ~ observacao ja existe (skip)")

        db.session.commit()

        # --- AFTER (nova conexao apos commit) ---
        conn2 = db.session.connection()
        depois_razao = coluna_existe(conn2, 'carvia_extrato_linhas', 'razao_social')
        depois_obs = coluna_existe(conn2, 'carvia_extrato_linhas', 'observacao')
        print(f"AFTER: razao_social={depois_razao}, observacao={depois_obs}")
        print("Migration concluida com sucesso.")


if __name__ == '__main__':
    main()
