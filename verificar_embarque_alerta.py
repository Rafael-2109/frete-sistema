#!/usr/bin/env python3
"""
Script para verificar porque alerta não aparece em lista_pedidos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem

app = create_app()

with app.app_context():
    print("=" * 60)
    print("VERIFICAÇÃO DO PROBLEMA DO ALERTA VFB2500241")
    print("=" * 60)
    
    # 1. Verificar o alerta
    print("\n1️⃣ ALERTA DO PEDIDO VFB2500241:")
    alerta = AlertaSeparacaoCotada.query.filter_by(
        num_pedido='VFB2500241',
        separacao_lote_id='LOTE-20250811-173-193822'
    ).first()
    
    if alerta:
        print(f"   ✅ Alerta encontrado: ID {alerta.id}")
        print(f"   - Reimpresso: {alerta.reimpresso}")
        print(f"   - Tipo: {alerta.tipo_alteracao}")
    else:
        print("   ❌ Alerta não encontrado!")
    
    # 2. Verificar o Pedido
    print("\n2️⃣ PEDIDO VFB2500241:")
    pedido = Pedido.query.filter_by(
        num_pedido='VFB2500241',
        separacao_lote_id='LOTE-20250811-173-193822'
    ).first()
    
    if pedido:
        print(f"   ✅ Pedido encontrado")
        print(f"   - Status: {pedido.status}")
        print(f"   - Lote: {pedido.separacao_lote_id}")
    else:
        print("   ❌ Pedido não encontrado com este lote!")
    
    # 3. Verificar EmbarqueItem
    print("\n3️⃣ EMBARQUE ITEM:")
    embarque_item = EmbarqueItem.query.filter_by(
        separacao_lote_id='LOTE-20250811-173-193822'
    ).first()
    
    if embarque_item:
        print(f"   ✅ EmbarqueItem encontrado")
        print(f"   - Embarque ID: {embarque_item.embarque_id}")
        print(f"   - Status: {embarque_item.status}")
        print(f"   - Pedido: {embarque_item.pedido}")
        
        # Verificar o Embarque
        embarque = Embarque.query.get(embarque_item.embarque_id)
        if embarque:
            print(f"\n4️⃣ EMBARQUE:")
            print(f"   - Número: {embarque.numero}")
            print(f"   - Status: {embarque.status}")
            print(f"   - Transportadora ID: {embarque.transportadora_id}")
            
            # Testar se transportadora tem razao_social
            if embarque.transportadora:
                print(f"   - Transportadora tem razao_social? {hasattr(embarque.transportadora, 'razao_social')}")
                if hasattr(embarque.transportadora, 'razao_social'):
                    print(f"   - Razão Social: {embarque.transportadora.razao_social}")
    else:
        print("   ❌ EmbarqueItem não encontrado com este lote!")
    
    # 5. Verificar todos os EmbarqueItems do pedido
    print("\n5️⃣ TODOS OS EMBARQUE ITEMS DO PEDIDO VFB2500241:")
    todos_items = EmbarqueItem.query.filter_by(pedido='VFB2500241').all()
    
    if todos_items:
        for item in todos_items:
            print(f"   - Lote: {item.separacao_lote_id}, Embarque: {item.embarque_id}, Status: {item.status}")
    else:
        print("   ❌ Nenhum EmbarqueItem para este pedido!")
    
    print("\n" + "=" * 60)