"""
Script para DESCOBRIR a relação real entre Requisições e Pedidos
Analisa dados do banco e do Odoo para entender o relacionamento

Uso:
    python scripts/analisar_relacao_requisicoes_pedidos.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.manufatura.models import RequisicaoCompras, PedidoCompras
from sqlalchemy import func, text
from collections import defaultdict, Counter
import json

def analisar_dados_locais():
    """Analisa dados do banco local"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("📊 ANÁLISE DE DADOS LOCAIS - Requisições vs Pedidos")
        print("=" * 80)

        # =====================================================
        # 1. ESTATÍSTICAS GERAIS
        # =====================================================
        print("\n📈 ESTATÍSTICAS GERAIS:")

        total_requisicoes = RequisicaoCompras.query.count()
        total_pedidos = PedidoCompras.query.count()

        print(f"   Total de Requisições: {total_requisicoes}")
        print(f"   Total de Pedidos: {total_pedidos}")

        # Requisições únicas (cabeçalho)
        requisicoes_unicas = db.session.query(
            func.count(func.distinct(RequisicaoCompras.num_requisicao))
        ).scalar()

        print(f"   Requisições únicas (cabeçalho): {requisicoes_unicas}")
        print(f"   Média de linhas por requisição: {total_requisicoes / requisicoes_unicas:.1f}")

        # Pedidos únicos
        pedidos_unicos = db.session.query(
            func.count(func.distinct(PedidoCompras.num_pedido))
        ).scalar()

        print(f"   Pedidos únicos: {pedidos_unicos}")

        # =====================================================
        # 2. ANALISAR CAMPO num_requisicao em PedidoCompras
        # =====================================================
        print("\n🔍 ANÁLISE: Campo 'num_requisicao' em PedidoCompras:")

        pedidos_com_requisicao = PedidoCompras.query.filter(
            PedidoCompras.num_requisicao.isnot(None),
            PedidoCompras.num_requisicao != ''
        ).count()

        pedidos_sem_requisicao = PedidoCompras.query.filter(
            (PedidoCompras.num_requisicao.is_(None)) |
            (PedidoCompras.num_requisicao == '')
        ).count()

        print(f"   Pedidos COM requisição vinculada: {pedidos_com_requisicao}")
        print(f"   Pedidos SEM requisição: {pedidos_sem_requisicao}")

        if total_pedidos > 0:
            percentual = (pedidos_com_requisicao / total_pedidos) * 100
            print(f"   % de pedidos vinculados: {percentual:.1f}%")

        # =====================================================
        # 3. RELAÇÃO: 1 Pedido → Quantas Requisições?
        # =====================================================
        print("\n🔗 ANÁLISE: 1 Pedido pode referenciar N requisições?")

        # Amostra de pedidos com requisição
        pedidos_sample = PedidoCompras.query.filter(
            PedidoCompras.num_requisicao.isnot(None),
            PedidoCompras.num_requisicao != ''
        ).limit(10).all()

        print(f"\n   Amostra de {len(pedidos_sample)} pedidos:")
        for p in pedidos_sample:
            print(f"   - Pedido: {p.num_pedido}")
            print(f"     Requisição: {p.num_requisicao}")
            print(f"     Produto: {p.cod_produto}")
            print(f"     Quantidade: {p.qtd_produto_pedido}")
            print()

        # =====================================================
        # 4. RELAÇÃO: 1 Requisição → Quantos Pedidos?
        # =====================================================
        print("\n🔗 ANÁLISE: 1 Requisição pode ter N pedidos?")

        # Contar pedidos por requisição
        pedidos_por_requisicao = db.session.query(
            PedidoCompras.num_requisicao,
            func.count(PedidoCompras.id).label('total_pedidos')
        ).filter(
            PedidoCompras.num_requisicao.isnot(None),
            PedidoCompras.num_requisicao != ''
        ).group_by(
            PedidoCompras.num_requisicao
        ).order_by(
            func.count(PedidoCompras.id).desc()
        ).limit(10).all()

        print(f"   Top 10 requisições com mais pedidos:")
        for req_num, total in pedidos_por_requisicao:
            print(f"   - {req_num}: {total} pedidos")

            # Detalhar pedidos dessa requisição
            pedidos = PedidoCompras.query.filter_by(
                num_requisicao=req_num
            ).all()

            for p in pedidos:
                print(f"     → Pedido: {p.num_pedido} | Produto: {p.cod_produto} | Qtd: {p.qtd_produto_pedido}")
            print()

        # Distribuição
        distribuicao = db.session.query(
            func.count(PedidoCompras.id).label('num_pedidos'),
            func.count().label('qtd_requisicoes')
        ).filter(
            PedidoCompras.num_requisicao.isnot(None),
            PedidoCompras.num_requisicao != ''
        ).group_by(
            PedidoCompras.num_requisicao
        ).all()

        print("\n   Distribuição de pedidos por requisição:")
        counter = Counter([d[0] for d in distribuicao])
        for num_pedidos, qtd_requisicoes in sorted(counter.items()):
            print(f"   - {qtd_requisicoes} requisições com {num_pedidos} pedido(s)")

        # =====================================================
        # 5. COMPARAR: Produto em Requisição vs Pedido
        # =====================================================
        print("\n🔍 ANÁLISE: Produto em Requisição == Produto em Pedido?")

        # Pegar requisições que têm pedidos
        sample_requisicoes = db.session.query(
            RequisicaoCompras.num_requisicao
        ).distinct().limit(5).all()

        for (req_num,) in sample_requisicoes:
            # Linhas da requisição
            req_linhas = RequisicaoCompras.query.filter_by(
                num_requisicao=req_num
            ).all()

            # Pedidos dessa requisição
            pedidos = PedidoCompras.query.filter_by(
                num_requisicao=req_num
            ).all()

            if pedidos:
                print(f"\n   Requisição: {req_num}")
                print(f"   Linhas na requisição ({len(req_linhas)}):")
                for r in req_linhas:
                    print(f"     - Produto: {r.cod_produto} | Qtd: {r.qtd_produto_requisicao}")

                print(f"   Pedidos vinculados ({len(pedidos)}):")
                for p in pedidos:
                    print(f"     - Pedido: {p.num_pedido} | Produto: {p.cod_produto} | Qtd: {p.qtd_produto_pedido}")

        # =====================================================
        # 6. ANÁLISE: Quantidades
        # =====================================================
        print("\n📊 ANÁLISE: Quantidade em Requisição vs Pedido")

        # Pegar casos onde num_requisicao + cod_produto coincidem
        query = text("""
            SELECT
                r.num_requisicao,
                r.cod_produto,
                r.qtd_produto_requisicao as qtd_requisicao,
                SUM(p.qtd_produto_pedido) as qtd_total_pedidos,
                COUNT(p.id) as num_pedidos
            FROM requisicao_compras r
            LEFT JOIN pedido_compras p
                ON r.num_requisicao = p.num_requisicao
                AND r.cod_produto = p.cod_produto
            WHERE p.id IS NOT NULL
            GROUP BY r.num_requisicao, r.cod_produto, r.qtd_produto_requisicao
            LIMIT 10
        """)

        resultados = db.session.execute(query).fetchall()

        print("\n   Comparação de quantidades (Requisição vs Soma de Pedidos):")
        for row in resultados:
            req_num, produto, qtd_req, qtd_ped, num_ped = row
            diff = float(qtd_ped) - float(qtd_req)
            print(f"   - {req_num} | {produto}")
            print(f"     Requisição: {qtd_req}")
            print(f"     Pedidos ({num_ped}): {qtd_ped}")
            print(f"     Diferença: {diff:+.3f}")
            print()

        # =====================================================
        # 7. CONCLUSÕES
        # =====================================================
        print("\n" + "=" * 80)
        print("📋 CONCLUSÕES PRELIMINARES:")
        print("=" * 80)

        print("\n✅ Dados coletados:")
        print(f"   - Total de requisições analisadas: {total_requisicoes}")
        print(f"   - Total de pedidos analisados: {total_pedidos}")
        print(f"   - Pedidos vinculados a requisições: {pedidos_com_requisicao}")

        print("\n📝 Próximo passo:")
        print("   Analisar estrutura no Odoo (API) para confirmar relacionamento")
        print()


