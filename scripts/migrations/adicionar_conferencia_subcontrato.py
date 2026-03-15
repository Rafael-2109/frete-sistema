"""
Migration: Adicionar campos de conferencia em carvia_subcontratos
================================================================

Novos campos:
- valor_considerado NUMERIC(15,2) NULLABLE
- status_conferencia VARCHAR(20) DEFAULT 'PENDENTE'
- conferido_por VARCHAR(100) NULLABLE
- conferido_em TIMESTAMP NULLABLE
- detalhes_conferencia JSONB NULLABLE

Permite conferencia individual de CTe subcontratado contra tabelas de frete.
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


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        tabela = 'carvia_subcontratos'
        campos = {
            'valor_considerado': 'NUMERIC(15,2)',
            'status_conferencia': "VARCHAR(20) NOT NULL DEFAULT 'PENDENTE'",
            'conferido_por': 'VARCHAR(100)',
            'conferido_em': 'TIMESTAMP',
            'detalhes_conferencia': 'JSONB',
        }

        print(f"\n=== Migration: Conferencia em {tabela} ===\n")

        # Before: verificar estado atual
        print("--- BEFORE ---")
        for campo in campos:
            existe = verificar_campo_existe(conn, tabela, campo)
            print(f"  {campo}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

        # Aplicar alteracoes
        print("\n--- APLICANDO ---")
        for campo, tipo in campos.items():
            if not verificar_campo_existe(conn, tabela, campo):
                sql = f"ALTER TABLE {tabela} ADD COLUMN {campo} {tipo}"
                conn.execute(text(sql))
                print(f"  + {campo} ({tipo})")
            else:
                print(f"  ~ {campo} ja existe (skip)")

        # Criar indice para status_conferencia
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_carvia_subcontratos_status_conferencia
            ON carvia_subcontratos (status_conferencia)
        """))
        print("  + indice idx_carvia_subcontratos_status_conferencia")

        db.session.commit()

        # After: verificar resultado
        print("\n--- AFTER ---")
        for campo in campos:
            existe = verificar_campo_existe(conn, tabela, campo)
            status = 'OK' if existe else 'FALHA'
            print(f"  {campo}: {status}")

        print("\n=== Migration concluida com sucesso ===\n")


if __name__ == '__main__':
    main()
