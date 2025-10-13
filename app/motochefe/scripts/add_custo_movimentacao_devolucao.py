"""
Script para adicionar campo custo_movimentacao_devolucao em CustosOperacionais
Executar localmente
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def add_campo_custo_movimentacao_devolucao():
    app = create_app()

    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='custos_operacionais'
                AND column_name='custo_movimentacao_devolucao'
            """))

            if resultado.fetchone():
                print("✅ Coluna 'custo_movimentacao_devolucao' já existe.")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE custos_operacionais
                ADD COLUMN custo_movimentacao_devolucao NUMERIC(15, 2) NOT NULL DEFAULT 0
            """))

            db.session.commit()
            print("✅ Coluna 'custo_movimentacao_devolucao' adicionada com sucesso!")
            print("⚠️  Configure o valor em CustosOperacionais vigente.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {e}")
            raise

if __name__ == '__main__':
    add_campo_custo_movimentacao_devolucao()
