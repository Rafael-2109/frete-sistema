"""
Verifica todos os pedidos do TOTAL ATACADO LJ 2 no sistema.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def verificar():
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.separacao.models import Separacao
        from app.carteira.models import CarteiraPrincipal

        print("=" * 60)
        print("VERIFICAÇÃO DE PEDIDOS TOTAL ATACADO LJ 2")
        print("=" * 60)

        # 1. Separação com sincronizado_nf=False e qtd_saldo > 0
        print("\n1. SEPARAÇÃO (sincronizado_nf=False, qtd_saldo>0):")
        seps = Separacao.query.filter(
            Separacao.raz_social_red.ilike('%TOTAL ATACADO LJ 2%'),
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        ).all()

        pedidos_sep = set()
        for s in seps:
            pedidos_sep.add(s.num_pedido)
            print(f"   {s.num_pedido} | {s.raz_social_red} | qtd={s.qtd_saldo} | status={s.status}")

        print(f"\n   Total: {len(seps)} registros, {len(pedidos_sep)} pedidos únicos")

        # 2. CarteiraPrincipal com qtd_saldo > 0
        print("\n2. CARTEIRA PRINCIPAL (qtd_saldo_produto_pedido > 0):")
        carts = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike('%TOTAL ATACADO LJ 2%'),
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        pedidos_cart = set()
        for c in carts:
            pedidos_cart.add(c.num_pedido)
            print(f"   {c.num_pedido} | {c.raz_social_red} | qtd={c.qtd_saldo_produto_pedido}")

        print(f"\n   Total: {len(carts)} registros, {len(pedidos_cart)} pedidos únicos")

        # 3. Comparação
        print("\n3. COMPARAÇÃO:")
        print(f"   Pedidos em Separacao: {pedidos_sep}")
        print(f"   Pedidos em CarteiraPrincipal: {pedidos_cart}")

        apenas_sep = pedidos_sep - pedidos_cart
        apenas_cart = pedidos_cart - pedidos_sep

        if apenas_sep:
            print(f"\n   ⚠️  Pedidos APENAS em Separacao: {apenas_sep}")
        if apenas_cart:
            print(f"\n   ⚠️  Pedidos APENAS em CarteiraPrincipal: {apenas_cart}")


if __name__ == "__main__":
    verificar()
