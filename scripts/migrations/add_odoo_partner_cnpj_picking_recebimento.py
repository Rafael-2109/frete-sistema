"""
Migration: Adiciona campo odoo_partner_cnpj na tabela picking_recebimento
==========================================================================

Adiciona o campo:
- odoo_partner_cnpj: CNPJ do fornecedor (vem do res.partner.l10n_br_cnpj)

Este campo permite filtrar pickings de fornecedores do grupo interno
(transferencias entre empresas) que nao devem aparecer na tela de
recebimento fisico.

Prefixos de CNPJs do grupo interno a serem excluidos:
- 61724241 (Nacom Goya)
- 18467441 (La Famiglia)

Uso:
    source .venv/bin/activate
    python scripts/migrations/add_odoo_partner_cnpj_picking_recebimento.py
"""

import sys
import os

# Adiciona o diretorio raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def run_migration():
    """Executa a migracao"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se campo ja existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'picking_recebimento'
                AND column_name = 'odoo_partner_cnpj'
            """))

            if result.fetchone():
                print("✓ Campo odoo_partner_cnpj ja existe na tabela picking_recebimento")
                return True

            # Adicionar novo campo
            db.session.execute(text("""
                ALTER TABLE picking_recebimento
                ADD COLUMN IF NOT EXISTS odoo_partner_cnpj VARCHAR(20)
            """))

            # Criar indice para buscas/filtros por prefixo de CNPJ
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_picking_rec_partner_cnpj
                ON picking_recebimento (odoo_partner_cnpj)
            """))

            db.session.commit()
            print("✓ Campo adicionado com sucesso na tabela picking_recebimento")
            print("  - odoo_partner_cnpj (VARCHAR(20))")
            print("  - Indice idx_picking_rec_partner_cnpj criado")
            return True

        except Exception as e:
            print(f"✗ Erro na migracao: {e}")
            db.session.rollback()
            return False


# Script SQL equivalente para rodar no Shell do Render:
SQL_RENDER = """
-- Adicionar campo CNPJ do fornecedor na tabela picking_recebimento
ALTER TABLE picking_recebimento
ADD COLUMN IF NOT EXISTS odoo_partner_cnpj VARCHAR(20);

-- Criar indice para filtros por prefixo de CNPJ
CREATE INDEX IF NOT EXISTS idx_picking_rec_partner_cnpj
ON picking_recebimento (odoo_partner_cnpj);
"""


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Migration: Adicionar campo odoo_partner_cnpj")
    print("="*60 + "\n")

    success = run_migration()

    if success:
        print("\n" + "-"*60)
        print("SQL para executar no Shell do Render:")
        print("-"*60)
        print(SQL_RENDER)
        print("\n" + "-"*60)
        print("PROXIMO PASSO:")
        print("-"*60)
        print("Apos rodar a migration, execute uma sincronizacao de pickings")
        print("para popular o campo odoo_partner_cnpj:")
        print("")
        print("  source .venv/bin/activate")
        print("  python -c \"")
        print("from app import create_app")
        print("from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService")
        print("app = create_app()")
        print("with app.app_context():")
        print("    service = PickingRecebimentoSyncService()")
        print("    result = service.sincronizar_por_periodo('2024-01-01', '2026-12-31')")
        print("    print(result)")
        print("\"")

    sys.exit(0 if success else 1)
