"""
Migration: Adicionar coluna nfs_referenciadas_json em carvia_operacoes
======================================================================

Armazena as referencias de NF extraidas do CTe XML como JSONB.
Permite re-linking retroativo quando NF e importada APOS o CTe.

Formato:
[
  {"chave": "44digitos", "numero_nf": "33268", "cnpj_emitente": "12345678000199"},
  ...
]

Execucao:
    source .venv/bin/activate
    python scripts/migrations/add_nfs_referenciadas_json_operacoes.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()

        print("=" * 60)
        print("Migration: ADD nfs_referenciadas_json TO carvia_operacoes")
        print("=" * 60)

        # Verificar estado ANTES
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'carvia_operacoes'
              AND column_name = 'nfs_referenciadas_json'
        """))
        existe = result.fetchone()

        if existe:
            print("\n[OK] Coluna nfs_referenciadas_json ja existe. Nada a fazer.")
            return

        # Adicionar coluna
        print("\nAdicionando coluna nfs_referenciadas_json (JSONB)...")
        conn.execute(text("""
            ALTER TABLE carvia_operacoes
            ADD COLUMN nfs_referenciadas_json JSONB
        """))

        db.session.commit()

        # Verificar estado DEPOIS
        result = conn.execute(text("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'carvia_operacoes'
              AND column_name = 'nfs_referenciadas_json'
        """))
        row = result.fetchone()

        if row:
            print(f"\n[SUCESSO] Coluna criada: {row[0]} ({row[1]})")
        else:
            print("\n[ERRO] Coluna nao foi criada!")


if __name__ == '__main__':
    run_migration()
