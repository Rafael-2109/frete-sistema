#!/usr/bin/env python3
"""
Script para limpar alertas órfãos (sem pedido ou com embarque cancelado)
"""

from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem

app = create_app()
with app.app_context():
    print("🔍 Analisando alertas órfãos...")
    
    # Buscar todos os alertas não reimpresos
    alertas = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).all()
    print(f"Total de alertas não reimpresos: {len(alertas)}")
    
    alertas_para_limpar = []
    alertas_validos = []
    
    for alerta in alertas:
        # Verificar se tem pedido
        pedido = Pedido.query.filter_by(separacao_lote_id=alerta.separacao_lote_id).first()
        
        if not pedido:
            print(f"❌ Alerta órfão (sem pedido): {alerta.id} - Lote: {alerta.separacao_lote_id}")
            alertas_para_limpar.append(alerta)
            continue
        
        # Verificar se tem embarque ativo
        embarque_item = EmbarqueItem.query.filter_by(
            separacao_lote_id=alerta.separacao_lote_id,
            status='ativo'
        ).first()
        
        if not embarque_item:
            # Tentar pelo número do pedido
            embarque_item = EmbarqueItem.query.filter_by(
                pedido=alerta.num_pedido,
                status='ativo'
            ).first()
        
        if not embarque_item:
            print(f"⚠️ Alerta sem embarque ativo: {alerta.id} - Pedido: {alerta.num_pedido} - Status pedido: {pedido.status}")
            alertas_para_limpar.append(alerta)
        else:
            alertas_validos.append(alerta)
    
    print(f"\n📊 RESUMO:")
    print(f"   Alertas válidos (com pedido e embarque ativo): {len(alertas_validos)}")
    print(f"   Alertas órfãos para limpar: {len(alertas_para_limpar)}")
    
    if alertas_para_limpar:
        resposta = input("\n🗑️ Deseja marcar esses alertas órfãos como reimpresos? (s/n): ")
        
        if resposta.lower() == 's':
            for alerta in alertas_para_limpar:
                alerta.reimpresso = True
                alerta.observacoes = "Marcado como reimpresso por limpeza de órfãos"
            
            db.session.commit()
            print(f"✅ {len(alertas_para_limpar)} alertas órfãos marcados como reimpresos")
        else:
            print("❌ Operação cancelada")
    else:
        print("✅ Não há alertas órfãos para limpar")