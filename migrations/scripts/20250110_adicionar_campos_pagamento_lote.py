"""
Migração: Adicionar campos para controle de pagamento em lote
Data: 10/01/2025

Adiciona campos:
- empresa_pagadora_id e lote_pagamento_id em Moto
- empresa_pagadora_id e lote_pagamento_id em ComissaoVendedor
- empresa_pagadora_montagem_id e lote_pagamento_montagem_id em PedidoVendaMotoItem
"""
import sys
import os

# Adicionar o diretório raiz do projeto ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_pagamento_lote():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("MIGRAÇÃO: Adicionar campos para controle de pagamento em lote")
            print("=" * 80)

            # 1. TABELA MOTO
            print("\n[1/3] Adicionando campos em 'moto'...")

            # Verificar se empresa_pagadora_id já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='moto' AND column_name='empresa_pagadora_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando empresa_pagadora_id...")
                # Primeiro adicionar coluna
                db.session.execute(text("ALTER TABLE moto ADD COLUMN empresa_pagadora_id INTEGER"))
                print("    ✓ Coluna criada")

                # Depois adicionar FK
                db.session.execute(text("""
                    ALTER TABLE moto
                    ADD CONSTRAINT fk_moto_empresa_pagadora
                    FOREIGN KEY (empresa_pagadora_id)
                    REFERENCES empresa_venda_moto(id)
                """))
                print("    ✓ FK criada")

                # Depois criar índice
                db.session.execute(text("CREATE INDEX idx_moto_empresa_pagadora ON moto(empresa_pagadora_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo empresa_pagadora_id já existe, pulando...")

            # Verificar se lote_pagamento_id já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='moto' AND column_name='lote_pagamento_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando lote_pagamento_id...")
                db.session.execute(text("ALTER TABLE moto ADD COLUMN lote_pagamento_id INTEGER"))
                print("    ✓ Coluna criada")

                db.session.execute(text("CREATE INDEX idx_moto_lote_pagamento ON moto(lote_pagamento_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo lote_pagamento_id já existe, pulando...")

            # 2. TABELA COMISSAO_VENDEDOR
            print("\n[2/3] Adicionando campos em 'comissao_vendedor'...")

            # Verificar empresa_pagadora_id
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='comissao_vendedor' AND column_name='empresa_pagadora_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando empresa_pagadora_id...")
                db.session.execute(text("ALTER TABLE comissao_vendedor ADD COLUMN empresa_pagadora_id INTEGER"))
                print("    ✓ Coluna criada")

                db.session.execute(text("""
                    ALTER TABLE comissao_vendedor
                    ADD CONSTRAINT fk_comissao_empresa_pagadora
                    FOREIGN KEY (empresa_pagadora_id)
                    REFERENCES empresa_venda_moto(id)
                """))
                print("    ✓ FK criada")

                db.session.execute(text("CREATE INDEX idx_comissao_empresa_pagadora ON comissao_vendedor(empresa_pagadora_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo empresa_pagadora_id já existe, pulando...")

            # Verificar lote_pagamento_id
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='comissao_vendedor' AND column_name='lote_pagamento_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando lote_pagamento_id...")
                db.session.execute(text("ALTER TABLE comissao_vendedor ADD COLUMN lote_pagamento_id INTEGER"))
                print("    ✓ Coluna criada")

                db.session.execute(text("CREATE INDEX idx_comissao_lote_pagamento ON comissao_vendedor(lote_pagamento_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo lote_pagamento_id já existe, pulando...")

            # 3. TABELA PEDIDO_VENDA_MOTO_ITEM
            print("\n[3/3] Adicionando campos em 'pedido_venda_moto_item'...")

            # Verificar empresa_pagadora_montagem_id
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='pedido_venda_moto_item' AND column_name='empresa_pagadora_montagem_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando empresa_pagadora_montagem_id...")
                db.session.execute(text("ALTER TABLE pedido_venda_moto_item ADD COLUMN empresa_pagadora_montagem_id INTEGER"))
                print("    ✓ Coluna criada")

                db.session.execute(text("""
                    ALTER TABLE pedido_venda_moto_item
                    ADD CONSTRAINT fk_item_empresa_pagadora_montagem
                    FOREIGN KEY (empresa_pagadora_montagem_id)
                    REFERENCES empresa_venda_moto(id)
                """))
                print("    ✓ FK criada")

                db.session.execute(text("CREATE INDEX idx_item_empresa_pagadora_montagem ON pedido_venda_moto_item(empresa_pagadora_montagem_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo empresa_pagadora_montagem_id já existe, pulando...")

            # Verificar lote_pagamento_montagem_id
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='pedido_venda_moto_item' AND column_name='lote_pagamento_montagem_id'
            """))

            if result.fetchone() is None:
                print("  → Adicionando lote_pagamento_montagem_id...")
                db.session.execute(text("ALTER TABLE pedido_venda_moto_item ADD COLUMN lote_pagamento_montagem_id INTEGER"))
                print("    ✓ Coluna criada")

                db.session.execute(text("CREATE INDEX idx_item_lote_pagamento_montagem ON pedido_venda_moto_item(lote_pagamento_montagem_id)"))
                print("    ✓ Índice criado")
            else:
                print("  ⚠ Campo lote_pagamento_montagem_id já existe, pulando...")

            # COMMIT
            db.session.commit()

            print("\n" + "=" * 80)
            print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\nResumo:")
            print("  • Tabela 'moto': empresa_pagadora_id, lote_pagamento_id")
            print("  • Tabela 'comissao_vendedor': empresa_pagadora_id, lote_pagamento_id")
            print("  • Tabela 'pedido_venda_moto_item': empresa_pagadora_montagem_id, lote_pagamento_montagem_id")
            print("\nTodos os campos possuem índices para otimização de consultas.")

        except Exception as e:
            db.session.rollback()
            print("\n" + "=" * 80)
            print("❌ ERRO NA MIGRAÇÃO:")
            print("=" * 80)
            print(f"{str(e)}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    adicionar_campos_pagamento_lote()
