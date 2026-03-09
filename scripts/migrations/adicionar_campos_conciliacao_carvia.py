"""
Migration: Adicionar campos total_conciliado e conciliado em 3 tabelas CarVia
=============================================================================

ALTER em carvia_faturas_cliente, carvia_faturas_transportadora, carvia_despesas.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_campos_conciliacao_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def coluna_existe(tabela, coluna):
    result = db.session.execute(
        db.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :tabela AND column_name = :coluna)"
        ),
        {'tabela': tabela, 'coluna': coluna},
    )
    return result.scalar()


def adicionar_campos():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: Adicionar campos conciliacao em 3 tabelas")
        print("=" * 60)

        tabelas = [
            'carvia_faturas_cliente',
            'carvia_faturas_transportadora',
            'carvia_despesas',
        ]

        for tabela in tabelas:
            print(f"\n--- {tabela} ---")

            if coluna_existe(tabela, 'total_conciliado'):
                print(f"  [SKIP] total_conciliado ja existe")
            else:
                db.session.execute(db.text(
                    f"ALTER TABLE {tabela} "
                    f"ADD COLUMN total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0"
                ))
                print(f"  [OK] total_conciliado adicionado")

            if coluna_existe(tabela, 'conciliado'):
                print(f"  [SKIP] conciliado ja existe")
            else:
                db.session.execute(db.text(
                    f"ALTER TABLE {tabela} "
                    f"ADD COLUMN conciliado BOOLEAN NOT NULL DEFAULT FALSE"
                ))
                print(f"  [OK] conciliado adicionado")

        db.session.commit()
        print("\n[DONE] Migration concluida com sucesso")

        # Verificacao
        for tabela in tabelas:
            tc = coluna_existe(tabela, 'total_conciliado')
            co = coluna_existe(tabela, 'conciliado')
            print(f"  {tabela}: total_conciliado={'OK' if tc else 'FALHOU'}, conciliado={'OK' if co else 'FALHOU'}")


if __name__ == '__main__':
    adicionar_campos()
