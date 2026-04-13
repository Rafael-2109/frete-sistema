"""Migration: adiciona campo cte_tomador em carvia_operacoes.

Tomador do frete extraido do CTe XML (<ide>/<toma3> ou <toma4>).
Valores: REMETENTE | EXPEDIDOR | RECEBEDOR | DESTINATARIO | TERCEIRO.

Idempotente: verifica information_schema antes de executar o ALTER.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_operacoes'
                  AND column_name = 'cte_tomador'
            """)).fetchone()

            if exists:
                print("[skip] Coluna carvia_operacoes.cte_tomador ja existe")
                return

            conn.execute(text(
                "ALTER TABLE carvia_operacoes "
                "ADD COLUMN cte_tomador VARCHAR(20)"
            ))
            conn.commit()
            print("[ok] Coluna carvia_operacoes.cte_tomador adicionada")


if __name__ == '__main__':
    main()
