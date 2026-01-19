"""
Migration: Adiciona campos para POs vinculados na tabela validacao_nf_po_dfe
============================================================================

Adiciona os campos:
- odoo_po_vinculado_id: ID do PO vinculado no Odoo
- odoo_po_vinculado_name: Nome do PO vinculado (ex: PO00123)
- odoo_po_fiscal_id: ID do PO fiscal (escrituracao)
- odoo_po_fiscal_name: Nome do PO fiscal
- pos_vinculados_importados_em: Data/hora da importacao

Estes campos armazenam informacoes dos POs que o Odoo ja vinculou
automaticamente ao DFE via campos purchase_id e purchase_fiscal_id.

Uso:
    source .venv/bin/activate
    python scripts/migrations/add_po_vinculado_campos.py
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
            # Verificar se campos ja existem
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe'
                AND column_name = 'odoo_po_vinculado_id'
            """))

            if result.fetchone():
                print("✓ Campos ja existem na tabela validacao_nf_po_dfe")
                return True

            # Adicionar novos campos
            db.session.execute(text("""
                ALTER TABLE validacao_nf_po_dfe
                ADD COLUMN IF NOT EXISTS odoo_po_vinculado_id INTEGER,
                ADD COLUMN IF NOT EXISTS odoo_po_vinculado_name VARCHAR(50),
                ADD COLUMN IF NOT EXISTS odoo_po_fiscal_id INTEGER,
                ADD COLUMN IF NOT EXISTS odoo_po_fiscal_name VARCHAR(50),
                ADD COLUMN IF NOT EXISTS pos_vinculados_importados_em TIMESTAMP
            """))

            # Criar indice para buscas
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_validacao_nf_po_dfe_odoo_po_vinculado_id
                ON validacao_nf_po_dfe (odoo_po_vinculado_id)
            """))

            db.session.commit()
            print("✓ Campos adicionados com sucesso na tabela validacao_nf_po_dfe")
            print("  - odoo_po_vinculado_id")
            print("  - odoo_po_vinculado_name")
            print("  - odoo_po_fiscal_id")
            print("  - odoo_po_fiscal_name")
            print("  - pos_vinculados_importados_em")
            return True

        except Exception as e:
            print(f"✗ Erro na migracao: {e}")
            db.session.rollback()
            return False


# Script SQL equivalente para rodar no Shell do Render:
SQL_RENDER = """
-- Adicionar campos de POs vinculados na tabela validacao_nf_po_dfe
ALTER TABLE validacao_nf_po_dfe
ADD COLUMN IF NOT EXISTS odoo_po_vinculado_id INTEGER,
ADD COLUMN IF NOT EXISTS odoo_po_vinculado_name VARCHAR(50),
ADD COLUMN IF NOT EXISTS odoo_po_fiscal_id INTEGER,
ADD COLUMN IF NOT EXISTS odoo_po_fiscal_name VARCHAR(50),
ADD COLUMN IF NOT EXISTS pos_vinculados_importados_em TIMESTAMP;

-- Criar indice para buscas
CREATE INDEX IF NOT EXISTS ix_validacao_nf_po_dfe_odoo_po_vinculado_id
ON validacao_nf_po_dfe (odoo_po_vinculado_id);
"""


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Migration: Adicionar campos POs vinculados")
    print("="*60 + "\n")

    success = run_migration()

    if success:
        print("\n" + "-"*60)
        print("SQL para executar no Shell do Render:")
        print("-"*60)
        print(SQL_RENDER)

    sys.exit(0 if success else 1)
