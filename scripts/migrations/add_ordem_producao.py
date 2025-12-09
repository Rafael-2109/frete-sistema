"""
Script de migração: Adicionar campo ordem_producao na tabela programacao_producao

Uso local:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source venv/bin/activate
    python scripts/migrations/add_ordem_producao.py

Autor: Claude Code
Data: 2025-12-09
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def add_ordem_producao():
    """Adiciona campo ordem_producao na tabela programacao_producao"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'programacao_producao'
                AND column_name = 'ordem_producao';
            """)

            result = db.session.execute(check_sql)
            if result.fetchone():
                print("✅ Coluna 'ordem_producao' já existe na tabela programacao_producao")
                return True

            # Adicionar coluna
            alter_sql = text("""
                ALTER TABLE programacao_producao
                ADD COLUMN ordem_producao VARCHAR(50) NULL;
            """)

            db.session.execute(alter_sql)
            db.session.commit()

            print("✅ Coluna 'ordem_producao' adicionada com sucesso!")
            print("   - Tipo: VARCHAR(50)")
            print("   - Nullable: True")
            return True

        except Exception as e:
            print(f"❌ Erro ao adicionar coluna: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    add_ordem_producao()
