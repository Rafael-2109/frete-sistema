"""
Script para adicionar campo atualizado_em em pedido_compras

Executar: python scripts/adicionar_atualizado_em_pedido_compras.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_atualizado_em():
    """Adiciona campo atualizado_em na tabela pedido_compras"""
    app = create_app()

    with app.app_context():
        try:
            print("🔍 Verificando se campo atualizado_em já existe...")

            # Verificar se coluna existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name = 'atualizado_em'
            """))

            if resultado.fetchone():
                print("⚠️  Campo atualizado_em já existe! Nada a fazer.")
                return

            print("\n🔧 Adicionando campo atualizado_em...")

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD COLUMN atualizado_em TIMESTAMP DEFAULT NOW()
            """))

            # Atualizar registros existentes
            db.session.execute(text("""
                UPDATE pedido_compras
                SET atualizado_em = criado_em
                WHERE atualizado_em IS NULL
            """))

            # Commit
            db.session.commit()

            print("✅ Campo atualizado_em adicionado com sucesso!")

            # Verificar estrutura final
            resultado_final = db.session.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name IN ('criado_em', 'atualizado_em')
                ORDER BY column_name
            """))

            print("\n📋 Colunas de auditoria:")
            for col in resultado_final.fetchall():
                print(f"   - {col[0]}: {col[1]} (default: {col[2]})")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao executar script: {e}")
            print(f"   Tipo: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    print("="*60)
    print("Script: Adicionar campo atualizado_em em pedido_compras")
    print("="*60)
    adicionar_campo_atualizado_em()
