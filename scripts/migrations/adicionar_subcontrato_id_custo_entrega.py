"""
Migration: Adicionar subcontrato_id em carvia_custos_entrega
=============================================================

Novo campo:
- subcontrato_id INTEGER NULLABLE FK → carvia_subcontratos(id) ON DELETE SET NULL

Permite vincular CustoEntrega ao Subcontrato que cobra este custo
(ex: diaria cobrada via CTe da transportadora). A FaturaTransportadora
e derivada via sub.fatura_transportadora_id.
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


def verificar_constraint_existe(conn, constraint_name):
    """Verifica se uma constraint existe."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = :nome
        )
    """), {'nome': constraint_name})
    return result.scalar()


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        tabela = 'carvia_custos_entrega'
        campo = 'subcontrato_id'
        constraint = 'fk_custo_entrega_subcontrato'
        indice = 'idx_carvia_custo_entrega_subcontrato_id'

        print(f"\n=== Migration: {campo} em {tabela} ===\n")

        # Before
        print("--- BEFORE ---")
        campo_existe = verificar_campo_existe(conn, tabela, campo)
        fk_existe = verificar_constraint_existe(conn, constraint)
        print(f"  {campo}: {'JA EXISTE' if campo_existe else 'NAO EXISTE'}")
        print(f"  {constraint}: {'JA EXISTE' if fk_existe else 'NAO EXISTE'}")

        # Aplicar
        print("\n--- APLICANDO ---")

        if not campo_existe:
            conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {campo} INTEGER"))
            print(f"  + {campo} (INTEGER)")
        else:
            print(f"  ~ {campo} ja existe (skip)")

        if not fk_existe:
            conn.execute(text(f"""
                ALTER TABLE {tabela}
                ADD CONSTRAINT {constraint}
                FOREIGN KEY ({campo}) REFERENCES carvia_subcontratos(id)
                ON DELETE SET NULL
            """))
            print(f"  + {constraint}")
        else:
            print(f"  ~ {constraint} ja existe (skip)")

        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {indice}
            ON {tabela} ({campo})
        """))
        print(f"  + {indice}")

        db.session.commit()

        # After
        print("\n--- AFTER ---")
        campo_existe = verificar_campo_existe(conn, tabela, campo)
        fk_existe = verificar_constraint_existe(conn, constraint)
        print(f"  {campo}: {'OK' if campo_existe else 'FALHA'}")
        print(f"  {constraint}: {'OK' if fk_existe else 'FALHA'}")

        if campo_existe and fk_existe:
            print("\n=== Migration concluida com SUCESSO ===\n")
        else:
            print("\n=== ATENCAO: Verificar falhas acima ===\n")


if __name__ == '__main__':
    main()
