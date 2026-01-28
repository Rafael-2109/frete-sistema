"""
Migration: Adiciona coluna nome_produto_interno em match_nf_po_item

Proposito: Armazenar o nome do produto interno (nosso nome) quando existe De-Para,
para exibicao na tela de Divergencias NF x PO.

Autor: Claude Code
Data: 2026-01-28
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Adiciona coluna nome_produto_interno na tabela match_nf_po_item."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna ja existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'match_nf_po_item'
                AND column_name = 'nome_produto_interno'
            """))

            if resultado.fetchone():
                print("Coluna nome_produto_interno ja existe em match_nf_po_item")
                return True

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE match_nf_po_item
                ADD COLUMN nome_produto_interno VARCHAR(255) NULL
            """))

            db.session.commit()
            print("SUCCESS: Coluna nome_produto_interno adicionada em match_nf_po_item")
            return True

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            return False


# SQL para rodar manualmente no Render Shell:
SQL_RENDER = """
-- Verificar se coluna existe
SELECT column_name FROM information_schema.columns
WHERE table_name = 'match_nf_po_item' AND column_name = 'nome_produto_interno';

-- Se nao existir, executar:
ALTER TABLE match_nf_po_item ADD COLUMN nome_produto_interno VARCHAR(255) NULL;
"""


if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Adicionar nome_produto_interno em match_nf_po_item")
    print("=" * 60)
    executar_migration()
    print("\n--- SQL para Render Shell ---")
    print(SQL_RENDER)
