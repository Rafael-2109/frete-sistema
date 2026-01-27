"""
Migration: Adicionar campo odoo_purchase_order_id na tabela pedido_compras
==========================================================================

PROBLEMA:
---------
O campo `odoo_id` da tabela `pedido_compras` armazena o ID da LINHA do PO
(`purchase.order.line`), mas em vários locais do sistema ele é usado como
se fosse o ID do HEADER do PO (`purchase.order`).

Isso causa erro ao tentar consolidar POs:
    Record does not exist or has been deleted.
    (Record: purchase.order(91890,), User: 42)

SOLUCAO:
--------
Adicionar novo campo `odoo_purchase_order_id` para armazenar explicitamente
o ID do header `purchase.order`, mantendo `odoo_id` como ID da linha.

CAMPOS APOS MIGRACAO:
- odoo_id: ID da linha (purchase.order.line) - MANTIDO (compatibilidade)
- odoo_purchase_order_id: ID do header (purchase.order) - NOVO

USO:
    python scripts/add_odoo_purchase_order_id.py

Autor: Sistema de Fretes
Data: 2026-01-26
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def executar():
    """Adiciona o campo odoo_purchase_order_id na tabela pedido_compras."""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("MIGRATION: Adicionar odoo_purchase_order_id em pedido_compras")
            print("=" * 70)

            # Verificar se o campo ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name = 'odoo_purchase_order_id'
            """))

            if resultado.fetchone():
                print("Campo odoo_purchase_order_id ja existe. Nada a fazer.")
                return

            # Adicionar o novo campo em pedido_compras
            print("Adicionando campo odoo_purchase_order_id em pedido_compras...")
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD COLUMN IF NOT EXISTS odoo_purchase_order_id VARCHAR(50);
            """))

            # Criar indice para o novo campo
            print("Criando indice idx_pedido_compras_odoo_po_id...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pedido_compras_odoo_po_id
                ON pedido_compras (odoo_purchase_order_id);
            """))

            # Adicionar comentario explicativo
            db.session.execute(text("""
                COMMENT ON COLUMN pedido_compras.odoo_purchase_order_id IS
                'ID do header purchase.order no Odoo. Diferente de odoo_id que e o ID da linha purchase.order.line';
            """))

            # Adicionar o campo no historico tambem
            print("Adicionando campo odoo_purchase_order_id em historico_pedido_compras...")
            db.session.execute(text("""
                ALTER TABLE historico_pedido_compras
                ADD COLUMN IF NOT EXISTS odoo_purchase_order_id VARCHAR(50);
            """))

            db.session.commit()

            print("-" * 70)
            print("SUCESSO!")
            print("-" * 70)
            print("Campo adicionado: odoo_purchase_order_id VARCHAR(50)")
            print("Indice criado: idx_pedido_compras_odoo_po_id")
            print("")
            print("PROXIMOS PASSOS:")
            print("1. Execute o script de correcao para preencher valores existentes:")
            print("   python scripts/fix_odoo_purchase_order_id_dados.py")
            print("2. Reinicie o scheduler para sincronizar novos pedidos")
            print("=" * 70)

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    executar()
