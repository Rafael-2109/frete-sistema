"""
Script para criar a tabela match_nf_po_alocacao.

Permite split de itens da NF entre multiplos POs.

Uso local:
    source .venv/bin/activate
    python scripts/criar_tabela_match_alocacao.py

Uso no Render (Shell):
    Executar o SQL diretamente
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria a tabela match_nf_po_alocacao se nao existir."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se tabela ja existe
            resultado = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'match_nf_po_alocacao'
                )
            """))
            existe = resultado.scalar()

            if existe:
                print("Tabela match_nf_po_alocacao ja existe.")
                return True

            # Criar tabela
            print("Criando tabela match_nf_po_alocacao...")
            db.session.execute(text("""
                CREATE TABLE match_nf_po_alocacao (
                    id SERIAL PRIMARY KEY,
                    match_item_id INTEGER NOT NULL REFERENCES match_nf_po_item(id) ON DELETE CASCADE,
                    odoo_po_id INTEGER NOT NULL,
                    odoo_po_name VARCHAR(50),
                    odoo_po_line_id INTEGER NOT NULL,
                    qtd_alocada NUMERIC(15,3) NOT NULL,
                    preco_po NUMERIC(15,4),
                    data_po DATE,
                    ordem INTEGER DEFAULT 1,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Criar indices
            print("Criando indices...")
            db.session.execute(text("""
                CREATE INDEX idx_match_alocacao_match_item
                ON match_nf_po_alocacao(match_item_id)
            """))

            db.session.execute(text("""
                CREATE INDEX idx_match_alocacao_po
                ON match_nf_po_alocacao(odoo_po_id, odoo_po_line_id)
            """))

            db.session.commit()
            print("Tabela match_nf_po_alocacao criada com sucesso!")
            return True

        except Exception as e:
            print(f"Erro ao criar tabela: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    criar_tabela()
