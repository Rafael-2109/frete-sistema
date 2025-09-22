#!/usr/bin/env python3
"""
Diagnóstico de Problemas na Carteira e Faturamento
=================================================

Verifica duplicatas e problemas nos dados.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date

def diagnosticar():
    from app import create_app, db
    from app.carteira.models import CarteiraPrincipal
    from app.faturamento.models import FaturamentoProduto
    from sqlalchemy import func, and_

    print("="*80)
    print("🔍 DIAGNÓSTICO DE PROBLEMAS NA CARTEIRA E FATURAMENTO")
    print("="*80)

    app = create_app()

    with app.app_context():
        # 1. Verificar duplicatas na CarteiraPrincipal
        print("\n📊 1. VERIFICANDO DUPLICATAS NA CARTEIRA (num_pedido + cod_produto):")
        print("-"*60)

        duplicatas_carteira = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto,
            func.count().label('quantidade')
        ).group_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto
        ).having(func.count() > 1).all()

        if duplicatas_carteira:
            print(f"❌ ENCONTRADAS {len(duplicatas_carteira)} COMBINAÇÕES DUPLICADAS!")
            for dup in duplicatas_carteira[:10]:  # Mostrar até 10
                print(f"   Pedido: {dup.num_pedido}, Produto: {dup.cod_produto} = {dup.quantidade} registros")
        else:
            print("✅ Nenhuma duplicata encontrada")

        # 2. Verificar duplicatas no FaturamentoProduto
        print("\n📊 2. VERIFICANDO DUPLICATAS NO FATURAMENTO (numero_nf + cod_produto):")
        print("-"*60)

        duplicatas_faturamento = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto,
            func.count().label('quantidade')
        ).group_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto
        ).having(func.count() > 1).all()

        if duplicatas_faturamento:
            print(f"❌ ENCONTRADAS {len(duplicatas_faturamento)} COMBINAÇÕES DUPLICADAS!")
            for dup in duplicatas_faturamento[:10]:  # Mostrar até 10
                print(f"   NF: {dup.numero_nf}, Produto: {dup.cod_produto} = {dup.quantidade} registros")
        else:
            print("✅ Nenhuma duplicata encontrada")

        # 3. Verificar saldos negativos
        print("\n📊 3. VERIFICANDO SALDOS NEGATIVOS NA CARTEIRA:")
        print("-"*60)

        saldos_negativos = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido < 0
        ).count()

        if saldos_negativos > 0:
            print(f"❌ {saldos_negativos} registros com saldo NEGATIVO")

            # Mostrar alguns exemplos
            exemplos = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido < 0
            ).limit(5).all()

            for item in exemplos:
                print(f"   Pedido: {item.num_pedido}, Produto: {item.cod_produto}")
                print(f"      Qtd Original: {item.qtd_produto_pedido}, Saldo: {item.qtd_saldo_produto_pedido}")
        else:
            print("✅ Nenhum saldo negativo")

        # 4. Verificar registros com saldo = 0
        print("\n📊 4. VERIFICANDO REGISTROS COM SALDO = 0:")
        print("-"*60)

        saldos_zero = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido == 0
        ).count()

        print(f"   Total com saldo = 0: {saldos_zero} registros")
        print("   (Estes devem ser mantidos para histórico)")

        # 5. Verificar totais
        print("\n📊 5. TOTAIS GERAIS:")
        print("-"*60)

        total_carteira = CarteiraPrincipal.query.count()
        total_faturamento = FaturamentoProduto.query.count()

        # Valor total da carteira com saldo > 0
        valor_carteira = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido)
        ).filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar() or 0

        print(f"   Total registros CarteiraPrincipal: {total_carteira}")
        print(f"   Total registros FaturamentoProduto: {total_faturamento}")
        print(f"   Valor total carteira (saldo > 0): R$ {valor_carteira:,.2f}")

        # 6. Verificar correspondência entre Carteira e Faturamento
        print("\n📊 6. VERIFICANDO CORRESPONDÊNCIA CARTEIRA x FATURAMENTO:")
        print("-"*60)

        # Buscar alguns pedidos para exemplo
        pedidos_exemplo = db.session.query(
            CarteiraPrincipal.num_pedido
        ).filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido < 0
        ).limit(3).all()

        for pedido in pedidos_exemplo:
            num_pedido = pedido[0]
            print(f"\n   Pedido: {num_pedido}")

            # Itens na carteira
            itens_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).all()

            print(f"   Itens na carteira: {len(itens_carteira)}")

            for item in itens_carteira[:3]:
                print(f"      Produto {item.cod_produto}: Qtd={item.qtd_produto_pedido}, Saldo={item.qtd_saldo_produto_pedido}")

                # Buscar faturamento correspondente
                faturados = FaturamentoProduto.query.filter_by(
                    origem=num_pedido,
                    cod_produto=item.cod_produto
                ).all()

                if faturados:
                    total_faturado = sum(f.qtd_produto_faturado for f in faturados)
                    print(f"         Faturado: {total_faturado} (em {len(faturados)} NFs)")
                    print(f"         Cálculo correto do saldo: {item.qtd_produto_pedido} - {total_faturado} = {item.qtd_produto_pedido - total_faturado}")
                else:
                    print(f"         Sem faturamento")

if __name__ == '__main__':
    diagnosticar()