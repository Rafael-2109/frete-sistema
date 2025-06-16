#!/usr/bin/env python3

"""
Script de Verificação de Problemas nos Pedidos (Somente Leitura)

Este script apenas VERIFICA problemas sem fazer correções:
1. Pedidos FOB sem cotacao_id
2. Pedidos com status incorreto
3. NFs que faltam nos pedidos

Executar: python verificar_problemas_pedidos.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem
from app.cotacao.models import Cotacao
from app.transportadoras.models import Transportadora

def verificar_pedidos_fob_sem_cotacao():
    """Verifica pedidos FOB que não possuem cotacao_id"""
    print("\n" + "="*50)
    print("1️⃣ PEDIDOS FOB SEM COTAÇÃO")
    print("="*50)
    
    pedidos_fob_sem_cotacao = Pedido.query.filter(
        Pedido.transportadora == "FOB - COLETA",
        Pedido.cotacao_id.is_(None)
    ).all()
    
    print(f"📊 Encontrados: {len(pedidos_fob_sem_cotacao)} pedidos FOB sem cotação")
    
    if pedidos_fob_sem_cotacao:
        print("\n⚠️ PROBLEMAS ENCONTRADOS:")
        for pedido in pedidos_fob_sem_cotacao[:10]:  # Mostra apenas os 10 primeiros
            print(f"   • Pedido {pedido.num_pedido} - Status: {pedido.status_calculado}")
        
        if len(pedidos_fob_sem_cotacao) > 10:
            print(f"   • ... e mais {len(pedidos_fob_sem_cotacao) - 10} pedidos")
    else:
        print("✅ Todos os pedidos FOB possuem cotação!")
    
    return len(pedidos_fob_sem_cotacao)

def verificar_status_incorretos():
    """Verifica pedidos com status incorreto"""
    print("\n" + "="*50)
    print("2️⃣ PEDIDOS COM STATUS INCORRETO")
    print("="*50)
    
    pedidos = Pedido.query.all()
    status_incorretos = []
    
    for pedido in pedidos:
        status_atual = pedido.status
        status_correto = pedido.status_calculado
        
        if status_atual != status_correto:
            status_incorretos.append({
                'pedido': pedido.num_pedido,
                'atual': status_atual,
                'correto': status_correto,
                'nf': pedido.nf or 'SEM NF',
                'cotacao': pedido.cotacao_id or 'SEM COTAÇÃO'
            })
    
    print(f"📊 Encontrados: {len(status_incorretos)} pedidos com status incorreto")
    
    if status_incorretos:
        print("\n⚠️ PROBLEMAS ENCONTRADOS:")
        for problema in status_incorretos[:10]:  # Mostra apenas os 10 primeiros
            print(f"   • Pedido {problema['pedido']}: '{problema['atual']}' → '{problema['correto']}'")
            print(f"     NF: {problema['nf']}, Cotação: {problema['cotacao']}")
        
        if len(status_incorretos) > 10:
            print(f"   • ... e mais {len(status_incorretos) - 10} pedidos")
    else:
        print("✅ Todos os status estão corretos!")
    
    return len(status_incorretos)

def verificar_nfs_nao_sincronizadas():
    """Verifica NFs que faltam nos pedidos"""
    print("\n" + "="*50)
    print("3️⃣ NFs NÃO SINCRONIZADAS")
    print("="*50)
    
    # Buscar itens de embarque ativos com NF preenchida
    itens_com_nf = EmbarqueItem.query.join(Embarque).filter(
        EmbarqueItem.nota_fiscal.isnot(None),
        EmbarqueItem.nota_fiscal != '',
        EmbarqueItem.status == 'ativo',
        Embarque.status == 'ativo'
    ).all()
    
    print(f"📊 Analisando {len(itens_com_nf)} itens de embarque com NF...")
    
    nfs_nao_sincronizadas = []
    pedidos_nao_encontrados = []
    
    for item in itens_com_nf:
        pedido = None
        
        # Buscar pedido correspondente
        if item.separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
        
        if not pedido and item.pedido:
            pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
        
        if not pedido:
            pedidos_nao_encontrados.append({
                'pedido': item.pedido,
                'lote': item.separacao_lote_id,
                'nf': item.nota_fiscal,
                'embarque': item.embarque_id
            })
            continue
        
        # Verificar se a NF do pedido está sincronizada
        if not pedido.nf or pedido.nf != item.nota_fiscal:
            nfs_nao_sincronizadas.append({
                'pedido': pedido.num_pedido,
                'nf_embarque': item.nota_fiscal,
                'nf_pedido': pedido.nf or 'SEM NF',
                'status': pedido.status_calculado,
                'embarque': item.embarque_id,
                'transportadora': pedido.transportadora
            })
    
    print(f"📊 Encontrados:")
    print(f"   • NFs não sincronizadas: {len(nfs_nao_sincronizadas)}")
    print(f"   • Pedidos não encontrados: {len(pedidos_nao_encontrados)}")
    
    if nfs_nao_sincronizadas:
        print("\n⚠️ NFs NÃO SINCRONIZADAS:")
        for problema in nfs_nao_sincronizadas[:10]:
            print(f"   • Pedido {problema['pedido']}: '{problema['nf_pedido']}' → '{problema['nf_embarque']}'")
            print(f"     Status: {problema['status']}, Embarque: {problema['embarque']}")
        
        if len(nfs_nao_sincronizadas) > 10:
            print(f"   • ... e mais {len(nfs_nao_sincronizadas) - 10} problemas")
    
    if pedidos_nao_encontrados:
        print("\n❌ PEDIDOS NÃO ENCONTRADOS:")
        for problema in pedidos_nao_encontrados[:5]:
            print(f"   • Pedido {problema['pedido']} (lote: {problema['lote']}) - NF: {problema['nf']}")
        
        if len(pedidos_nao_encontrados) > 5:
            print(f"   • ... e mais {len(pedidos_nao_encontrados) - 5} problemas")
    
    return len(nfs_nao_sincronizadas), len(pedidos_nao_encontrados)

def mostrar_estatisticas_gerais():
    """Mostra estatísticas gerais do sistema"""
    print("\n" + "="*50)
    print("📊 ESTATÍSTICAS GERAIS")
    print("="*50)
    
    # Contadores gerais
    total_pedidos = Pedido.query.count()
    pedidos_fob = Pedido.query.filter_by(transportadora="FOB - COLETA").count()
    pedidos_com_nf = Pedido.query.filter(Pedido.nf.isnot(None), Pedido.nf != '').count()
    pedidos_com_cotacao = Pedido.query.filter(Pedido.cotacao_id.isnot(None)).count()
    
    print(f"📈 NÚMEROS GERAIS:")
    print(f"   • Total de pedidos: {total_pedidos}")
    print(f"   • Pedidos FOB: {pedidos_fob}")
    print(f"   • Pedidos com NF: {pedidos_com_nf}")
    print(f"   • Pedidos com cotação: {pedidos_com_cotacao}")
    print(f"   • Cobertura de cotações: {(pedidos_com_cotacao/total_pedidos*100):.1f}%")
    
    # Status dos pedidos
    status_query = db.session.query(
        Pedido.status, 
        db.func.count(Pedido.id)
    ).group_by(Pedido.status).all()
    
    print(f"\n📊 DISTRIBUIÇÃO POR STATUS:")
    for status, count in status_query:
        print(f"   • {status}: {count} pedidos ({(count/total_pedidos*100):.1f}%)")
    
    # Transportadoras mais usadas
    transp_query = db.session.query(
        Pedido.transportadora, 
        db.func.count(Pedido.id)
    ).filter(Pedido.transportadora.isnot(None)).group_by(Pedido.transportadora).order_by(
        db.func.count(Pedido.id).desc()
    ).limit(5).all()
    
    print(f"\n🚛 TOP 5 TRANSPORTADORAS:")
    for transp, count in transp_query:
        print(f"   • {transp}: {count} pedidos")

def main():
    """Função principal"""
    
    print("🔍 VERIFICAÇÃO DE PROBLEMAS NO SISTEMA DE PEDIDOS")
    print("=" * 60)
    print("Este script apenas VERIFICA problemas sem fazer correções.")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Verificações
            fob_sem_cotacao = verificar_pedidos_fob_sem_cotacao()
            status_incorretos = verificar_status_incorretos()
            nfs_nao_sync, pedidos_nao_encontrados = verificar_nfs_nao_sincronizadas()
            
            # Estatísticas gerais
            mostrar_estatisticas_gerais()
            
            # Resumo final
            print("\n" + "="*50)
            print("📋 RESUMO DOS PROBLEMAS ENCONTRADOS")
            print("="*50)
            print(f"⚠️ Pedidos FOB sem cotação: {fob_sem_cotacao}")
            print(f"⚠️ Pedidos com status incorreto: {status_incorretos}")
            print(f"⚠️ NFs não sincronizadas: {nfs_nao_sync}")
            print(f"❌ Pedidos não encontrados: {pedidos_nao_encontrados}")
            
            total_problemas = fob_sem_cotacao + status_incorretos + nfs_nao_sync + pedidos_nao_encontrados
            
            if total_problemas > 0:
                print(f"\n🔧 TOTAL DE PROBLEMAS: {total_problemas}")
                print("\n💡 Para CORRIGIR os problemas, execute:")
                print("   python script_manutencao_pedidos_completo.py")
            else:
                print("\n🎉 NENHUM PROBLEMA ENCONTRADO!")
                print("   O sistema está funcionando corretamente! ✅")
            
        except Exception as e:
            print(f"\n❌ ERRO durante a verificação: {str(e)}")
            raise

if __name__ == "__main__":
    main() 