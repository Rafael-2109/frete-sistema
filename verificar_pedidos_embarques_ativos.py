#!/usr/bin/env python3

"""
Script para Verificar Pedidos em Embarques Ativos (APENAS LEITURA)

Este script APENAS VERIFICA problemas nos pedidos que estão em embarques ativos.
NÃO faz alterações no banco de dados.

Verifica:
- Pedidos em embarques ativos
- NFs desatualizadas
- Status incorretos 
- Pedidos FOB sem cotação

Executar: python verificar_pedidos_embarques_ativos.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem
from app.cotacao.models import Cotacao
from app.transportadoras.models import Transportadora

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

def analisar_problemas_detalhado(pedidos_em_embarques):
    """
    Analisa problemas com detalhes para relatório
    """
    print("\n" + "="*80)
    print("🔍 ANÁLISE DETALHADA DE PROBLEMAS")
    print("="*80)
    
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
        problema_nf = False
        if nfs_nos_embarques:
            nf_embarque = list(nfs_nos_embarques)[0]  # Pega a primeira NF encontrada
            if not pedido.nf or pedido.nf.strip() != nf_embarque:
                problemas['nfs_nao_sincronizadas'].append({
                    'pedido': pedido,
                    'nf_atual': pedido.nf,
                    'nf_embarque': nf_embarque,
                    'embarques': [item.embarque_id for item in itens_embarque]
                })
                problema_nf = True
        
        # Verificar status incorreto
        status_atual = pedido.status
        status_correto = pedido.status_calculado
        problema_status = False
        if status_atual != status_correto:
            problemas['status_incorretos'].append({
                'pedido': pedido,
                'status_atual': status_atual,
                'status_correto': status_correto
            })
            problema_status = True
        
        # Verificar FOB sem cotação
        problema_fob = False
        if pedido.transportadora == "FOB - COLETA" and not pedido.cotacao_id:
            problemas['fob_sem_cotacao'].append({
                'pedido': pedido,
                'embarques': [item.embarque_id for item in itens_embarque]
            })
            problema_fob = True
        
        # Se não tem problemas
        if not (problema_nf or problema_status or problema_fob):
            problemas['pedidos_ok'].append(pedido)
    
    return problemas

def exibir_relatorio_detalhado(problemas, pedidos_nao_encontrados):
    """
    Exibe relatório detalhado dos problemas encontrados
    """
    print("\n" + "="*80)
    print("📊 RELATÓRIO DE PROBLEMAS ENCONTRADOS")
    print("="*80)
    
    # Resumo geral
    total_problemas = (len(problemas['nfs_nao_sincronizadas']) + 
                      len(problemas['status_incorretos']) + 
                      len(problemas['fob_sem_cotacao']))
    
    print(f"📈 RESUMO GERAL:")
    print(f"   ✅ Pedidos OK: {len(problemas['pedidos_ok'])}")
    print(f"   ❌ Pedidos com problemas: {total_problemas}")
    print(f"   📊 Total de pedidos: {len(problemas['pedidos_ok']) + total_problemas}")
    
    # 1. NFs não sincronizadas
    if problemas['nfs_nao_sincronizadas']:
        print(f"\n🔄 NFs NÃO SINCRONIZADAS ({len(problemas['nfs_nao_sincronizadas'])}):")
        print("-" * 60)
        for item in problemas['nfs_nao_sincronizadas']:
            pedido = item['pedido']
            nf_atual = item['nf_atual'] or 'None'
            nf_embarque = item['nf_embarque']
            embarques = ', '.join(map(str, item['embarques']))
            
            print(f"   📝 Pedido {pedido.num_pedido}:")
            print(f"      • NF atual no pedido: '{nf_atual}'")
            print(f"      • NF nos embarques: '{nf_embarque}'")
            print(f"      • Embarques: {embarques}")
            print(f"      • Transportadora: {pedido.transportadora}")
            print()
    
    # 2. Status incorretos
    if problemas['status_incorretos']:
        print(f"\n📝 STATUS INCORRETOS ({len(problemas['status_incorretos'])}):")
        print("-" * 60)
        for item in problemas['status_incorretos']:
            pedido = item['pedido']
            status_atual = item['status_atual']
            status_correto = item['status_correto']
            
            print(f"   📊 Pedido {pedido.num_pedido}:")
            print(f"      • Status atual: '{status_atual}'")
            print(f"      • Status correto: '{status_correto}'")
            print(f"      • Transportadora: {pedido.transportadora}")
            print(f"      • NF: {pedido.nf or 'None'}")
            print()
    
    # 3. FOB sem cotação
    if problemas['fob_sem_cotacao']:
        print(f"\n🚛 PEDIDOS FOB SEM COTAÇÃO ({len(problemas['fob_sem_cotacao'])}):")
        print("-" * 60)
        for item in problemas['fob_sem_cotacao']:
            pedido = item['pedido']
            embarques = ', '.join(map(str, item['embarques']))
            
            print(f"   🚛 Pedido {pedido.num_pedido}:")
            print(f"      • Transportadora: {pedido.transportadora}")
            print(f"      • Cotação ID: {pedido.cotacao_id or 'None'}")
            print(f"      • Embarques: {embarques}")
            print(f"      • Status: {pedido.status}")
            print()
    
    # 4. Itens sem pedido correspondente
    if pedidos_nao_encontrados:
        print(f"\n⚠️ ITENS SEM PEDIDO CORRESPONDENTE ({len(pedidos_nao_encontrados)}):")
        print("-" * 60)
        for item in pedidos_nao_encontrados:
            print(f"   🔍 Embarque {item['embarque']}:")
            print(f"      • Num Pedido: {item['num_pedido']}")
            print(f"      • Lote: {item['lote']}")
            print(f"      • NF: {item['nf']}")
            print()
    
    # 5. Pedidos OK (apenas resumo)
    if problemas['pedidos_ok']:
        print(f"\n✅ PEDIDOS SEM PROBLEMAS ({len(problemas['pedidos_ok'])}):")
        print("-" * 60)
        transportadoras = {}
        for pedido in problemas['pedidos_ok']:
            transp = pedido.transportadora or 'Não informado'
            transportadoras[transp] = transportadoras.get(transp, 0) + 1
        
        for transp, count in transportadoras.items():
            print(f"   • {transp}: {count} pedido(s)")
    
    # Recomendações
    print(f"\n" + "="*80)
    print("💡 RECOMENDAÇÕES")
    print("="*80)
    
    if total_problemas == 0:
        print("🎉 EXCELENTE! Todos os pedidos em embarques ativos estão corretos!")
        print("   Nenhuma ação necessária.")
    else:
        print(f"🔧 Encontrados {total_problemas} problemas que podem ser corrigidos.")
        print("   Para corrigir automaticamente, execute:")
        print("   python atualizar_pedidos_embarques_ativos.py")
        
        if problemas['nfs_nao_sincronizadas']:
            print(f"\n📝 NFs não sincronizadas: {len(problemas['nfs_nao_sincronizadas'])}")
            print("   • Serão copiadas as NFs dos embarques para os pedidos")
        
        if problemas['status_incorretos']:
            print(f"\n📊 Status incorretos: {len(problemas['status_incorretos'])}")
            print("   • Serão atualizados usando a lógica status_calculado")
        
        if problemas['fob_sem_cotacao']:
            print(f"\n🚛 FOB sem cotação: {len(problemas['fob_sem_cotacao'])}")
            print("   • Será criada/associada cotação FOB global")
    
    print("\n" + "="*80)

def main():
    """Função principal"""
    
    print("🔍 VERIFICAÇÃO DE PEDIDOS EM EMBARQUES ATIVOS")
    print("=" * 80)
    print("Este script APENAS VERIFICA problemas - NÃO faz alterações!")
    print("=" * 80)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Buscar pedidos em embarques ativos
            pedidos_em_embarques, pedidos_nao_encontrados = buscar_pedidos_em_embarques_ativos()
            
            if not pedidos_em_embarques:
                print("❌ Nenhum pedido encontrado em embarques ativos!")
                return
            
            # 2. Analisar problemas
            problemas = analisar_problemas_detalhado(pedidos_em_embarques)
            
            # 3. Exibir relatório detalhado
            exibir_relatorio_detalhado(problemas, pedidos_nao_encontrados)
            
        except Exception as e:
            print(f"\n❌ ERRO durante a verificação: {str(e)}")
            raise

if __name__ == "__main__":
    main() 