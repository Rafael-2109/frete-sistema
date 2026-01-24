"""
Migração: Adicionar campos de nome ao modelo PerfilFiscalProdutoFornecedor.

Campos adicionados:
- nome_empresa_compradora (VARCHAR 255)
- razao_fornecedor (VARCHAR 255)
- nome_produto (VARCHAR 255)

Uso:
    python scripts/migrations/add_nomes_perfil_fiscal.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se as colunas já existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'perfil_fiscal_produto_fornecedor'
                AND column_name IN ('nome_empresa_compradora', 'razao_fornecedor', 'nome_produto')
            """))
            colunas_existentes = [row[0] for row in resultado]

            colunas_adicionadas = []

            if 'nome_empresa_compradora' not in colunas_existentes:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN nome_empresa_compradora VARCHAR(255)
                """))
                colunas_adicionadas.append('nome_empresa_compradora')

            if 'razao_fornecedor' not in colunas_existentes:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN razao_fornecedor VARCHAR(255)
                """))
                colunas_adicionadas.append('razao_fornecedor')

            if 'nome_produto' not in colunas_existentes:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    ADD COLUMN nome_produto VARCHAR(255)
                """))
                colunas_adicionadas.append('nome_produto')

            db.session.commit()

            if colunas_adicionadas:
                print(f"✅ Colunas adicionadas: {', '.join(colunas_adicionadas)}")
            else:
                print("ℹ️  Todas as colunas já existiam. Nenhuma alteração necessária.")

        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migracao()
