"""
Script para adicionar campo tipo_pedido em pedido_compras

Executar: python scripts/adicionar_tipo_pedido_pedido_compras.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_tipo_pedido():
    """Adiciona campo tipo_pedido na tabela pedido_compras"""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Verificando se campo tipo_pedido já existe...")

            # Verificar se coluna existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name = 'tipo_pedido'
            """))

            if resultado.fetchone():
                print("⚠️  Campo tipo_pedido já existe! Nada a fazer.")
                return

            print("\n🔧 Adicionando campo tipo_pedido...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD COLUMN tipo_pedido VARCHAR(50)
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_pedido_compras_tipo_pedido
                ON pedido_compras(tipo_pedido)
            """))

            # Commit
            db.session.commit()

            print("✅ Campo tipo_pedido adicionado com sucesso!")

            # Verificar estrutura final
            resultado_final = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name = 'tipo_pedido'
            """))

            print("\n📋 Campo adicionado:")
            for col in resultado_final.fetchall():
                print(f"   - {col[0]}: {col[1]}({col[2]})")

            # Verificar índice
            indices = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'pedido_compras'
                AND indexname = 'ix_pedido_compras_tipo_pedido'
            """))

            if indices.fetchone():
                print("   - Índice criado: ix_pedido_compras_tipo_pedido ✅")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao executar script: {e}")
            print(f"   Tipo: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    print("="*60)
    print("Script: Adicionar campo tipo_pedido em pedido_compras")
    print("="*60)
    adicionar_campo_tipo_pedido()
