"""
Migration: Adicionar campos atualizado_em e atualizado_por em tabelas_frete.

Permite rastrear quem e quando atualizou uma tabela de frete,
sem sobrescrever criado_por/criado_em originais.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_atualizado_tabelas_frete.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(coluna):
    """Verifica se coluna existe na tabela tabelas_frete."""
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tabelas_frete' AND column_name = :col
    """), {'col': coluna})
    return result.fetchone() is not None


def main():
    app = create_app()
    with app.app_context():
        colunas = [
            ('atualizado_em', 'TIMESTAMP'),
            ('atualizado_por', 'VARCHAR(120)'),
        ]

        # Before: verificar estado atual
        print("=== BEFORE ===")
        for col, _ in colunas:
            existe = verificar_coluna_existe(col)
            print(f"  {col}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

        # Aplicar DDL
        for col, tipo in colunas:
            if not verificar_coluna_existe(col):
                db.session.execute(text(
                    f"ALTER TABLE tabelas_frete ADD COLUMN {col} {tipo}"
                ))
                print(f"  + {col} adicionado")
            else:
                print(f"  ~ {col} ja existia, pulando")

        db.session.commit()

        # After: confirmar
        print("\n=== AFTER ===")
        for col, _ in colunas:
            existe = verificar_coluna_existe(col)
            status = 'OK' if existe else 'FALHOU'
            print(f"  {col}: {status}")

        print("\nMigration concluida.")


if __name__ == '__main__':
    main()
