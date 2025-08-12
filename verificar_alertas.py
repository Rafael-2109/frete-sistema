#!/usr/bin/env python3
"""
Script para verificar alertas gerados no banco de dados
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.separacao.models import Separacao

app = create_app()

with app.app_context():
    print("=" * 60)
    print("VERIFICAÇÃO DE ALERTAS DE SEPARAÇÕES COTADAS")
    print("=" * 60)
    
    # 1. Verificar todos os alertas no banco
    print("\n📋 TODOS OS ALERTAS NO BANCO:")
    alertas = AlertaSeparacaoCotada.query.all()
    
    if not alertas:
        print("   ❌ Nenhum alerta encontrado no banco!")
    else:
        for alerta in alertas:
            print(f"\n   ID: {alerta.id}")
            print(f"   Pedido: {alerta.num_pedido}")
            print(f"   Lote: {alerta.separacao_lote_id}")
            print(f"   Produto: {alerta.cod_produto}")
            print(f"   Tipo: {alerta.tipo_alteracao}")
            print(f"   Qtd Anterior: {alerta.qtd_anterior}")
            print(f"   Qtd Nova: {alerta.qtd_nova}")
            print(f"   Reimpresso: {alerta.reimpresso}")
            print(f"   Data: {alerta.data_alerta}")
            print(f"   Observação: {alerta.observacao}")
    
    # 2. Verificar alertas pendentes (não reimpresos)
    print("\n🚨 ALERTAS PENDENTES (não reimpresos):")
    alertas_pendentes = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).all()
    
    if not alertas_pendentes:
        print("   ❌ Nenhum alerta pendente!")
    else:
        print(f"   ✅ {len(alertas_pendentes)} alertas pendentes")
        for alerta in alertas_pendentes:
            print(f"      - {alerta.num_pedido} / {alerta.separacao_lote_id}")
    
    # 3. Verificar pedido específico VFB2500241
    print("\n🔍 VERIFICANDO PEDIDO VFB2500241:")
    
    # Verificar Pedido
    pedido = Pedido.query.filter_by(num_pedido='VFB2500241').first()
    if pedido:
        print(f"   Pedido encontrado:")
        print(f"   - Lote: {pedido.separacao_lote_id}")
        print(f"   - Status: {pedido.status}")
    
    # Verificar Separações
    separacoes = Separacao.query.filter_by(num_pedido='VFB2500241').all()
    if separacoes:
        print(f"\n   Separações encontradas: {len(separacoes)}")
        for sep in separacoes[:3]:  # Mostrar apenas 3 primeiras
            print(f"   - Lote: {sep.separacao_lote_id}, Produto: {sep.cod_produto}, Qtd: {sep.qtd_saldo}")
    
    # Verificar alertas deste pedido
    alertas_pedido = AlertaSeparacaoCotada.query.filter_by(num_pedido='VFB2500241').all()
    if alertas_pedido:
        print(f"\n   ✅ Alertas do pedido: {len(alertas_pedido)}")
        for alerta in alertas_pedido:
            print(f"      - Lote: {alerta.separacao_lote_id}, Produto: {alerta.cod_produto}")
    else:
        print("\n   ❌ Nenhum alerta para este pedido!")
    
    # 4. Testar método buscar_alertas_pendentes
    print("\n📊 TESTE DO MÉTODO buscar_alertas_pendentes():")
    alertas_agrupados = AlertaSeparacaoCotada.buscar_alertas_pendentes()
    
    if not alertas_agrupados:
        print("   ❌ Nenhum alerta retornado pelo método")
    else:
        print(f"   ✅ {len(alertas_agrupados)} embarques com alertas")
        for embarque_num, info in alertas_agrupados.items():
            print(f"      - Embarque {embarque_num}: {len(info['pedidos'])} pedidos")
    
    print("\n" + "=" * 60)