"""
Script para adicionar campos de controle em EmbarqueMoto:
- valor_frete_saldo: Saldo devedor do frete
- historico_status: JSON com histórico de mudanças de status
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_embarque():
    app = create_app()

    with app.app_context():
        try:
            print("🔧 Adicionando campos em embarque_moto...")

            # 1. Adicionar valor_frete_saldo
            print("\n1️⃣ Adicionando campo valor_frete_saldo...")
            db.session.execute(text("""
                ALTER TABLE embarque_moto
                ADD COLUMN IF NOT EXISTS valor_frete_saldo NUMERIC(15, 2) DEFAULT 0
            """))

            # 2. Adicionar historico_status
            print("2️⃣ Adicionando campo historico_status...")
            db.session.execute(text("""
                ALTER TABLE embarque_moto
                ADD COLUMN IF NOT EXISTS historico_status TEXT
            """))

            # 3. Atualizar valor_frete_saldo para embarques existentes
            print("3️⃣ Calculando saldo para embarques existentes...")
            db.session.execute(text("""
                UPDATE embarque_moto
                SET valor_frete_saldo = COALESCE(valor_frete_contratado, 0) - COALESCE(valor_frete_pago, 0)
                WHERE valor_frete_saldo IS NULL
            """))

            db.session.commit()
            print("✅ Campos adicionados com sucesso!")

            # Verificar
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'embarque_moto'
                AND column_name IN ('valor_frete_saldo', 'historico_status')
                ORDER BY column_name
            """)).fetchall()

            print("\n📊 Campos criados:")
            for row in resultado:
                print(f"   {row[0]}: {row[1]} (nullable: {row[2]})")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro: {e}")
            raise

if __name__ == '__main__':
    adicionar_campos_embarque()
