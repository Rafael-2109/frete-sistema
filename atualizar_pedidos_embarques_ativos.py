#!/usr/bin/env python3

"""
Script para Atualizar Pedidos em Embarques Ativos

Este script atualiza APENAS os pedidos que estão em embarques ativos e que
podem estar com status ou NFs desatualizados.

Foco específico:
- Pedidos em embarques ativos
- Sincronização de NFs entre embarque → pedido
- Atualização de status apenas dos pedidos afetados
- Criação de cotações FOB quando necessário

Executar: python atualizar_pedidos_embarques_ativos.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem
from app.cotacao.models import Cotacao
from app.transportadoras.models import Transportadora
from datetime import datetime

def buscar_pedidos_em_embarques_ativos():
    """
    Busca todos os pedidos que estão em embarques ativos
    """
    print("🔍 Buscando pedidos em embarques ativos...")
    
    # Query para buscar todos os itens de embarque ativos
    itens_embarque = EmbarqueItem.query.join(Embarque).filter(
        EmbarqueItem.status == 'ativo',
        Embarque.status == 'ativo'
    ).all()
    
    print(f"📊 Encontrados {len(itens_embarque)} itens em embarques ativos")
    
    # Mapear itens para pedidos
    pedidos_em_embarques = {}
    pedidos_nao_encontrados = []
    
    for item in itens_embarque:
        pedido = None
        
        # Buscar pedido (priorizar lote de separação)
        if item.separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
        
        if not pedido and item.pedido:
            pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
        
        if pedido:
            if pedido.id not in pedidos_em_embarques:
                pedidos_em_embarques[pedido.id] = {
                    'pedido': pedido,
                    'itens_embarque': []
                }
            pedidos_em_embarques[pedido.id]['itens_embarque'].append(item)
        else:
            pedidos_nao_encontrados.append({
                'num_pedido': item.pedido,
                'lote': item.separacao_lote_id,
                'embarque': item.embarque_id,
                'nf': item.nota_fiscal
            })
    
    print(f"✅ {len(pedidos_em_embarques)} pedidos únicos encontrados")
    if pedidos_nao_encontrados:
        print(f"⚠️ {len(pedidos_nao_encontrados)} itens sem pedido correspondente")
    
    return pedidos_em_embarques, pedidos_nao_encontrados

def analisar_problemas_pedidos(pedidos_em_embarques):
    """
    Analisa quais pedidos têm problemas de sincronização
    """
    print("\n" + "="*60)
    print("🔍 ANALISANDO PROBLEMAS DE SINCRONIZAÇÃO")
    print("="*60)
    
    problemas = {
        'nfs_nao_sincronizadas': [],
        'status_incorretos': [],
        'fob_sem_cotacao': [],
        'pedidos_ok': []
    }
    
    for pedido_id, dados in pedidos_em_embarques.items():
        pedido = dados['pedido']
        itens_embarque = dados['itens_embarque']
        
        # Verificar NFs não sincronizadas
        nfs_nos_embarques = set()
        for item in itens_embarque:
            if item.nota_fiscal and item.nota_fiscal.strip():
                nfs_nos_embarques.add(item.nota_fiscal.strip())
        
        # Se há NFs nos embarques mas não no pedido, ou se são diferentes
        if nfs_nos_embarques:
            nf_embarque = list(nfs_nos_embarques)[0]  # Pega a primeira NF encontrada
            if not pedido.nf or pedido.nf.strip() != nf_embarque:
                problemas['nfs_nao_sincronizadas'].append({
                    'pedido': pedido,
                    'nf_atual': pedido.nf,
                    'nf_embarque': nf_embarque,
                    'embarques': [item.embarque_id for item in itens_embarque]
                })
        
        # Verificar status incorreto
        status_atual = pedido.status
        status_correto = pedido.status_calculado
        if status_atual != status_correto:
            problemas['status_incorretos'].append({
                'pedido': pedido,
                'status_atual': status_atual,
                'status_correto': status_correto
            })
        
        # Verificar FOB sem cotação
        if pedido.transportadora == "FOB - COLETA" and not pedido.cotacao_id:
            problemas['fob_sem_cotacao'].append({
                'pedido': pedido,
                'embarques': [item.embarque_id for item in itens_embarque]
            })
        
        # Se não tem problemas
        if (status_atual == status_correto and 
            pedido.id not in [p['pedido'].id for p in problemas['nfs_nao_sincronizadas']] and
            pedido.id not in [p['pedido'].id for p in problemas['fob_sem_cotacao']]):
            problemas['pedidos_ok'].append(pedido)
    
    # Relatório dos problemas
    print(f"📊 RESULTADO DA ANÁLISE:")
    print(f"   ✅ Pedidos OK: {len(problemas['pedidos_ok'])}")
    print(f"   🔄 NFs não sincronizadas: {len(problemas['nfs_nao_sincronizadas'])}")
    print(f"   📝 Status incorretos: {len(problemas['status_incorretos'])}")
    print(f"   🚛 FOB sem cotação: {len(problemas['fob_sem_cotacao'])}")
    
    return problemas

def corrigir_cotacoes_fob(pedidos_fob_sem_cotacao):
    """
    Cria/associa cotações para pedidos FOB
    """
    if not pedidos_fob_sem_cotacao:
        return 0
    
    print(f"\n🚛 Corrigindo {len(pedidos_fob_sem_cotacao)} pedidos FOB sem cotação...")
    
    # Buscar ou criar transportadora FOB
    transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
    if not transportadora_fob:
        print("❌ Transportadora FOB não encontrada!")
        return 0
    
    # Buscar ou criar cotação FOB global
    cotacao_fob = Cotacao.query.filter_by(
        transportadora_id=transportadora_fob.id,
        tipo_carga='FOB'
    ).first()
    
    if not cotacao_fob:
        print("🔧 Criando cotação FOB...")
        cotacao_fob = Cotacao(
            usuario_id=1,
            transportadora_id=transportadora_fob.id,
            status='Fechado',
            data_criacao=datetime.now(),
            data_fechamento=datetime.now(),
            tipo_carga='FOB',
            valor_total=0,
            peso_total=0,
            modalidade='FOB',
            nome_tabela='FOB - COLETA',
            frete_minimo_valor=0,
            valor_kg=0,
            percentual_valor=0,
            frete_minimo_peso=0,
            icms=0,
            percentual_gris=0,
            pedagio_por_100kg=0,
            valor_tas=0,
            percentual_adv=0,
            percentual_rca=0,
            valor_despacho=0,
            valor_cte=0,
            icms_incluso=False,
            icms_destino=0
        )
        db.session.add(cotacao_fob)
        db.session.flush()
        print(f"✅ Cotação FOB criada: ID {cotacao_fob.id}")
    
    # Atualizar pedidos FOB
    for item in pedidos_fob_sem_cotacao:
        pedido = item['pedido']
        pedido.cotacao_id = cotacao_fob.id
        print(f"   ✅ Pedido {pedido.num_pedido}: cotacao_id = {cotacao_fob.id}")
    
    return len(pedidos_fob_sem_cotacao)

def corrigir_nfs_nao_sincronizadas(nfs_nao_sincronizadas):
    """
    Sincroniza NFs dos embarques para os pedidos
    """
    if not nfs_nao_sincronizadas:
        return 0
    
    print(f"\n📝 Sincronizando {len(nfs_nao_sincronizadas)} NFs...")
    
    for item in nfs_nao_sincronizadas:
        pedido = item['pedido']
        nf_embarque = item['nf_embarque']
        nf_anterior = item['nf_atual']
        
        pedido.nf = nf_embarque
        print(f"   🔄 Pedido {pedido.num_pedido}: '{nf_anterior or 'None'}' → '{nf_embarque}'")
    
    return len(nfs_nao_sincronizadas)

def corrigir_status_incorretos(status_incorretos):
    """
    Corrige status dos pedidos
    """
    if not status_incorretos:
        return 0
    
    print(f"\n📊 Corrigindo {len(status_incorretos)} status...")
    
    for item in status_incorretos:
        pedido = item['pedido']
        status_atual = item['status_atual']
        status_correto = item['status_correto']
        
        pedido.status = status_correto
        print(f"   📝 Pedido {pedido.num_pedido}: '{status_atual}' → '{status_correto}'")
    
    return len(status_incorretos)

def verificar_resultados_apos_correcoes(pedidos_em_embarques):
    """
    Verifica se as correções funcionaram
    """
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO FINAL")
    print("="*60)
    
    pedidos_verificados = 0
    problemas_restantes = 0
    
    for pedido_id, dados in pedidos_em_embarques.items():
        pedido = dados['pedido']
        
        # Recarrega o pedido do banco para ver os dados atualizados
        db.session.refresh(pedido)
        
        status_atual = pedido.status
        status_correto = pedido.status_calculado
        
        pedidos_verificados += 1
        
        if status_atual != status_correto:
            problemas_restantes += 1
            print(f"   ⚠️ Pedido {pedido.num_pedido}: status ainda incorreto ({status_atual} vs {status_correto})")
        
        # Verificar FOB sem cotação
        if pedido.transportadora == "FOB - COLETA" and not pedido.cotacao_id:
            problemas_restantes += 1
            print(f"   ⚠️ Pedido {pedido.num_pedido}: FOB ainda sem cotação")
    
    print(f"\n📊 RESULTADO FINAL:")
    print(f"   • Pedidos verificados: {pedidos_verificados}")
    print(f"   • Problemas restantes: {problemas_restantes}")
    
    if problemas_restantes == 0:
        print("   🎉 TODOS OS PROBLEMAS FORAM CORRIGIDOS!")
    else:
        print(f"   ⚠️ {problemas_restantes} problemas ainda precisam atenção")
    
    return problemas_restantes

def main():
    """Função principal"""
    
    print("🔧 ATUALIZAÇÃO DE PEDIDOS EM EMBARQUES ATIVOS")
    print("=" * 60)
    print("Este script atualiza APENAS pedidos que estão em embarques ativos")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Buscar pedidos em embarques ativos
            pedidos_em_embarques, pedidos_nao_encontrados = buscar_pedidos_em_embarques_ativos()
            
            if not pedidos_em_embarques:
                print("❌ Nenhum pedido encontrado em embarques ativos!")
                return
            
            # 2. Analisar problemas
            problemas = analisar_problemas_pedidos(pedidos_em_embarques)
            
            total_problemas = (len(problemas['nfs_nao_sincronizadas']) + 
                             len(problemas['status_incorretos']) + 
                             len(problemas['fob_sem_cotacao']))
            
            if total_problemas == 0:
                print("\n🎉 NENHUM PROBLEMA ENCONTRADO!")
                print("Todos os pedidos em embarques ativos estão corretos! ✅")
                return
            
            print(f"\n🔧 Iniciando correções de {total_problemas} problemas...")
            
            # 3. Fazer correções
            fob_corrigidos = corrigir_cotacoes_fob(problemas['fob_sem_cotacao'])
            nfs_corrigidas = corrigir_nfs_nao_sincronizadas(problemas['nfs_nao_sincronizadas'])
            status_corrigidos = corrigir_status_incorretos(problemas['status_incorretos'])
            
            # 4. Commit das alterações
            db.session.commit()
            print("\n💾 Alterações salvas no banco de dados!")
            
            # 5. Verificação final
            problemas_restantes = verificar_resultados_apos_correcoes(pedidos_em_embarques)
            
            # 6. Resumo final
            print("\n" + "="*60)
            print("📋 RESUMO DAS CORREÇÕES")
            print("="*60)
            print(f"✅ Cotações FOB criadas: {fob_corrigidos}")
            print(f"✅ NFs sincronizadas: {nfs_corrigidas}")
            print(f"✅ Status corrigidos: {status_corrigidos}")
            print(f"📊 Pedidos em embarques ativos: {len(pedidos_em_embarques)}")
            
            if pedidos_nao_encontrados:
                print(f"⚠️ Itens sem pedido correspondente: {len(pedidos_nao_encontrados)}")
            
            if problemas_restantes == 0:
                print("\n🚀 MANUTENÇÃO CONCLUÍDA COM SUCESSO!")
            else:
                print(f"\n⚠️ {problemas_restantes} problemas ainda precisam atenção manual")
            
        except Exception as e:
            print(f"\n❌ ERRO durante a atualização: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    main() 