"""
Migration: Adicionar campo odoo_picking_id em pallet_nf_solucoes
================================================================

Adiciona campo para armazenar o ID do picking de devolução criado no Odoo
quando o usuário vincula uma NFD de devolução de pallet às NFs de remessa.

Executar localmente:
    source .venv/bin/activate
    python scripts/pallet/add_odoo_picking_id_nf_solucao.py

Executar no Render Shell (SQL):
    ALTER TABLE pallet_nf_solucoes ADD COLUMN IF NOT EXISTS odoo_picking_id INTEGER;
    CREATE INDEX IF NOT EXISTS idx_pallet_nf_solucao_odoo_picking ON pallet_nf_solucoes(odoo_picking_id);

Data: 2026-02-06
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            # Adicionar coluna
            db.session.execute(text(
                "ALTER TABLE pallet_nf_solucoes "
                "ADD COLUMN IF NOT EXISTS odoo_picking_id INTEGER"
            ))
            print("✅ Coluna odoo_picking_id adicionada")

            # Criar índice
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_pallet_nf_solucao_odoo_picking "
                "ON pallet_nf_solucoes(odoo_picking_id)"
            ))
            print("✅ Índice idx_pallet_nf_solucao_odoo_picking criado")

            db.session.commit()
            print("\n✅ Migration concluída com sucesso!")

        except Exception as e:
            print(f"\n❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
