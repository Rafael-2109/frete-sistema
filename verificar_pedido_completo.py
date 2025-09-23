#!/usr/bin/env python3
"""
Script para verificar a existência do pedido VCD2510435 em todas as tabelas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def verificar_pedido_completo():
    app = create_app()

    with app.app_context():
        pedido = 'VCD2510435'

        print("\n" + "="*60)
        print(f"VERIFICAÇÃO COMPLETA DO PEDIDO: {pedido}")
        print("="*60 + "\n")

        # 1. Verificar em FaturamentoProduto
        print("1. FATURAMENTO_PRODUTO:")
        print("-" * 40)

        sql1 = text("""
            SELECT
                numero_nf,
                origem,
                cnpj_cliente,
                nome_cliente,
                vendedor,
                equipe_vendas,
                status_nf
            FROM faturamento_produto
            WHERE
                origem = :pedido OR
                origem LIKE '%' || :pedido || '%'
            LIMIT 5
        """)

        result1 = db.session.execute(sql1, {'pedido': pedido}).fetchall()

        if result1:
            print(f"✓ Encontrado em faturamento_produto: {len(result1)} registros")
            for row in result1:
                print(f"  - NF: {row.numero_nf}, Origem: {row.origem}, Status: {row.status_nf}")
                print(f"    Cliente: {row.nome_cliente}, Vendedor: {row.vendedor}")
        else:
            print("✗ NÃO encontrado em faturamento_produto")

        # 2. Verificar em RelatorioFaturamentoImportado
        print("\n2. RELATORIO_FATURAMENTO_IMPORTADO:")
        print("-" * 40)

        sql2 = text("""
            SELECT
                numero_nf,
                origem,
                cnpj_cliente,
                nome_cliente,
                vendedor,
                equipe_vendas,
                ativo
            FROM relatorio_faturamento_importado
            WHERE
                origem = :pedido OR
                origem LIKE '%' || :pedido || '%'
            LIMIT 5
        """)

        result2 = db.session.execute(sql2, {'pedido': pedido}).fetchall()

        if result2:
            print(f"✓ Encontrado em relatorio_faturamento: {len(result2)} registros")
            for row in result2:
                print(f"  - NF: {row.numero_nf}, Origem: {row.origem}, Ativo: {row.ativo}")
                print(f"    Cliente: {row.nome_cliente}, Vendedor: {row.vendedor}")
        else:
            print("✗ NÃO encontrado em relatorio_faturamento_importado")

        # 3. Verificar pedidos similares na carteira
        print("\n3. PEDIDOS SIMILARES NA CARTEIRA (VCD251...):")
        print("-" * 40)

        sql3 = text("""
            SELECT DISTINCT
                num_pedido,
                raz_social_red,
                vendedor,
                equipe_vendas,
                SUM(qtd_saldo_produto_pedido) as saldo_total
            FROM carteira_principal
            WHERE
                num_pedido LIKE 'VCD251%'
            GROUP BY num_pedido, raz_social_red, vendedor, equipe_vendas
            ORDER BY num_pedido
            LIMIT 10
        """)

        result3 = db.session.execute(sql3).fetchall()

        if result3:
            print(f"✓ Pedidos similares encontrados:")
            for row in result3:
                print(f"  - {row.num_pedido}: {row.raz_social_red} (Saldo: {row.saldo_total})")
        else:
            print("✗ Nenhum pedido similar VCD251* encontrado")

        # 4. Verificar em Pedido (view)
        print("\n4. TABELA/VIEW PEDIDOS:")
        print("-" * 40)

        sql4 = text("""
            SELECT
                num_pedido,
                cnpj_cpf,
                raz_social_red,
                status,
                nf
            FROM pedidos
            WHERE
                num_pedido = :pedido OR
                num_pedido LIKE '%' || :pedido || '%'
            LIMIT 5
        """)

        try:
            result4 = db.session.execute(sql4, {'pedido': pedido}).fetchall()

            if result4:
                print(f"✓ Encontrado em pedidos: {len(result4)} registros")
                for row in result4:
                    print(f"  - Pedido: {row.num_pedido}, Status: {row.status}, NF: {row.nf}")
            else:
                print("✗ NÃO encontrado em pedidos")
        except Exception as e:
            print(f"✗ Erro ao consultar pedidos: {e}")

        # 5. Conclusão
        print("\n" + "="*60)
        print("CONCLUSÃO:")
        print("="*60)

        if not result1 and not result2:
            print("\n⚠️ O pedido VCD2510435 não foi encontrado em nenhuma tabela.")
            print("   Possíveis razões:")
            print("   1. O pedido não existe no sistema")
            print("   2. O pedido tem um número diferente (espaços, caracteres especiais)")
            print("   3. O pedido foi removido ou cancelado")
            print("   4. O pedido ainda não foi importado")
        else:
            print("\n⚠️ O pedido foi FATURADO (encontrado em faturamento) mas")
            print("   não está na carteira_principal (já foi completamente atendido)")

if __name__ == '__main__':
    verificar_pedido_completo()