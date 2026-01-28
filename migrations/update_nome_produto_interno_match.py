"""
Migration: Atualiza nome_produto_interno em MatchNfPoItem usando De-Para

Proposito: Preencher retroativamente o campo nome_produto_interno nos registros
de MatchNfPoItem que foram criados ANTES da implementacao deste campo.

O problema: MatchNfPoItem criados antes tinham nome_produto_interno = NULL,
mesmo quando o De-Para ja tinha o nome preenchido.

Autor: Claude Code
Data: 2026-01-28
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def executar_atualizacao():
    """
    Atualiza nome_produto_interno em MatchNfPoItem usando dados do De-Para.

    Logica:
    - Busca MatchNfPoItem com nome_produto_interno NULL
    - Faz JOIN com ProdutoFornecedorDepara pelo cod_produto_interno + cnpj_fornecedor
    - Atualiza com o nome_produto_interno do De-Para
    """
    app = create_app()
    with app.app_context():
        try:
            # Primeiro, verificar quantos registros serao afetados
            count_query = text("""
                SELECT COUNT(*) as total
                FROM match_nf_po_item m
                JOIN validacao_nf_po_dfe v ON m.validacao_id = v.id
                JOIN produto_fornecedor_depara d ON
                    m.cod_produto_interno = d.cod_produto_interno
                    AND d.cnpj_fornecedor = REPLACE(REPLACE(REPLACE(v.cnpj_fornecedor, '.', ''), '/', ''), '-', '')
                WHERE m.nome_produto_interno IS NULL
                  AND d.nome_produto_interno IS NOT NULL
                  AND d.ativo = true
            """)

            resultado = db.session.execute(count_query)
            total = resultado.scalar()

            print(f"Registros a serem atualizados: {total}")

            if total == 0:
                print("Nenhum registro para atualizar.")
                return True

            # Executar UPDATE
            update_query = text("""
                UPDATE match_nf_po_item m
                SET nome_produto_interno = d.nome_produto_interno
                FROM produto_fornecedor_depara d, validacao_nf_po_dfe v
                WHERE m.validacao_id = v.id
                  AND m.cod_produto_interno = d.cod_produto_interno
                  AND d.cnpj_fornecedor = REPLACE(REPLACE(REPLACE(v.cnpj_fornecedor, '.', ''), '/', ''), '-', '')
                  AND m.nome_produto_interno IS NULL
                  AND d.nome_produto_interno IS NOT NULL
                  AND d.ativo = true
            """)

            resultado = db.session.execute(update_query)
            db.session.commit()

            print(f"SUCCESS: {resultado.rowcount} registros atualizados")
            return True

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            return False


def verificar_nf_430279():
    """Verifica especificamente a NF 430279 mencionada pelo usuario."""
    app = create_app()
    with app.app_context():
        try:
            query = text("""
                SELECT
                    m.cod_produto_fornecedor,
                    m.cod_produto_interno,
                    m.nome_produto_interno as nome_no_match,
                    d.nome_produto_interno as nome_no_depara
                FROM match_nf_po_item m
                JOIN validacao_nf_po_dfe v ON m.validacao_id = v.id
                LEFT JOIN produto_fornecedor_depara d ON
                    m.cod_produto_interno = d.cod_produto_interno
                    AND d.cnpj_fornecedor = REPLACE(REPLACE(REPLACE(v.cnpj_fornecedor, '.', ''), '/', ''), '-', '')
                    AND d.ativo = true
                WHERE v.numero_nf = '430279'
                ORDER BY m.cod_produto_fornecedor
            """)

            resultado = db.session.execute(query)
            rows = resultado.fetchall()

            print("\n=== NF 430279 - Verificacao ===")
            print(f"{'Cod Forn':<15} {'Cod Int':<15} {'Nome no Match':<40} {'Nome no De-Para':<40}")
            print("-" * 115)

            for row in rows:
                nome_match = (row.nome_no_match or 'NULL')[:38]
                nome_depara = (row.nome_no_depara or 'NULL')[:38]
                print(f"{row.cod_produto_fornecedor:<15} {row.cod_produto_interno:<15} {nome_match:<40} {nome_depara:<40}")

            return True

        except Exception as e:
            print(f"ERRO na verificacao: {e}")
            return False


# SQL para rodar manualmente no Render Shell:
SQL_RENDER = """
-- Verificar quantos registros serao afetados
SELECT COUNT(*) as total
FROM match_nf_po_item m
JOIN validacao_nf_po_dfe v ON m.validacao_id = v.id
JOIN produto_fornecedor_depara d ON
    m.cod_produto_interno = d.cod_produto_interno
    AND d.cnpj_fornecedor = REPLACE(REPLACE(REPLACE(v.cnpj_fornecedor, '.', ''), '/', ''), '-', '')
WHERE m.nome_produto_interno IS NULL
  AND d.nome_produto_interno IS NOT NULL
  AND d.ativo = true;

-- Executar UPDATE
UPDATE match_nf_po_item m
SET nome_produto_interno = d.nome_produto_interno
FROM produto_fornecedor_depara d, validacao_nf_po_dfe v
WHERE m.validacao_id = v.id
  AND m.cod_produto_interno = d.cod_produto_interno
  AND d.cnpj_fornecedor = REPLACE(REPLACE(REPLACE(v.cnpj_fornecedor, '.', ''), '/', ''), '-', '')
  AND m.nome_produto_interno IS NULL
  AND d.nome_produto_interno IS NOT NULL
  AND d.ativo = true;

-- Verificar NF 430279 apos atualizacao
SELECT m.cod_produto_fornecedor, m.cod_produto_interno, m.nome_produto_interno
FROM match_nf_po_item m
JOIN validacao_nf_po_dfe v ON m.validacao_id = v.id
WHERE v.numero_nf = '430279';
"""


if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Atualizar nome_produto_interno em MatchNfPoItem")
    print("=" * 60)

    # Verificar antes
    print("\n--- ANTES DA ATUALIZACAO ---")
    verificar_nf_430279()

    # Executar atualizacao
    print("\n--- EXECUTANDO ATUALIZACAO ---")
    executar_atualizacao()

    # Verificar depois
    print("\n--- APOS ATUALIZACAO ---")
    verificar_nf_430279()

    print("\n--- SQL PARA RENDER SHELL ---")
    print(SQL_RENDER)
