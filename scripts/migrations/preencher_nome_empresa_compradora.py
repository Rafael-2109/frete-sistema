"""
Script de Migracao: Preencher nome_empresa_compradora em registros existentes
=============================================================================

Este script atualiza registros onde:
- cnpj_empresa_compradora IS NOT NULL
- razao_empresa_compradora / nome_empresa_compradora IS NULL ou vazio

Tabelas afetadas:
- cadastro_primeira_compra (campo: razao_empresa_compradora)
- perfil_fiscal_produto_fornecedor (campo: nome_empresa_compradora)
- divergencia_fiscal (campo: razao_empresa_compradora)

Uso:
    source .venv/bin/activate && python scripts/migrations/preencher_nome_empresa_compradora.py

Para executar em producao (Render Shell):
    ALTER TABLE ... (ver SQL abaixo)
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from app.utils.cnpj_utils import EMPRESAS_CNPJ_NOME


def preencher_nomes():
    """Preenche nomes de empresa em registros existentes"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRACAO: Preencher nome_empresa_compradora")
            print("=" * 60)

            total_atualizados = 0

            # 1. Atualizar cadastro_primeira_compra
            print("\n1. Tabela: cadastro_primeira_compra")
            print("-" * 40)

            for cnpj, nome in EMPRESAS_CNPJ_NOME.items():
                resultado = db.session.execute(text("""
                    UPDATE cadastro_primeira_compra
                    SET razao_empresa_compradora = :nome
                    WHERE cnpj_empresa_compradora = :cnpj
                      AND (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
                """), {'cnpj': cnpj, 'nome': nome})

                if resultado.rowcount > 0:
                    print(f"   CNPJ {cnpj}: {resultado.rowcount} registros atualizados -> {nome}")
                    total_atualizados += resultado.rowcount

            # 2. Atualizar perfil_fiscal_produto_fornecedor
            print("\n2. Tabela: perfil_fiscal_produto_fornecedor")
            print("-" * 40)

            for cnpj, nome in EMPRESAS_CNPJ_NOME.items():
                resultado = db.session.execute(text("""
                    UPDATE perfil_fiscal_produto_fornecedor
                    SET nome_empresa_compradora = :nome
                    WHERE cnpj_empresa_compradora = :cnpj
                      AND (nome_empresa_compradora IS NULL OR nome_empresa_compradora = '')
                """), {'cnpj': cnpj, 'nome': nome})

                if resultado.rowcount > 0:
                    print(f"   CNPJ {cnpj}: {resultado.rowcount} registros atualizados -> {nome}")
                    total_atualizados += resultado.rowcount

            # 3. Atualizar divergencia_fiscal
            print("\n3. Tabela: divergencia_fiscal")
            print("-" * 40)

            for cnpj, nome in EMPRESAS_CNPJ_NOME.items():
                resultado = db.session.execute(text("""
                    UPDATE divergencia_fiscal
                    SET razao_empresa_compradora = :nome
                    WHERE cnpj_empresa_compradora = :cnpj
                      AND (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '')
                """), {'cnpj': cnpj, 'nome': nome})

                if resultado.rowcount > 0:
                    print(f"   CNPJ {cnpj}: {resultado.rowcount} registros atualizados -> {nome}")
                    total_atualizados += resultado.rowcount

            # Commit
            db.session.commit()

            print("\n" + "=" * 60)
            print(f"CONCLUIDO: {total_atualizados} registros atualizados no total")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\nERRO: {e}")
            db.session.rollback()
            return False


def gerar_sql_producao():
    """Gera SQL para executar diretamente no Render Shell"""
    print("\n" + "=" * 60)
    print("SQL PARA PRODUCAO (Render Shell)")
    print("=" * 60)

    for cnpj, nome in EMPRESAS_CNPJ_NOME.items():
        print(f"""
-- CNPJ: {cnpj} -> {nome}
UPDATE cadastro_primeira_compra
SET razao_empresa_compradora = '{nome}'
WHERE cnpj_empresa_compradora = '{cnpj}'
  AND (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '');

UPDATE perfil_fiscal_produto_fornecedor
SET nome_empresa_compradora = '{nome}'
WHERE cnpj_empresa_compradora = '{cnpj}'
  AND (nome_empresa_compradora IS NULL OR nome_empresa_compradora = '');

UPDATE divergencia_fiscal
SET razao_empresa_compradora = '{nome}'
WHERE cnpj_empresa_compradora = '{cnpj}'
  AND (razao_empresa_compradora IS NULL OR razao_empresa_compradora = '');
""")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Preencher nome_empresa_compradora em registros existentes')
    parser.add_argument('--sql', action='store_true', help='Apenas gerar SQL para producao')
    args = parser.parse_args()

    if args.sql:
        gerar_sql_producao()
    else:
        preencher_nomes()
