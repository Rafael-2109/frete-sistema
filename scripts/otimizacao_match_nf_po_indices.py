"""
Script para adicionar indices de otimizacao para Match NF x PO.

Estes indices melhoram a performance das consultas De-Para e Validacao.

Executar: python scripts/otimizacao_match_nf_po_indices.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_indices():
    """Cria indices compostos para otimizar consultas do match NF x PO."""
    app = create_app()

    indices = [
        # Indice para converter_lote() do DeparaService
        # Usado na busca batch de De-Para: WHERE cnpj + cod_produto IN (...)
        {
            'nome': 'idx_depara_cnpj_cod_ativo',
            'tabela': 'produto_fornecedor_depara',
            'colunas': 'cnpj_fornecedor, cod_produto_fornecedor, ativo',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_depara_cnpj_cod_ativo
                ON produto_fornecedor_depara(cnpj_fornecedor, cod_produto_fornecedor, ativo)
            """
        },
        # Indice para busca de validacoes por DFE
        {
            'nome': 'idx_validacao_odoo_dfe',
            'tabela': 'validacao_nf_po_dfe',
            'colunas': 'odoo_dfe_id',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_validacao_odoo_dfe
                ON validacao_nf_po_dfe(odoo_dfe_id)
            """
        },
        # Indice para busca de matches por validacao
        {
            'nome': 'idx_match_validacao',
            'tabela': 'match_nf_po_item',
            'colunas': 'validacao_id',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_match_validacao
                ON match_nf_po_item(validacao_id)
            """
        },
        # Indice para busca de divergencias por validacao
        {
            'nome': 'idx_divergencia_validacao',
            'tabela': 'divergencia_nf_po',
            'colunas': 'validacao_id',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_divergencia_validacao
                ON divergencia_nf_po(validacao_id)
            """
        },
        # Indice para busca de alocacoes por match_item
        {
            'nome': 'idx_alocacao_match_item',
            'tabela': 'match_nf_po_alocacao',
            'colunas': 'match_item_id',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_alocacao_match_item
                ON match_nf_po_alocacao(match_item_id)
            """
        }
    ]

    with app.app_context():
        print("=" * 60)
        print("CRIANDO INDICES DE OTIMIZACAO PARA MATCH NF x PO")
        print("=" * 60)

        for idx in indices:
            try:
                print(f"\n[{idx['nome']}]")
                print(f"  Tabela: {idx['tabela']}")
                print(f"  Colunas: {idx['colunas']}")

                db.session.execute(text(idx['sql']))
                db.session.commit()

                print(f"  Status: CRIADO com sucesso")

            except Exception as e:
                print(f"  Status: ERRO - {e}")
                db.session.rollback()

        print("\n" + "=" * 60)
        print("PROCESSO CONCLUIDO")
        print("=" * 60)

        # Verificar indices existentes
        print("\nINDICES NA TABELA produto_fornecedor_depara:")
        try:
            result = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'produto_fornecedor_depara'
            """))
            for row in result:
                print(f"  - {row[0]}")
        except Exception as e:
            print(f"  Erro ao listar: {e}")


if __name__ == '__main__':
    criar_indices()
