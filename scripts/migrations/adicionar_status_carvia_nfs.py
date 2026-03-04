"""
Migration: Adicionar campo status + auditoria de cancelamento em carvia_nfs

Campos:
  - status VARCHAR(20) NOT NULL DEFAULT 'ATIVA'  (ATIVA / CANCELADA)
  - cancelado_em TIMESTAMP
  - cancelado_por VARCHAR(100)
  - motivo_cancelamento TEXT
  - Indice: ix_carvia_nfs_status

Idempotente: verifica existencia antes de criar.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    app = create_app()
    with app.app_context():
        # ---- BEFORE: verificar estado atual ----
        result = db.session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'carvia_nfs'
            ORDER BY ordinal_position
        """))
        colunas_antes = [r[0] for r in result]
        print(f"Colunas ANTES: {len(colunas_antes)} — {colunas_antes}")

        # ---- 1. Campo status ----
        if 'status' not in colunas_antes:
            db.session.execute(text("""
                ALTER TABLE carvia_nfs
                ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ATIVA'
            """))
            print("+ Coluna 'status' adicionada")
        else:
            print("= Coluna 'status' ja existe")

        # ---- 2. Campo cancelado_em ----
        if 'cancelado_em' not in colunas_antes:
            db.session.execute(text("""
                ALTER TABLE carvia_nfs ADD COLUMN cancelado_em TIMESTAMP
            """))
            print("+ Coluna 'cancelado_em' adicionada")
        else:
            print("= Coluna 'cancelado_em' ja existe")

        # ---- 3. Campo cancelado_por ----
        if 'cancelado_por' not in colunas_antes:
            db.session.execute(text("""
                ALTER TABLE carvia_nfs ADD COLUMN cancelado_por VARCHAR(100)
            """))
            print("+ Coluna 'cancelado_por' adicionada")
        else:
            print("= Coluna 'cancelado_por' ja existe")

        # ---- 4. Campo motivo_cancelamento ----
        if 'motivo_cancelamento' not in colunas_antes:
            db.session.execute(text("""
                ALTER TABLE carvia_nfs ADD COLUMN motivo_cancelamento TEXT
            """))
            print("+ Coluna 'motivo_cancelamento' adicionada")
        else:
            print("= Coluna 'motivo_cancelamento' ja existe")

        # ---- 5. Indice no status ----
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_carvia_nfs_status ON carvia_nfs (status)
        """))
        print("+ Indice ix_carvia_nfs_status criado/verificado")

        db.session.commit()

        # ---- AFTER: verificar estado final ----
        result = db.session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'carvia_nfs'
              AND column_name IN ('status', 'cancelado_em', 'cancelado_por', 'motivo_cancelamento')
            ORDER BY ordinal_position
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]} nullable={row[2]} default={row[3]}")

        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    run_migration()
