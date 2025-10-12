"""
Script de Migração: Adicionar campo numero_nf_importada
Executar LOCALMENTE via: python app/motochefe/scripts/migration_nf_importada_local.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campo_nf_importada():
    app = create_app()

    with app.app_context():
        try:
            # Verificar se campo já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='pedido_venda_moto'
                AND column_name='numero_nf_importada'
            """))

            if resultado.fetchone():
                print("✅ Campo 'numero_nf_importada' já existe!")
                return

            # Adicionar campo
            db.session.execute(text("""
                ALTER TABLE pedido_venda_moto
                ADD COLUMN numero_nf_importada VARCHAR(20) NULL
            """))

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX idx_pedido_venda_moto_nf_importada
                ON pedido_venda_moto(numero_nf_importada)
            """))

            db.session.commit()
            print("✅ Campo 'numero_nf_importada' adicionado com sucesso!")
            print("✅ Índice criado com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO: {str(e)}")
            raise

if __name__ == '__main__':
    adicionar_campo_nf_importada()
