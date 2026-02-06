"""
Migration: Adicionar campo atualizado_em e unique constraint em recebimento_lf
===============================================================================

Aplica alteracoes incrementais na tabela recebimento_lf ja existente:
1. Adiciona coluna atualizado_em (TIMESTAMP)
2. Troca index de odoo_dfe_id para UNIQUE (previne duplicatas)

Executar:
    source .venv/bin/activate
    python scripts/recebimento/004_alter_recebimento_lf_add_atualizado_em.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    """Aplica alteracoes incrementais em recebimento_lf."""
    app = create_app()
    with app.app_context():
        try:
            # 1. Adicionar coluna atualizado_em (se nao existir)
            print("1. Adicionando coluna atualizado_em...")
            db.session.execute(text("""
                ALTER TABLE recebimento_lf
                ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            db.session.commit()
            print("   OK")

            # 2. Dropar index nao-unique de odoo_dfe_id (se existir)
            print("2. Removendo index nao-unique de odoo_dfe_id...")
            db.session.execute(text("""
                DROP INDEX IF EXISTS ix_recebimento_lf_odoo_dfe_id
            """))
            db.session.commit()
            print("   OK")

            # 3. Criar unique index em odoo_dfe_id
            print("3. Criando UNIQUE index em odoo_dfe_id...")
            db.session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_recebimento_lf_odoo_dfe_id
                ON recebimento_lf (odoo_dfe_id)
            """))
            db.session.commit()
            print("   OK")

            print("\nMigration 004 concluida com sucesso!")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
