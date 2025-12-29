"""
Script para propagar o número do pedido do cliente para as linhas do pedido no Odoo

Busca pedidos criados em uma data e propaga o l10n_br_pedido_compra do cabeçalho
para as linhas que estão sem.

Uso:
    source .venv/bin/activate
    python scripts/propagar_pedido_cliente_linhas.py

Para executar de verdade, altere DRY_RUN = False
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ===== CONFIGURAÇÃO =====
DATA_CRIACAO = '2025-12-26'  # Data de criação dos pedidos (formato YYYY-MM-DD)
DRY_RUN = False  # True = apenas mostra, False = executa
# =========================


def main():
    from app import create_app
    from app.odoo.utils.connection import get_odoo_connection

    app = create_app()

    with app.app_context():
        print(f"\n{'='*70}")
        print(f"PROPAGAÇÃO DE NÚMERO DO PEDIDO DO CLIENTE PARA LINHAS")
        print(f"{'='*70}")
        print(f"📅 Filtrando pedidos criados em: {DATA_CRIACAO}")
        print(f"🔍 Modo: {'SIMULAÇÃO' if DRY_RUN else 'EXECUÇÃO'}")

        conn = get_odoo_connection()

        # Busca pedidos criados na data especificada
        print(f"\n🔍 Buscando pedidos no Odoo...")

        order_ids = conn.execute_kw('sale.order', 'search', [
            [
                ('create_date', '>=', f'{DATA_CRIACAO} 00:00:00'),
                ('create_date', '<=', f'{DATA_CRIACAO} 23:59:59'),
                ('l10n_br_pedido_compra', '!=', False)  # Tem número do pedido do cliente
            ]
        ])

        if not order_ids:
            print(f"❌ Nenhum pedido encontrado")
            return

        print(f"📋 Encontrados {len(order_ids)} pedidos")

        # Busca dados dos pedidos
        orders = conn.execute_kw('sale.order', 'read', [order_ids], {
            'fields': ['name', 'l10n_br_pedido_compra', 'order_line']
        })

        total_linhas_atualizadas = 0
        pedidos_afetados = 0

        print("-" * 70)

        for order in orders:
            order_id = order['id']
            order_name = order['name']
            pedido_compra = order.get('l10n_br_pedido_compra', '')
            line_ids = order.get('order_line', [])

            if not line_ids or not pedido_compra:
                continue

            # Busca linhas SEM pedido_compra
            linhas_sem = conn.execute_kw('sale.order.line', 'search', [
                [
                    ('order_id', '=', order_id),
                    '|',
                    ('l10n_br_pedido_compra', '=', False),
                    ('l10n_br_pedido_compra', '=', '')
                ]
            ])

            if not linhas_sem:
                continue

            pedidos_afetados += 1
            print(f"\n📦 {order_name} - Pedido Cliente: {pedido_compra}")
            print(f"   Linhas sem pedido_compra: {len(linhas_sem)}")

            if not DRY_RUN:
                # Atualiza as linhas
                conn.execute_kw('sale.order.line', 'write', [
                    linhas_sem,
                    {'l10n_br_pedido_compra': pedido_compra}
                ])
                print(f"   ✅ {len(linhas_sem)} linhas atualizadas")
            else:
                print(f"   ⏳ [DRY-RUN] {len(linhas_sem)} linhas seriam atualizadas")

            total_linhas_atualizadas += len(linhas_sem)

        print(f"\n{'='*70}")
        print(f"📊 RESUMO:")
        print(f"   Pedidos afetados: {pedidos_afetados}")
        print(f"   Total linhas {'atualizadas' if not DRY_RUN else 'a atualizar'}: {total_linhas_atualizadas}")

        if DRY_RUN and total_linhas_atualizadas > 0:
            print(f"\n⚠️  SIMULAÇÃO - Para executar, altere DRY_RUN = False no script")

        print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
