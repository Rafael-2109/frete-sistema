"""
Script para corrigir constraint do PedidoCompras
Remove unique de num_pedido e adiciona constraint composta (num_pedido, cod_produto)

Executar: python scripts/corrigir_constraint_pedido_compras.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def corrigir_constraint_pedido_compras():
    """Remove unique de num_pedido e adiciona constraint composta"""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Verificando constraints existentes...")

            # Verificar constraints atuais
            resultado = db.session.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'pedido_compras'
                AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            """))

            constraints = resultado.fetchall()
            print(f"✅ Constraints encontradas: {len(constraints)}")
            for c in constraints:
                print(f"   - {c[0]} ({c[1]})")

            # Verificar se já existe a constraint composta
            check_composta = db.session.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'pedido_compras'
                AND constraint_name = 'uq_pedido_compras_num_cod_produto'
            """))

            if check_composta.fetchone():
                print("⚠️  Constraint composta já existe! Nada a fazer.")
                return

            print("\n🔧 Iniciando correção...")

            # 1. Dropar índice único de num_pedido
            print("1️⃣ Removendo índice único ix_pedido_compras_num_pedido...")
            try:
                db.session.execute(text("""
                    DROP INDEX IF EXISTS ix_pedido_compras_num_pedido CASCADE
                """))
                print("   ✅ Índice removido")
            except Exception as e:
                print(f"   ⚠️  Erro ao remover índice (pode não existir): {e}")

            # 2. Criar índice normal (não-único) para num_pedido
            print("2️⃣ Criando índice normal para num_pedido...")
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_pedido_compras_num_pedido
                    ON pedido_compras(num_pedido)
                """))
                print("   ✅ Índice normal criado")
            except Exception as e:
                print(f"   ⚠️  Erro ao criar índice: {e}")

            # 3. Adicionar constraint composta UNIQUE
            print("3️⃣ Adicionando constraint composta (num_pedido, cod_produto)...")
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD CONSTRAINT uq_pedido_compras_num_cod_produto
                UNIQUE (num_pedido, cod_produto)
            """))
            print("   ✅ Constraint composta adicionada")

            # Commit
            db.session.commit()

            print("\n✅ Correção concluída com sucesso!")
            print("\n📊 Verificando estrutura final...")

            # Verificar estrutura final
            resultado_final = db.session.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'pedido_compras'
                AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            """))

            constraints_final = resultado_final.fetchall()
            print(f"✅ Constraints finais: {len(constraints_final)}")
            for c in constraints_final:
                print(f"   - {c[0]} ({c[1]})")

            # Verificar índices
            indices = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'pedido_compras'
            """))

            print(f"\n📑 Índices:")
            for idx in indices.fetchall():
                print(f"   - {idx[0]}")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao executar script: {e}")
            print(f"   Tipo: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    print("="*60)
    print("Script: Corrigir Constraint PedidoCompras")
    print("="*60)
    corrigir_constraint_pedido_compras()
