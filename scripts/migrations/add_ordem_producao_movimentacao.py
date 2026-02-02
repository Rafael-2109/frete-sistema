"""
Migration: Adicionar campo ordem_producao na tabela movimentacao_estoque
Data: 2026-02-02
Descrição: Campo para identificar a Ordem de Produção (OP) associada à movimentação.
           Propagado da produção RAIZ para todos os componentes consumidos.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_ordem_producao_movimentacao():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se coluna já existe
            result = db.session.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'movimentacao_estoque' AND column_name = 'ordem_producao'
            """))
            if result.fetchone():
                print("✅ Coluna ordem_producao já existe em movimentacao_estoque")
                return

            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN ordem_producao VARCHAR(50) NULL
            """))
            print("✅ Coluna ordem_producao adicionada em movimentacao_estoque")

            # Criar índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_movimentacao_ordem_producao
                ON movimentacao_estoque(ordem_producao)
            """))
            print("✅ Índice idx_movimentacao_ordem_producao criado")

            db.session.commit()
            print("✅ Migration concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_ordem_producao_movimentacao()
