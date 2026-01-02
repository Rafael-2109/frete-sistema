"""
Migration: Criar tabela descarte_item para itens do descarte
Data: 2026-01-01
Descricao: Tabela para armazenar os itens descartados com quantidades editaveis
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabela ja existe
            resultado = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'descarte_item'
            """))

            if resultado.fetchone():
                print("Tabela 'descarte_item' ja existe. Migration ignorada.")
                return

            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE descarte_item (
                    id SERIAL PRIMARY KEY,
                    descarte_id INTEGER NOT NULL REFERENCES descarte_devolucao(id) ON DELETE CASCADE,
                    nfd_linha_id INTEGER NOT NULL REFERENCES nf_devolucao_linha(id) ON DELETE CASCADE,
                    quantidade_descarte NUMERIC(15,3) NOT NULL DEFAULT 0,
                    quantidade_caixas NUMERIC(15,3) NOT NULL DEFAULT 0,
                    valor_descarte NUMERIC(15,2) NOT NULL DEFAULT 0,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                )
            """))

            # Criar indices
            db.session.execute(text("""
                CREATE INDEX idx_descarte_item_descarte_id ON descarte_item(descarte_id);
                CREATE INDEX idx_descarte_item_nfd_linha_id ON descarte_item(nfd_linha_id);
            """))

            db.session.commit()
            print("Tabela 'descarte_item' criada com sucesso!")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    executar_migration()
