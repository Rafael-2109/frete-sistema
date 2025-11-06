"""
Script Python para adicionar campo qtd_recebida à tabela pedido_compras

Uso:
    python scripts/adicionar_qtd_recebida_pedido_compras.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_qtd_recebida():
    app = create_app()

    with app.app_context():
        try:
            print("🔧 Adicionando campo qtd_recebida...")

            # 1. Adicionar coluna qtd_recebida
            print("   → Adicionando coluna qtd_recebida...")
            db.session.execute(text("""
                ALTER TABLE pedido_compras
                ADD COLUMN IF NOT EXISTS qtd_recebida NUMERIC(15, 3) DEFAULT 0;
            """))

            db.session.commit()
            print("   ✅ Coluna adicionada")

            # 2. Verificar se foi criada
            print("\n🔍 Verificando criação do campo...")
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'pedido_compras'
                AND column_name = 'qtd_recebida';
            """))

            campo = resultado.fetchone()
            if campo:
                print(f"✅ Campo qtd_recebida adicionado com sucesso!")
                print(f"   Tipo: {campo[1]}")
                print(f"   Default: {campo[2]}")
            else:
                print("❌ Erro: Campo não foi criado")
                return False

            # 3. Estatísticas
            print("\n📊 Estatísticas:")
            resultado = db.session.execute(text("""
                SELECT
                    COUNT(*) as total_pedidos,
                    COUNT(CASE WHEN qtd_recebida > 0 THEN 1 END) as com_recebimento,
                    COUNT(CASE WHEN qtd_recebida = 0 THEN 1 END) as sem_recebimento
                FROM pedido_compras
                WHERE importado_odoo = TRUE;
            """))

            stats = resultado.fetchone()
            print(f"   Total de pedidos: {stats[0]}")
            print(f"   Com recebimento: {stats[1]}")
            print(f"   Sem recebimento: {stats[2]}")

            print("\n✅ Script executado com sucesso!")
            print("\n📝 PRÓXIMO PASSO:")
            print("   Execute a sincronização do Odoo para preencher qtd_recebida")

            return True

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    adicionar_qtd_recebida()
