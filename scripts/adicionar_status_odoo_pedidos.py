#!/usr/bin/env python3
"""
Script para adicionar campo 'status_odoo' na tabela pedido_compras
===================================================================

Adiciona campo VARCHAR para armazenar o status real do Odoo:
- draft, sent, to approve, purchase, done, cancel

Autor: Sistema de Fretes
Data: 2025-11-03
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_status_odoo_pedidos():
    """Adiciona campo status_odoo à tabela pedido_compras"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 ADICIONANDO CAMPO 'status_odoo' EM pedido_compras")
            print("=" * 80)

            # Adicionar campo
            print("\n📝 Adicionando campo status_odoo...")
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD COLUMN IF NOT EXISTS status_odoo VARCHAR(20);
            """))

            print("   ✅ Campo adicionado")

            # Criar índice
            print("\n🔍 Criando índice para otimizar consultas por status...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pedido_status_odoo
                ON pedido_compras(status_odoo);
            """))
            print("   ✅ Índice criado")

            # Commit
            db.session.commit()

            print("\n" + "=" * 80)
            print("✅ CAMPO 'status_odoo' ADICIONADO COM SUCESSO!")
            print("=" * 80)
            print("\n📊 Valores possíveis:")
            print("   - draft: Rascunho")
            print("   - sent: Enviado")
            print("   - to approve: Aguardando Aprovação")
            print("   - purchase: Aprovado/Confirmado")
            print("   - done: Concluído")
            print("   - cancel: Cancelado")
            print("\n🔄 Próximo passo:")
            print("   Execute sincronização para popular o campo com dados do Odoo")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao adicionar campo: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    adicionar_status_odoo_pedidos()
