#!/usr/bin/env python3
"""
Script para visualizar alertas de separação cotada
"""

from app import create_app, db
from app.carteira.models_alertas import AlertaSeparacaoCotada
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem, Embarque
from datetime import datetime
from sqlalchemy import func

app = create_app()
with app.app_context():
    print("\n" + "="*80)
    print("📊 RELATÓRIO DE ALERTAS DE SEPARAÇÃO COTADA")
    print("="*80)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80)
    
    # Estatísticas gerais
    total_alertas = AlertaSeparacaoCotada.query.count()
    alertas_pendentes = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).count()
    alertas_reimpresos = AlertaSeparacaoCotada.query.filter_by(reimpresso=True).count()
    
    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"   Total de alertas: {total_alertas}")
    print(f"   Alertas pendentes: {alertas_pendentes}")
    print(f"   Alertas reimpresos: {alertas_reimpresos}")
    
    # Alertas por tipo
    print(f"\n📝 ALERTAS POR TIPO:")
    tipos = db.session.query(
        AlertaSeparacaoCotada.tipo_alteracao,
        func.count(AlertaSeparacaoCotada.id).label('total'),
        func.sum(func.cast(AlertaSeparacaoCotada.reimpresso == False, db.Integer)).label('pendentes')
    ).group_by(AlertaSeparacaoCotada.tipo_alteracao).all()
    
    for tipo in tipos:
        print(f"   {tipo.tipo_alteracao}: {tipo.total} total ({tipo.pendentes or 0} pendentes)")
    
    # Detalhes dos alertas pendentes
    if alertas_pendentes > 0:
        print(f"\n🔔 ALERTAS PENDENTES DE REIMPRESSÃO:")
        print("-"*80)
        
        alertas = AlertaSeparacaoCotada.query.filter_by(reimpresso=False).order_by(
            AlertaSeparacaoCotada.data_alerta.desc()
        ).limit(50).all()
        
        for alerta in alertas:
            # Buscar pedido
            pedido = Pedido.query.filter_by(separacao_lote_id=alerta.separacao_lote_id).first()
            
            # Buscar embarque
            embarque_item = EmbarqueItem.query.filter_by(
                separacao_lote_id=alerta.separacao_lote_id,
                status='ativo'
            ).first()
            
            if not embarque_item:
                embarque_item = EmbarqueItem.query.filter_by(
                    pedido=alerta.num_pedido,
                    status='ativo'
                ).first()
            
            embarque = None
            if embarque_item:
                embarque = Embarque.query.get(embarque_item.embarque_id)
            
            print(f"\n   ID: {alerta.id}")
            print(f"   Lote: {alerta.separacao_lote_id}")
            print(f"   Pedido: {alerta.num_pedido}")
            print(f"   Produto: {alerta.cod_produto} - {alerta.nome_produto}")
            print(f"   Tipo: {alerta.tipo_alteracao}")
            
            if alerta.tipo_alteracao == 'alteracao_quantidade':
                print(f"   Qtd Anterior: {alerta.qtd_anterior} → Nova: {alerta.qtd_nova}")
            elif alerta.tipo_alteracao == 'alteracao_data':
                print(f"   Data Anterior: {alerta.data_anterior} → Nova: {alerta.data_nova}")
            
            print(f"   Data Alerta: {alerta.data_alerta.strftime('%d/%m/%Y %H:%M')}")
            print(f"   Status Pedido: {pedido.status if pedido else 'SEM PEDIDO'}")
            print(f"   Embarque: {f'#{embarque.numero}' if embarque else 'SEM EMBARQUE'}")
            
            if pedido and not embarque_item:
                print(f"   ⚠️ ALERTA ÓRFÃO - Pedido existe mas sem embarque ativo")
            elif not pedido:
                print(f"   ❌ ALERTA ÓRFÃO - Sem pedido correspondente")
    
    # Últimos alertas reimpresos
    print(f"\n✅ ÚLTIMOS ALERTAS REIMPRESOS:")
    print("-"*80)
    
    alertas_reimp = AlertaSeparacaoCotada.query.filter_by(reimpresso=True).order_by(
        AlertaSeparacaoCotada.data_alerta.desc()
    ).limit(10).all()
    
    if alertas_reimp:
        for alerta in alertas_reimp:
            print(f"   ID: {alerta.id} | Lote: {alerta.separacao_lote_id} | "
                  f"Pedido: {alerta.num_pedido} | Tipo: {alerta.tipo_alteracao}")
            if alerta.data_reimpressao:
                print(f"      Reimpresso em: {alerta.data_reimpressao.strftime('%d/%m/%Y %H:%M')}")
    else:
        print("   Nenhum alerta reimpresso")
    
    print("\n" + "="*80)
    print("FIM DO RELATÓRIO")
    print("="*80)