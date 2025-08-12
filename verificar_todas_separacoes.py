#!/usr/bin/env python3
"""
Verificar TODAS as Separações e PreSeparacaoItems do pedido VFB2500241
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.separacao.models import Separacao
from app.carteira.models import PreSeparacaoItem
from app.pedidos.models import Pedido

app = create_app()

with app.app_context():
    print("=" * 80)
    print("VERIFICAÇÃO COMPLETA DO PEDIDO VFB2500241")
    print("=" * 80)
    
    # 1. Verificar todas as Separações
    print("\n🚛 TODAS AS SEPARAÇÕES DO PEDIDO VFB2500241:")
    print("-" * 60)
    
    separacoes = Separacao.query.filter_by(num_pedido='VFB2500241').all()
    
    if separacoes:
        # Agrupar por lote
        lotes_sep = {}
        for sep in separacoes:
            if sep.separacao_lote_id not in lotes_sep:
                lotes_sep[sep.separacao_lote_id] = []
            lotes_sep[sep.separacao_lote_id].append(sep)
        
        for lote_id, items in lotes_sep.items():
            print(f"\n📦 Lote: {lote_id}")
            print(f"   Total de itens: {len(items)}")
            print(f"   Tipo envio: {items[0].tipo_envio if items else 'N/A'}")
            print(f"   Data criação: {items[0].criado_em if items else 'N/A'}")
            print("   Produtos:")
            total_qtd = 0
            for item in items:
                print(f"      - {item.cod_produto}: {item.qtd_saldo} unidades")
                total_qtd += float(item.qtd_saldo or 0)
            print(f"   Total geral: {total_qtd} unidades")
    else:
        print("   ❌ Nenhuma Separação encontrada")
    
    # 2. Verificar todas as PreSeparacaoItems
    print("\n📋 TODAS AS PRÉ-SEPARAÇÕES DO PEDIDO VFB2500241:")
    print("-" * 60)
    
    pre_seps = PreSeparacaoItem.query.filter_by(num_pedido='VFB2500241').all()
    
    if pre_seps:
        # Agrupar por lote
        lotes_pre = {}
        for pre in pre_seps:
            if pre.separacao_lote_id not in lotes_pre:
                lotes_pre[pre.separacao_lote_id] = []
            lotes_pre[pre.separacao_lote_id].append(pre)
        
        for lote_id, items in lotes_pre.items():
            print(f"\n📝 Lote: {lote_id}")
            print(f"   Total de itens: {len(items)}")
            print(f"   Status: {items[0].status if items else 'N/A'}")
            print(f"   Tipo envio: {items[0].tipo_envio if items else 'N/A'}")
            print(f"   Recomposto: {items[0].recomposto if items else 'N/A'}")
            print(f"   Data criação: {items[0].data_criacao if items else 'N/A'}")
            print("   Produtos:")
            total_qtd = 0
            for item in items:
                print(f"      - {item.cod_produto}: {item.qtd_selecionada_usuario} unidades")
                total_qtd += float(item.qtd_selecionada_usuario or 0)
            print(f"   Total geral: {total_qtd} unidades")
    else:
        print("   ❌ Nenhuma PreSeparacaoItem encontrada")
    
    # 3. Verificar Pedidos agrupados
    print("\n📊 PEDIDOS AGRUPADOS (tabela pedidos):")
    print("-" * 60)
    
    pedidos = Pedido.query.filter_by(num_pedido='VFB2500241').all()
    
    if pedidos:
        for pedido in pedidos:
            print(f"\n🎯 Lote: {pedido.separacao_lote_id}")
            print(f"   Status: {pedido.status}")
            print(f"   Valor total: R$ {pedido.valor_saldo_total:.2f}" if pedido.valor_saldo_total else "   Valor: N/A")
            print(f"   Peso total: {pedido.peso_total} kg" if pedido.peso_total else "   Peso: N/A")
            print(f"   Pallet total: {pedido.pallet_total}" if pedido.pallet_total else "   Pallet: N/A")
    else:
        print("   ❌ Nenhum Pedido agrupado encontrado")
    
    # 4. Resumo comparativo
    print("\n" + "=" * 80)
    print("📈 RESUMO COMPARATIVO:")
    print("-" * 60)
    
    # Contar lotes únicos
    todos_lotes = set()
    
    if lotes_sep:
        todos_lotes.update(lotes_sep.keys())
        print(f"✅ Separações: {len(lotes_sep)} lotes distintos")
        for lote in lotes_sep.keys():
            print(f"   - {lote}")
    
    if lotes_pre:
        todos_lotes.update(lotes_pre.keys())
        print(f"\n✅ Pré-Separações: {len(lotes_pre)} lotes distintos")
        for lote in lotes_pre.keys():
            print(f"   - {lote}")
    
    # Verificar lotes compartilhados
    if lotes_sep and lotes_pre:
        lotes_compartilhados = set(lotes_sep.keys()) & set(lotes_pre.keys())
        if lotes_compartilhados:
            print(f"\n⚠️ Lotes que existem em AMBOS (Separacao E PreSeparacao):")
            for lote in lotes_compartilhados:
                print(f"   - {lote}")
    
    print(f"\n📊 Total de lotes únicos: {len(todos_lotes)}")
    
    print("\n" + "=" * 80)