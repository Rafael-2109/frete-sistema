"""
Migration: Adicionar campos odoo_status, odoo_job_id, odoo_erro em pallet_nf_solucoes
======================================================================================

Campos para rastrear o processamento assíncrono de devoluções no Odoo via worker.

- odoo_status: 'pendente', 'processando', 'concluido', 'erro' (ou NULL)
- odoo_job_id: ID do job no Redis Queue (para polling)
- odoo_erro: Mensagem de erro se falhou

Executar localmente:
    source .venv/bin/activate
    python scripts/pallet/add_odoo_status_nf_solucao.py

Executar no Render Shell (SQL):
    ALTER TABLE pallet_nf_solucoes ADD COLUMN IF NOT EXISTS odoo_status VARCHAR(20);
    ALTER TABLE pallet_nf_solucoes ADD COLUMN IF NOT EXISTS odoo_job_id VARCHAR(100);
    ALTER TABLE pallet_nf_solucoes ADD COLUMN IF NOT EXISTS odoo_erro TEXT;
    CREATE INDEX IF NOT EXISTS idx_pallet_nf_solucao_odoo_status ON pallet_nf_solucoes(odoo_status);

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
            # Adicionar coluna odoo_status
            db.session.execute(text(
                "ALTER TABLE pallet_nf_solucoes "
                "ADD COLUMN IF NOT EXISTS odoo_status VARCHAR(20)"
            ))
            print("  Coluna odoo_status adicionada")

            # Adicionar coluna odoo_job_id
            db.session.execute(text(
                "ALTER TABLE pallet_nf_solucoes "
                "ADD COLUMN IF NOT EXISTS odoo_job_id VARCHAR(100)"
            ))
            print("  Coluna odoo_job_id adicionada")

            # Adicionar coluna odoo_erro
            db.session.execute(text(
                "ALTER TABLE pallet_nf_solucoes "
                "ADD COLUMN IF NOT EXISTS odoo_erro TEXT"
            ))
            print("  Coluna odoo_erro adicionada")

            # Criar índice em odoo_status
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_pallet_nf_solucao_odoo_status "
                "ON pallet_nf_solucoes(odoo_status)"
            ))
            print("  Indice idx_pallet_nf_solucao_odoo_status criado")

            db.session.commit()
            print("\n  Migration concluida com sucesso!")

        except Exception as e:
            print(f"\n  Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