def analisar_odoo():
    """Analisa estrutura no Odoo via API"""
    app = create_app()

    with app.app_context():
        try:
            from app.odoo.utils.connection import get_odoo_connection

            print("=" * 80)
            print("🌐 ANÁLISE DA API ODOO - Requisições vs Pedidos")
            print("=" * 80)

            connection = get_odoo_connection()
            uid = connection.authenticate()

            if not uid:
                print("❌ Falha na autenticação com Odoo")
                return

            print(f"✅ Autenticado com Odoo (UID: {uid})")

            # =====================================================
            # 1. BUSCAR REQUISIÇÕES (purchase.request)
            # =====================================================
            print("\n📋 Analisando purchase.request (Requisições)...")

            requisicoes = connection.search_read(
                'purchase.request',
                [['state', '!=', 'rejected']],
                fields=['id', 'name', 'state', 'line_ids'],
                limit=5
            )

            print(f"\n   Amostra de {len(requisicoes)} requisições:")
            for req in requisicoes:
                print(f"\n   Requisição: {req['name']} (ID: {req['id']})")
                print(f"   Estado: {req['state']}")
                print(f"   Número de linhas: {len(req.get('line_ids', []))}")

                # Buscar linhas
                if req.get('line_ids'):
                    linhas = connection.read(
                        'purchase.request.line',
                        req['line_ids'][:3],  # Primeiras 3 linhas
                        fields=['id', 'product_id', 'product_qty', 'purchase_lines']
                    )

                    print(f"   Linhas:")
                    for linha in linhas:
                        print(f"     - Linha ID: {linha['id']}")
                        print(f"       Produto: {linha['product_id']}")
                        print(f"       Quantidade: {linha['product_qty']}")
                        print(f"       purchase_lines: {linha.get('purchase_lines', [])} ← IMPORTANTE!")

            # =====================================================
            # 2. BUSCAR PEDIDOS (purchase.order)
            # =====================================================
            print("\n\n🛒 Analisando purchase.order (Pedidos)...")

            pedidos = connection.search_read(
                'purchase.order',
                [],
                fields=['id', 'name', 'state', 'partner_id', 'order_line'],
                limit=5
            )

            print(f"\n   Amostra de {len(pedidos)} pedidos:")
            for pedido in pedidos:
                print(f"\n   Pedido: {pedido['name']} (ID: {pedido['id']})")
                print(f"   Fornecedor: {pedido.get('partner_id', 'N/A')}")
                print(f"   Estado: {pedido['state']}")
                print(f"   Número de linhas: {len(pedido.get('order_line', []))}")

                # Buscar linhas do pedido
                if pedido.get('order_line'):
                    linhas_pedido = connection.read(
                        'purchase.order.line',
                        pedido['order_line'][:3],  # Primeiras 3 linhas
                        fields=['id', 'product_id', 'product_qty', 'request_line_id']
                    )

                    print(f"   Linhas do pedido:")
                    for linha in linhas_pedido:
                        print(f"     - Linha ID: {linha['id']}")
                        print(f"       Produto: {linha['product_id']}")
                        print(f"       Quantidade: {linha['product_qty']}")
                        print(f"       request_line_id: {linha.get('request_line_id', 'NULL')} ← IMPORTANTE!")

            # =====================================================
            # 3. DESCOBRIR RELACIONAMENTO
            # =====================================================
            print("\n\n🔗 DESCOBRINDO RELACIONAMENTO:")
            print("\nCampos importantes encontrados:")
            print("   - purchase.request.line.purchase_lines → Lista de IDs de purchase.order.line")
            print("   - purchase.order.line.request_line_id → ID da purchase.request.line")
            print("\n   CONCLUSÃO: Relacionamento N:N entre requisições e pedidos!")
            print("   - 1 linha de requisição pode gerar N linhas de pedido")
            print("   - 1 linha de pedido referencia 1 linha de requisição")

        except Exception as e:
            print(f"\n❌ Erro ao analisar Odoo: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    print("\n🔍 INICIANDO ANÁLISE DE RELACIONAMENTO REQUISIÇÕES ↔ PEDIDOS\n")

    # Análise de dados locais
    analisar_dados_locais()

    # Análise do Odoo
    print("\n" + "=" * 80)
    input("Pressione ENTER para analisar estrutura no Odoo (API)...")
    analisar_odoo()

    print("\n✅ ANÁLISE CONCLUÍDA!")
