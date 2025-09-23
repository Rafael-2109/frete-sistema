#!/usr/bin/env python3
"""
Script para verificar a existência do pedido VCD2510435 na carteira_principal
e entender por que não aparece no filtro
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from sqlalchemy import or_, text

def verificar_pedido():
    app = create_app()

    with app.app_context():
        pedido = 'VCD2510435'

        print("\n" + "="*60)
        print(f"VERIFICANDO PEDIDO: {pedido}")
        print("="*60 + "\n")

        # 1. Buscar na carteira_principal
        print("1. CARTEIRA PRINCIPAL:")
        print("-" * 40)

        items = CarteiraPrincipal.query.filter(
            or_(
                CarteiraPrincipal.num_pedido == pedido,
                CarteiraPrincipal.pedido_cliente == pedido
            )
        ).all()

        if items:
            print(f"✓ Encontrado: {len(items)} itens")

            # Verificar se tem saldo
            tem_saldo = False
            for item in items:
                if item.qtd_saldo_produto_pedido > 0:
                    tem_saldo = True
                    break

            print(f"  - Tem saldo? {'SIM' if tem_saldo else 'NÃO'}")

            # Mostrar detalhes
            for i, item in enumerate(items[:3], 1):
                print(f"\n  Item {i}:")
                print(f"    num_pedido: {item.num_pedido}")
                print(f"    pedido_cliente: {item.pedido_cliente}")
                print(f"    qtd_saldo_produto_pedido: {item.qtd_saldo_produto_pedido}")
                print(f"    qtd_produto_pedido: {item.qtd_produto_pedido}")
                print(f"    cliente: {item.raz_social_red}")
                print(f"    vendedor: {item.vendedor}")
                print(f"    equipe: {item.equipe_vendas}")

        else:
            print("✗ NÃO encontrado na carteira_principal")

        # 2. Buscar na Separacao
        print("\n2. SEPARAÇÃO:")
        print("-" * 40)

        sep_items = Separacao.query.filter(
            or_(
                Separacao.num_pedido == pedido,
                Separacao.pedido_cliente == pedido
            )
        ).all()

        if sep_items:
            print(f"✓ Encontrado: {len(sep_items)} itens")
            for item in sep_items[:2]:
                print(f"  - num_pedido: {item.num_pedido}")
                print(f"  - sincronizado_nf: {item.sincronizado_nf}")
                print(f"  - status: {item.status}")
        else:
            print("✗ NÃO encontrado em Separacao")

        # 3. Buscar direto via SQL para debug
        print("\n3. BUSCA DIRETA SQL:")
        print("-" * 40)

        sql = text("""
            SELECT
                num_pedido,
                pedido_cliente,
                qtd_saldo_produto_pedido,
                raz_social_red,
                vendedor,
                equipe_vendas
            FROM carteira_principal
            WHERE
                num_pedido = :pedido OR
                pedido_cliente = :pedido OR
                num_pedido LIKE '%' || :pedido || '%' OR
                pedido_cliente LIKE '%' || :pedido || '%'
        """)

        result = db.session.execute(sql, {'pedido': pedido}).fetchall()

        if result:
            print(f"✓ Encontrado via SQL: {len(result)} itens")
            for row in result[:3]:
                print(f"  - num_pedido: {row.num_pedido}, pedido_cliente: {row.pedido_cliente}, saldo: {row.qtd_saldo_produto_pedido}")
        else:
            print("✗ NÃO encontrado via SQL")

        # 4. Verificar se o problema é case-sensitive ou espaços
        print("\n4. BUSCA FLEXÍVEL (case-insensitive e sem espaços):")
        print("-" * 40)

        sql_flex = text("""
            SELECT DISTINCT
                num_pedido,
                pedido_cliente
            FROM carteira_principal
            WHERE
                UPPER(TRIM(num_pedido)) = UPPER(TRIM(:pedido)) OR
                UPPER(TRIM(pedido_cliente)) = UPPER(TRIM(:pedido)) OR
                UPPER(num_pedido) LIKE '%VCD2510%' OR
                UPPER(pedido_cliente) LIKE '%VCD2510%'
        """)

        result_flex = db.session.execute(sql_flex, {'pedido': pedido}).fetchall()

        if result_flex:
            print(f"✓ Encontrado com busca flexível: {len(result_flex)} pedidos")
            for row in result_flex[:5]:
                print(f"  - num_pedido: '{row.num_pedido}', pedido_cliente: '{row.pedido_cliente}'")
        else:
            print("✗ NÃO encontrado mesmo com busca flexível")

        print("\n" + "="*60)
        print("FIM DA VERIFICAÇÃO")
        print("="*60 + "\n")

if __name__ == '__main__':
    verificar_pedido()