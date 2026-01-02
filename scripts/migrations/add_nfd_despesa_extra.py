"""
Migração: Adicionar campos nfd_id e numero_nfd na tabela despesas_extras
Para vincular despesas de devolução às NFDs correspondentes
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def add_campos_nfd():
    """Adiciona campos nfd_id e numero_nfd em despesas_extras"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'despesas_extras'
                AND column_name = 'nfd_id'
            """))
            if resultado.fetchone():
                print("Campo nfd_id já existe em despesas_extras")
            else:
                # Adicionar coluna nfd_id
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN nfd_id INTEGER REFERENCES nf_devolucao(id)
                """))
                print("Campo nfd_id adicionado")

            # Verificar numero_nfd
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'despesas_extras'
                AND column_name = 'numero_nfd'
            """))
            if resultado.fetchone():
                print("Campo numero_nfd já existe em despesas_extras")
            else:
                # Adicionar coluna numero_nfd
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN numero_nfd VARCHAR(20)
                """))
                print("Campo numero_nfd adicionado")

            # Criar índice
            resultado = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'despesas_extras'
                AND indexname = 'idx_despesas_extras_nfd'
            """))
            if resultado.fetchone():
                print("Índice idx_despesas_extras_nfd já existe")
            else:
                db.session.execute(text("""
                    CREATE INDEX idx_despesas_extras_nfd ON despesas_extras(nfd_id)
                """))
                print("Índice idx_despesas_extras_nfd criado")

            db.session.commit()
            print("Migração concluída com sucesso!")

        except Exception as e:
            print(f"Erro na migração: {e}")
            db.session.rollback()
            raise


# SQL para execução direta no Render Shell:
SQL_RENDER = """
-- Adicionar campos de NFD em despesas_extras
ALTER TABLE despesas_extras ADD COLUMN IF NOT EXISTS nfd_id INTEGER REFERENCES nf_devolucao(id);
ALTER TABLE despesas_extras ADD COLUMN IF NOT EXISTS numero_nfd VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_despesas_extras_nfd ON despesas_extras(nfd_id);
"""


if __name__ == '__main__':
    print("Executando migração...")
    add_campos_nfd()
    print("\n--- SQL para Render Shell ---")
    print(SQL_RENDER)
