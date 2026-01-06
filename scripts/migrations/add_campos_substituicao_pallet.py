"""
Script de migração para adicionar campos de substituição de pallet
na tabela movimentacao_estoque.

Campos adicionados:
- nf_remessa_origem: NF original da transportadora que foi substituida
- cnpj_responsavel: CNPJ de quem é responsável pelo retorno
- nome_responsavel: Nome do responsável

Data: 2026-01-05
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campos():
    """Adiciona os campos de substituição de pallet"""
    app = create_app()
    with app.app_context():
        try:
            # Adicionar campo nf_remessa_origem
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN IF NOT EXISTS nf_remessa_origem VARCHAR(20);
            """))
            print("✅ Campo nf_remessa_origem adicionado")

            # Adicionar campo cnpj_responsavel
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN IF NOT EXISTS cnpj_responsavel VARCHAR(20);
            """))
            print("✅ Campo cnpj_responsavel adicionado")

            # Adicionar campo nome_responsavel
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN IF NOT EXISTS nome_responsavel VARCHAR(255);
            """))
            print("✅ Campo nome_responsavel adicionado")

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_movimentacao_nf_remessa_origem
                ON movimentacao_estoque(nf_remessa_origem);
            """))
            print("✅ Índice idx_movimentacao_nf_remessa_origem criado")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_movimentacao_cnpj_responsavel
                ON movimentacao_estoque(cnpj_responsavel);
            """))
            print("✅ Índice idx_movimentacao_cnpj_responsavel criado")

            db.session.commit()
            print("\n✅ Migration concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRATION: Campos de Substituição de Pallet")
    print("=" * 60)
    adicionar_campos()
