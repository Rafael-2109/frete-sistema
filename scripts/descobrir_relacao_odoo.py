"""
Script para DESCOBRIR a relação entre Requisições e Pedidos no ODOO
Consulta diretamente a API do Odoo para entender o modelo de dados

Uso:
    python scripts/descobrir_relacao_odoo.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
import json

def descobrir_estrutura_odoo():
    """Descobre a estrutura real no Odoo"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🌐 DESCOBRINDO ESTRUTURA NO ODOO")
        print("=" * 80)

        connection = get_odoo_connection()
        uid = connection.authenticate()

        if not uid:
            print("❌ Falha na autenticação com Odoo")
            return

        print(f"✅ Autenticado com Odoo (UID: {uid})\n")

        # =====================================================
        # 1. ANALISAR purchase.request (Requisição)
        # =====================================================
        print("\n📋 ESTRUTURA: purchase.request (Requisição)")
        print("-" * 80)

        # Buscar 1 requisição como exemplo
        requisicoes = connection.search_read(
            'purchase.request',
            [['state', '!=', 'rejected']],
            fields=[
                'id', 'name', 'state', 'date_start', 'requested_by',
                'description', 'line_ids', 'create_date', 'write_date'
            ],
            limit=3
        )

        print(f"\n✅ Encontradas {len(requisicoes)} requisições\n")

        for req in requisicoes:
            print(f"📌 Requisição: {req['name']} (ID Odoo: {req['id']})")
            print(f"   Estado: {req['state']}")
            print(f"   Data início: {req.get('date_start', 'N/A')}")
            print(f"   Solicitante: {req.get('requested_by', 'N/A')}")
            print(f"   Linhas: {len(req.get('line_ids', []))} linha(s)")

            # Analisar LINHAS da requisição
            if req.get('line_ids'):
                print(f"\n   📝 Linhas da requisição:")

                linhas = connection.read(
                    'purchase.request.line',
                    req['line_ids'][:3],  # Primeiras 3 linhas
                    fields=[
                        'id', 'product_id', 'name', 'product_qty',
                        'product_uom_id', 'date_required', 'estimated_cost',
                        'purchase_lines',  # ← CAMPO IMPORTANTE!
                        'request_id'
                    ]
                )

                for linha in linhas:
                    print(f"\n      → Linha ID: {linha['id']}")
                    print(f"        Produto: {linha.get('product_id', 'N/A')}")
                    print(f"        Quantidade: {linha.get('product_qty', 0)}")
                    print(f"        Data necessária: {linha.get('date_required', 'N/A')}")

                    # CAMPO CRUCIAL: purchase_lines
                    purchase_lines = linha.get('purchase_lines', [])
                    print(f"        🔗 purchase_lines: {purchase_lines}")

                    if purchase_lines:
                        print(f"           ↳ Esta linha está vinculada a {len(purchase_lines)} linha(s) de pedido(s)")
                    else:
                        print(f"           ↳ Esta linha NÃO tem pedidos vinculados ainda")

            print("\n" + "-" * 80)

        # =====================================================
        # 2. ANALISAR purchase.order (Pedido de Compra)
        # =====================================================
        print("\n\n🛒 ESTRUTURA: purchase.order (Pedido de Compra)")
        print("-" * 80)

        pedidos = connection.search_read(
            'purchase.order',
            [['state', '!=', 'cancel']],
            fields=[
                'id', 'name', 'state', 'partner_id', 'date_order',
                'date_planned', 'amount_total', 'currency_id',
                'order_line', 'create_date', 'write_date'
            ],
            limit=3
        )

        print(f"\n✅ Encontrados {len(pedidos)} pedidos\n")

        for pedido in pedidos:
            print(f"📌 Pedido: {pedido['name']} (ID Odoo: {pedido['id']})")
            print(f"   Estado: {pedido['state']}")
            print(f"   Fornecedor: {pedido.get('partner_id', 'N/A')}")
            print(f"   Data pedido: {pedido.get('date_order', 'N/A')}")
            print(f"   Valor total: {pedido.get('amount_total', 0)} {pedido.get('currency_id', ['', ''])[1]}")
            print(f"   Linhas: {len(pedido.get('order_line', []))} linha(s)")

            # Analisar LINHAS do pedido
            if pedido.get('order_line'):
                print(f"\n   📝 Linhas do pedido:")

                linhas_pedido = connection.read(
                    'purchase.order.line',
                    pedido['order_line'][:3],  # Primeiras 3 linhas
                    fields=[
                        'id', 'product_id', 'name', 'product_qty',
                        'price_unit', 'price_subtotal', 'date_planned',
                        'request_line_id',  # ← CAMPO IMPORTANTE!
                        'order_id'
                    ]
                )

                for linha in linhas_pedido:
                    print(f"\n      → Linha Pedido ID: {linha['id']}")
                    print(f"        Produto: {linha.get('product_id', 'N/A')}")
                    print(f"        Quantidade: {linha.get('product_qty', 0)}")
                    print(f"        Preço unitário: {linha.get('price_unit', 0)}")
                    print(f"        Subtotal: {linha.get('price_subtotal', 0)}")

                    # CAMPO CRUCIAL: request_line_id
                    request_line_id = linha.get('request_line_id', False)
                    print(f"        🔗 request_line_id: {request_line_id}")

                    if request_line_id:
                        print(f"           ↳ Esta linha atende a requisição ID: {request_line_id}")
                    else:
                        print(f"           ↳ Esta linha NÃO veio de uma requisição (compra direta)")

            print("\n" + "-" * 80)

        # =====================================================
        # 3. RASTREAR RELACIONAMENTO COMPLETO
        # =====================================================
        print("\n\n🔗 RASTREANDO RELACIONAMENTO COMPLETO")
        print("=" * 80)

        # Buscar uma requisição que tenha pedidos vinculados
        print("\n🔍 Buscando requisição com pedidos vinculados...\n")

        requisicoes_com_pedidos = connection.search_read(
            'purchase.request',
            [],
            fields=['id', 'name', 'line_ids'],
            limit=50
        )

        for req in requisicoes_com_pedidos:
            if req.get('line_ids'):
                linhas = connection.read(
                    'purchase.request.line',
                    req['line_ids'],
                    fields=['id', 'product_id', 'product_qty', 'purchase_lines']
                )

                # Verificar se tem purchase_lines
                for linha in linhas:
                    if linha.get('purchase_lines'):
                        print(f"✅ ENCONTRADO! Requisição com pedidos vinculados:")
                        print(f"\n📌 Requisição: {req['name']} (ID: {req['id']})")

                        print(f"\n   Linha Requisição ID: {linha['id']}")
                        print(f"   Produto: {linha.get('product_id', 'N/A')}")
                        print(f"   Quantidade requisitada: {linha.get('product_qty', 0)}")
                        print(f"   Linhas de pedido vinculadas: {linha.get('purchase_lines', [])}")

                        # Buscar detalhes das linhas de pedido
                        purchase_line_ids = linha.get('purchase_lines', [])
                        if purchase_line_ids:
                            linhas_pedido = connection.read(
                                'purchase.order.line',
                                purchase_line_ids,
                                fields=[
                                    'id', 'order_id', 'product_id', 'product_qty',
                                    'price_unit', 'request_line_id'
                                ]
                            )

                            print(f"\n   📦 Pedidos que atendem esta linha:")
                            for lp in linhas_pedido:
                                print(f"\n      → Linha Pedido ID: {lp['id']}")
                                print(f"        Pedido: {lp.get('order_id', 'N/A')}")
                                print(f"        Produto: {lp.get('product_id', 'N/A')}")
                                print(f"        Quantidade: {lp.get('product_qty', 0)}")
                                print(f"        Preço: {lp.get('price_unit', 0)}")
                                print(f"        Referência requisição: {lp.get('request_line_id', 'N/A')}")

                        print("\n" + "=" * 80)
                        return  # Parar após encontrar um exemplo

        print("\n⚠️  Nenhuma requisição com pedidos vinculados encontrada nos primeiros 50 registros")

        # =====================================================
        # 4. CONCLUSÕES
        # =====================================================
        print("\n\n📋 CONCLUSÕES SOBRE A ESTRUTURA:")
        print("=" * 80)
        print("\n✅ RELACIONAMENTO DESCOBERTO:\n")

        print("1. purchase.request (Cabeçalho da requisição)")
        print("   └─ line_ids → purchase.request.line (Linhas da requisição)")
        print("       └─ purchase_lines → [purchase.order.line IDs]")
        print("\n2. purchase.order (Cabeçalho do pedido)")
        print("   └─ order_line → purchase.order.line (Linhas do pedido)")
        print("       └─ request_line_id → purchase.request.line ID\n")

        print("🔗 RELAÇÃO:")
        print("   - 1 purchase.request.line pode gerar N purchase.order.line (atendimento parcial)")
        print("   - 1 purchase.order.line referencia 1 purchase.request.line (ou NULL)")
        print("\n   CONCLUSÃO: Relação 1:N entre linha de requisição e linhas de pedidos!")
        print("\n" + "=" * 80)


if __name__ == '__main__':
    descobrir_estrutura_odoo()
