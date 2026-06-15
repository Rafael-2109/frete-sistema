"""
Script para debugar saídas não visíveis
Simula EXATAMENTE o que acontece na função calcular_saidas_nao_visiveis
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("="*80)
    print("DEBUG: Saídas Não Visíveis")
    print("="*80)

    # PASSO 1: Buscar alguns produtos da carteira
    print("\n[PASSO 1] Buscar produtos da carteira...")
    produtos = db.session.query(
        CarteiraPrincipal.cod_produto
    ).filter(
        CarteiraPrincipal.ativo == True,
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).distinct().limit(5).all()

    codigos_produtos = [p[0] for p in produtos]
    print(f"   ✅ Produtos encontrados: {codigos_produtos}")

    if not codigos_produtos:
        print("\n   ⚠️ NENHUM produto encontrado!")
        sys.exit(0)

    # PASSO 2: Simular filtro - pegar apenas alguns pedidos como "visíveis"
    print("\n[PASSO 2] Simular pedidos visíveis (primeiros 10)...")
    pedidos_visiveis = db.session.query(
        CarteiraPrincipal.num_pedido
    ).filter(
        CarteiraPrincipal.ativo == True,
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        CarteiraPrincipal.cod_produto.in_(codigos_produtos)
    ).distinct().limit(10).all()

    pedidos_visiveis = [p[0] for p in pedidos_visiveis]
    print(f"   ✅ Pedidos 'visíveis' (simulado): {len(pedidos_visiveis)}")
    for p in pedidos_visiveis[:3]:
        print(f"      - {p}")
    print(f"      ... e mais {len(pedidos_visiveis) - 3}")

    # PASSO 3: Buscar separações NÃO visíveis (igual à função)
    print("\n[PASSO 3] Buscar separações NÃO visíveis...")

    query = db.session.query(
        Separacao.cod_produto,
        Separacao.expedicao,
        func.sum(Separacao.qtd_saldo).label('qtd_total')
    ).filter(
        Separacao.sincronizado_nf == False,
        Separacao.cod_produto.in_(codigos_produtos),
        Separacao.expedicao.isnot(None),
        ~Separacao.num_pedido.in_(pedidos_visiveis)
    ).group_by(
        Separacao.cod_produto,
        Separacao.expedicao
    )

    resultados = query.all()

    print(f"   ✅ Separações NÃO visíveis encontradas: {len(resultados)}")

    if not resultados:
        print("\n   ⚠️ NENHUMA separação não visível encontrada!")
        print("\n   🔍 Investigando por que...")

        # Verificar separações TOTAIS (com filtros)
        total_sep = db.session.query(
            func.count(Separacao.id)
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.cod_produto.in_(codigos_produtos),
            Separacao.expedicao.isnot(None)
        ).scalar()

        print(f"\n   Total de separações (sincronizado_nf=False, com expedicao): {total_sep}")

        # Verificar quantas estão nos pedidos visíveis
        total_visiveis = db.session.query(
            func.count(Separacao.id)
        ).filter(
            Separacao.sincronizado_nf == False,
            Separacao.cod_produto.in_(codigos_produtos),
            Separacao.expedicao.isnot(None),
            Separacao.num_pedido.in_(pedidos_visiveis)
        ).scalar()

        print(f"   Separações nos pedidos 'visíveis': {total_visiveis}")
        print(f"   Separações NÃO visíveis esperadas: {total_sep - total_visiveis}")

        sys.exit(0)

    # PASSO 4: Mostrar resultados
    print("\n[PASSO 4] Detalhes das separações NÃO visíveis:")

    saidas_por_produto = {}
    for cod_prod, data_exp, qtd_total in resultados:
        if cod_prod not in saidas_por_produto:
            saidas_por_produto[cod_prod] = []

        saidas_por_produto[cod_prod].append({
            'data': data_exp.isoformat(),
            'qtd': float(qtd_total)
        })

    for cod_prod, saidas in saidas_por_produto.items():
        print(f"\n   Produto: {cod_prod}")
        print(f"   Total de saídas: {len(saidas)}")
        total_qtd = sum(s['qtd'] for s in saidas)
        print(f"   Quantidade total: {total_qtd}")

        for saida in saidas[:3]:
            print(f"      - Data: {saida['data']}, Qtd: {saida['qtd']}")
        if len(saidas) > 3:
            print(f"      ... e mais {len(saidas) - 3} saídas")

    print("\n" + "="*80)
    print("✅ DEBUG CONCLUÍDO!")
    print("="*80)
