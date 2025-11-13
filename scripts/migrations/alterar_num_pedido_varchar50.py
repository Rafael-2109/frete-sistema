"""
Script de Migration: Aumentar tamanho do campo num_pedido
==========================================================

PROBLEMA:
    Campo num_pedido na tabela movimentacao_estoque está com VARCHAR(30)
    mas precisa ser VARCHAR(50) para acomodar strings como:
    "Devolução de CD/CD/PALLET/03617" (33 caracteres)

SOLUÇÃO:
    Alterar num_pedido de VARCHAR(30) para VARCHAR(50)

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def alterar_num_pedido():
    """Altera o tamanho do campo num_pedido de VARCHAR(30) para VARCHAR(50)"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 MIGRATION: Alterando tamanho do campo num_pedido")
            print("=" * 80)

            # 1. Verificar tamanho atual
            print("\n1️⃣  Verificando tamanho atual do campo...")
            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque'
                  AND column_name = 'num_pedido';
            """))

            campo = resultado.fetchone()
            if campo:
                print(f"   ✅ Campo atual: {campo[0]} - {campo[1]}({campo[2]})")
            else:
                print("   ⚠️  Campo num_pedido não encontrado!")
                return

            # 2. Alterar tamanho do campo
            print("\n2️⃣  Alterando tamanho para VARCHAR(50)...")
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ALTER COLUMN num_pedido TYPE VARCHAR(50);
            """))

            # 3. Verificar alteração
            print("\n3️⃣  Verificando alteração...")
            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque'
                  AND column_name = 'num_pedido';
            """))

            campo_novo = resultado.fetchone()
            if campo_novo:
                print(f"   ✅ Campo alterado: {campo_novo[0]} - {campo_novo[1]}({campo_novo[2]})")

            # 4. Commit
            db.session.commit()

            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO durante migration: {e}")
            raise

if __name__ == '__main__':
    alterar_num_pedido()
