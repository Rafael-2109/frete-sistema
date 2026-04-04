"""
Migration: Expandir precisao do percentual de comissao
======================================================

NUMERIC(5,4) → NUMERIC(10,8) em:
- carvia_comissao_fechamentos.percentual
- carvia_comissao_fechamento_ctes.percentual_snapshot

Permite percentuais como 3.49116% = fracao 0.0349116 (7 casas decimais).
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def get_column_type(conn, tabela, campo):
    """Retorna tipo atual do campo."""
    result = conn.execute(text("""
        SELECT data_type, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_name = :tabela AND column_name = :campo
    """), {'tabela': tabela, 'campo': campo})
    row = result.fetchone()
    if row:
        return f"{row[0]}({row[1]},{row[2]})"
    return 'NOT FOUND'


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        alteracoes = [
            ('carvia_comissao_fechamentos', 'percentual'),
            ('carvia_comissao_fechamento_ctes', 'percentual_snapshot'),
        ]

        print("\n=== Migration: Expandir precisao percentual comissao ===\n")

        # Before
        print("--- BEFORE ---")
        for tabela, campo in alteracoes:
            tipo = get_column_type(conn, tabela, campo)
            print(f"  {tabela}.{campo}: {tipo}")

        # Aplicar
        print("\n--- APLICANDO ---")
        for tabela, campo in alteracoes:
            conn.execute(text(f"""
                ALTER TABLE {tabela}
                ALTER COLUMN {campo} TYPE NUMERIC(10,8)
            """))
            print(f"  + {tabela}.{campo} → NUMERIC(10,8)")

        # Recriar CHECK constraint
        conn.execute(text("""
            ALTER TABLE carvia_comissao_fechamentos
            DROP CONSTRAINT IF EXISTS ck_comissao_percentual_range
        """))
        conn.execute(text("""
            ALTER TABLE carvia_comissao_fechamentos
            ADD CONSTRAINT ck_comissao_percentual_range
            CHECK (percentual > 0 AND percentual <= 1)
        """))
        print("  + CHECK constraint recriada")

        db.session.commit()

        # After
        print("\n--- AFTER ---")
        for tabela, campo in alteracoes:
            tipo = get_column_type(conn, tabela, campo)
            status = 'OK' if '10,8' in tipo else f'VERIFICAR ({tipo})'
            print(f"  {tabela}.{campo}: {status}")

        print("\n=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
