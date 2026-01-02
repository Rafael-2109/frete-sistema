"""
Migration: Adiciona campos de conversao em NFDevolucaoLinha
============================================================

Campos adicionados:
- quantidade_convertida: Quantidade convertida para caixas
- qtd_por_caixa: Quantidade de unidades por caixa do nosso produto

Data: 01/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Adiciona campos de conversao na tabela nf_devolucao_linha"""
    app = create_app()

    with app.app_context():
        try:
            # Adicionar campo quantidade_convertida
            print("Adicionando campo quantidade_convertida...")
            db.session.execute(text("""
                ALTER TABLE nf_devolucao_linha
                ADD COLUMN IF NOT EXISTS quantidade_convertida NUMERIC(15, 3)
            """))

            # Adicionar campo qtd_por_caixa
            print("Adicionando campo qtd_por_caixa...")
            db.session.execute(text("""
                ALTER TABLE nf_devolucao_linha
                ADD COLUMN IF NOT EXISTS qtd_por_caixa INTEGER
            """))

            db.session.commit()
            print("Migration executada com sucesso!")

        except Exception as e:
            print(f"Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    executar_migration()
