"""
Migration: Adicionar FK despesa_id em carvia_comissao_fechamentos
=================================================================

Vincula comissao a despesa para integracao com conciliacao bancaria.

Novos artefatos:
- despesa_id INTEGER NULLABLE FK -> carvia_despesas(id) ON DELETE SET NULL
- Unique index parcial (despesa_id) WHERE despesa_id IS NOT NULL
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_campo_existe(conn, tabela, campo):
    """Verifica se um campo existe na tabela."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :campo
        )
    """), {'tabela': tabela, 'campo': campo})
    return result.scalar()


def verificar_index_existe(conn, index_name):
    """Verifica se um index existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :index_name
        )
    """), {'index_name': index_name})
    return result.scalar()


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        tabela = 'carvia_comissao_fechamentos'
        campo = 'despesa_id'
        index_name = 'uq_comissao_fechamentos_despesa_id'

        print(f"\n=== Migration: FK despesa_id em {tabela} ===\n")

        # Before
        print("--- BEFORE ---")
        existe_campo = verificar_campo_existe(conn, tabela, campo)
        existe_index = verificar_index_existe(conn, index_name)
        print(f"  {campo}: {'JA EXISTE' if existe_campo else 'NAO EXISTE'}")
        print(f"  {index_name}: {'JA EXISTE' if existe_index else 'NAO EXISTE'}")

        # Aplicar
        print("\n--- APLICANDO ---")
        if not existe_campo:
            conn.execute(text(f"""
                ALTER TABLE {tabela}
                ADD COLUMN {campo} INTEGER REFERENCES carvia_despesas(id) ON DELETE SET NULL
            """))
            print(f"  + {campo} (INTEGER FK -> carvia_despesas)")
        else:
            print(f"  ~ {campo} ja existe (skip)")

        if not existe_index:
            conn.execute(text(f"""
                CREATE UNIQUE INDEX {index_name}
                ON {tabela} ({campo}) WHERE {campo} IS NOT NULL
            """))
            print(f"  + {index_name}")
        else:
            print(f"  ~ {index_name} ja existe (skip)")

        db.session.commit()

        # After
        print("\n--- AFTER ---")
        existe_campo = verificar_campo_existe(conn, tabela, campo)
        existe_index = verificar_index_existe(conn, index_name)
        print(f"  {campo}: {'OK' if existe_campo else 'FALHA'}")
        print(f"  {index_name}: {'OK' if existe_index else 'FALHA'}")

        print("\n=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
