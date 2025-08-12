#!/usr/bin/env python3
"""
Testar exatamente o que a API de alertas retorna
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
import json

app = create_app()

with app.app_context():
    print("=" * 60)
    print("TESTE DA API DE ALERTAS")
    print("=" * 60)
    
    # Chamar o método exatamente como a API faz
    alertas = AlertaSeparacaoCotada.buscar_alertas_pendentes()
    total_alertas = AlertaSeparacaoCotada.contar_alertas_pendentes()
    
    print(f"\n📊 Total de alertas pendentes: {total_alertas}")
    print(f"📦 Embarques com alertas: {len(alertas)}")
    
    # Mostrar detalhes de cada embarque
    for embarque_num, embarque_info in alertas.items():
        print(f"\n🚛 EMBARQUE #{embarque_num}:")
        print(f"   ID: {embarque_info['embarque_id']}")
        print(f"   Data: {embarque_info['data_embarque']}")
        print(f"   Transportadora: {embarque_info['transportadora']}")
        print(f"   Pedidos afetados: {len(embarque_info['pedidos'])}")
        
        for num_pedido, pedido_info in embarque_info['pedidos'].items():
            print(f"\n   📋 Pedido {num_pedido}:")
            print(f"      Lote: {pedido_info['separacao_lote_id']}")
            print(f"      Cliente: {pedido_info['cliente']}")
            print(f"      Itens alterados: {len(pedido_info['itens'])}")
            
            for item in pedido_info['itens'][:2]:  # Mostrar apenas 2 primeiros
                print(f"         - {item['cod_produto']}: {item['qtd_anterior']} → {item['qtd_nova']} ({item['tipo_alteracao']})")
    
    # Verificar especificamente o pedido VFB2500241
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO ESPECÍFICA DO VFB2500241:")
    
    encontrou_vfb = False
    for embarque_num, embarque_info in alertas.items():
        if 'VFB2500241' in embarque_info['pedidos']:
            encontrou_vfb = True
            print(f"✅ Pedido VFB2500241 encontrado no Embarque #{embarque_num}")
            pedido_info = embarque_info['pedidos']['VFB2500241']
            print(f"   Itens com alerta: {len(pedido_info['itens'])}")
            for item in pedido_info['itens']:
                print(f"   - {item['cod_produto']}: {item['tipo_alteracao']}")
    
    if not encontrou_vfb:
        print("❌ Pedido VFB2500241 NÃO está nos alertas retornados!")
        
        # Verificar diretamente o alerta
        alerta_direto = AlertaSeparacaoCotada.query.filter_by(
            num_pedido='VFB2500241',
            reimpresso=False
        ).order_by(AlertaSeparacaoCotada.id.desc()).first()
        
        if alerta_direto:
            print(f"\nMas existe alerta direto no banco:")
            print(f"   ID: {alerta_direto.id}")
            print(f"   Lote: {alerta_direto.separacao_lote_id}")
            print(f"   Produto: {alerta_direto.cod_produto}")
            print(f"   Tipo: {alerta_direto.tipo_alteracao}")
    
    print("\n" + "=" * 60)