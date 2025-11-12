#!/usr/bin/env python3
"""
Script de migração: Adicionar campos para rastreabilidade de Entradas de Materiais
==================================================================================

Adiciona 4 campos em MovimentacaoEstoque para vincular entradas com o Odoo:
- odoo_picking_id: ID do recebimento (stock.picking)
- odoo_move_id: ID do movimento (stock.move)
- purchase_line_id: ID da linha de pedido de compra
- pedido_compras_id: FK para tabela pedido_compras local

Autor: Sistema de Fretes
Data: 2025-01-11
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_entrada_material():
    """Adiciona campos de rastreabilidade de entradas de materiais"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRAÇÃO: Adicionar campos de rastreabilidade de Entradas")
            print("=" * 80)

            # Verificar se campos já existem
            print("\n1️⃣ Verificando campos existentes...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque'
                  AND column_name IN ('odoo_picking_id', 'odoo_move_id', 'purchase_line_id', 'pedido_compras_id')
                ORDER BY column_name;
            """))

            campos_existentes = {row[0] for row in resultado}
            print(f"   Campos já existentes: {campos_existentes if campos_existentes else 'Nenhum'}")

            # Adicionar odoo_picking_id
            if 'odoo_picking_id' not in campos_existentes:
                print("\n2️⃣ Adicionando campo odoo_picking_id...")
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS odoo_picking_id VARCHAR(50);
                """))
                print("   ✅ Campo odoo_picking_id adicionado")
            else:
                print("\n2️⃣ Campo odoo_picking_id já existe")

            # Adicionar odoo_move_id
            if 'odoo_move_id' not in campos_existentes:
                print("\n3️⃣ Adicionando campo odoo_move_id...")
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS odoo_move_id VARCHAR(50);
                """))
                print("   ✅ Campo odoo_move_id adicionado")
            else:
                print("\n3️⃣ Campo odoo_move_id já existe")

            # Adicionar purchase_line_id
            if 'purchase_line_id' not in campos_existentes:
                print("\n4️⃣ Adicionando campo purchase_line_id...")
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS purchase_line_id VARCHAR(50);
                """))
                print("   ✅ Campo purchase_line_id adicionado")
            else:
                print("\n4️⃣ Campo purchase_line_id já existe")

            # Adicionar pedido_compras_id
            if 'pedido_compras_id' not in campos_existentes:
                print("\n5️⃣ Adicionando campo pedido_compras_id...")
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN IF NOT EXISTS pedido_compras_id INTEGER;
                """))
                print("   ✅ Campo pedido_compras_id adicionado")
            else:
                print("\n5️⃣ Campo pedido_compras_id já existe")

            # Criar índices
            print("\n6️⃣ Criando índices...")

            # Índice odoo_picking_id
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_odoo_picking
                    ON movimentacao_estoque(odoo_picking_id);
                """))
                print("   ✅ Índice idx_movimentacao_odoo_picking criado")
            except Exception as e:
                print(f"   ⚠️  Índice idx_movimentacao_odoo_picking: {e}")

            # Índice odoo_move_id
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_odoo_move
                    ON movimentacao_estoque(odoo_move_id);
                """))
                print("   ✅ Índice idx_movimentacao_odoo_move criado")
            except Exception as e:
                print(f"   ⚠️  Índice idx_movimentacao_odoo_move: {e}")

            # Criar FK para pedido_compras (opcional, pode falhar se não existir a tabela)
            print("\n7️⃣ Criando FK para pedido_compras (se não existir)...")
            try:
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD CONSTRAINT fk_movimentacao_pedido_compras
                    FOREIGN KEY (pedido_compras_id)
                    REFERENCES pedido_compras(id)
                    ON DELETE SET NULL;
                """))
                print("   ✅ FK fk_movimentacao_pedido_compras criada")
            except Exception as e:
                print(f"   ⚠️  FK pode já existir ou tabela pedido_compras não existe: {e}")

            # Commit
            db.session.commit()

            # Verificar resultado final
            print("\n8️⃣ Verificando campos criados...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque'
                  AND column_name IN ('odoo_picking_id', 'odoo_move_id', 'purchase_line_id', 'pedido_compras_id')
                ORDER BY column_name;
            """))

            print("\n   Campos na tabela movimentacao_estoque:")
            for row in resultado:
                print(f"      - {row[0]}: {row[1]} (nullable={row[2]})")

            # Verificar índices
            resultado_indices = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'movimentacao_estoque'
                  AND indexname IN ('idx_movimentacao_odoo_picking', 'idx_movimentacao_odoo_move')
                ORDER BY indexname;
            """))

            print("\n   Índices criados:")
            for row in resultado_indices:
                print(f"      - {row[0]}")

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n💡 Próximos passos:")
            print("   1. Executar o mesmo SQL no Render (arquivo MIGRAR_RENDER.sql)")
            print("   2. Testar importação de entradas de materiais")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    print("\n🚀 Executando migração LOCAL...")
    sucesso = adicionar_campos_entrada_material()

    if sucesso:
        print("\n✅ Migração executada com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)
