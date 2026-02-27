"""
Migration: Adicionar campo odoo_product_uom_id na tabela produto_fornecedor_depara
===================================================================================

Armazena o ID da UoM no Odoo (uom.uom) localmente para que o sincronismo
bidirecional envie product_uom correto ao criar/atualizar product.supplierinfo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_odoo_product_uom_id.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def verificar_antes(engine):
    """Verifica estado antes da migration."""
    insp = inspect(engine)
    colunas = [c['name'] for c in insp.get_columns('produto_fornecedor_depara')]
    tem_campo = 'odoo_product_uom_id' in colunas
    print(f"[BEFORE] Tabela produto_fornecedor_depara: {len(colunas)} colunas")
    print(f"[BEFORE] Campo odoo_product_uom_id existe: {tem_campo}")
    return tem_campo


def executar_migration(engine):
    """Executa a migration."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE produto_fornecedor_depara
            ADD COLUMN IF NOT EXISTS odoo_product_uom_id INTEGER
        """))
        conn.execute(text("""
            COMMENT ON COLUMN produto_fornecedor_depara.odoo_product_uom_id
            IS 'ID da UoM no Odoo (uom.uom). Usado no sync para product.supplierinfo.product_uom'
        """))
        conn.commit()
    print("[OK] Campo odoo_product_uom_id adicionado com sucesso")


def verificar_depois(engine):
    """Verifica estado depois da migration."""
    insp = inspect(engine)
    colunas = [c['name'] for c in insp.get_columns('produto_fornecedor_depara')]
    tem_campo = 'odoo_product_uom_id' in colunas
    print(f"[AFTER] Tabela produto_fornecedor_depara: {len(colunas)} colunas")
    print(f"[AFTER] Campo odoo_product_uom_id existe: {tem_campo}")
    if not tem_campo:
        print("[ERRO] Campo NAO foi criado!")
        sys.exit(1)


def main():
    app = create_app()
    with app.app_context():
        engine = db.engine

        ja_existe = verificar_antes(engine)

        if ja_existe:
            print("[SKIP] Campo ja existe, nada a fazer")
            return

        executar_migration(engine)
        verificar_depois(engine)

    print("\n[CONCLUIDO] Migration executada com sucesso")


if __name__ == '__main__':
    main()
