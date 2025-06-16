#!/usr/bin/env python3

"""
Script de Manutenção Completo do Sistema de Pedidos

Este script realiza 3 operações principais:
1. Cria cotações para pedidos FOB que não possuem cotacao_id
2. Atualiza status de todos os pedidos, 3. Verifica NFs que deveriam estar nos pedidos mas não estão.

Executar: python script_manutencao_pedidos_completo.py
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

def criar_cotacoes_fob():
    """
    1. Cria cotações para pedidos FOB que não possuem cotacao_id
    """
    print("\n" + "="*60)
    print("1️⃣ CRIANDO COTAÇÕES PARA PEDIDOS FOB")
    print("="*60)
    
    # Buscar pedidos FOB sem cotacao_id
    pedidos_fob_sem_cotacao = Pedido.query.filter(
        Pedido.transportadora == "FOB - COLETA",
        Pedido.cotacao_id.is_(None)
    ).all()
    
    print(f"📊 Encontrados {len(pedidos_fob_sem_cotacao)} pedidos FOB sem cotação")
    
    if not pedidos_fob_sem_cotacao:
        print("✅ Todos os pedidos FOB já possuem cotação!")
        return 0
    
    # Buscar ou criar transportadora FOB
    transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
    
    if not transportadora_fob:
        print("❌ Transportadora 'FOB - COLETA' não encontrada! Criando...")
        transportadora_fob = Transportadora(
            razao_social="FOB - COLETA",
            cnpj="00000000000000",
            cidade="FOB",
            uf="SP",
            optante=False,
            condicao_pgto="FOB"
        )
        db.session.add(transportadora_fob)
        db.session.flush()
        print(f"✅ Transportadora FOB criada com ID: {transportadora_fob.id}")
    
    # Verificar se já existe uma cotação FOB global
    cotacao_fob_global = Cotacao.query.filter_by(
        transportadora_id=transportadora_fob.id,
        tipo_carga='FOB',
        nome_tabela='FOB - COLETA'
    ).first()
    
    if not cotacao_fob_global:
        print("🔧 Criando cotação FOB global...")
        cotacao_fob_global = Cotacao(
            usuario_id=1,  # Sistema
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
        db.session.add(cotacao_fob_global)
        db.session.flush()
        print(f"✅ Cotação FOB global criada com ID: {cotacao_fob_global.id}")
    else:
        print(f"✅ Cotação FOB global já existe com ID: {cotacao_fob_global.id}")
    
    # Atualizar todos os pedidos FOB sem cotacao_id
    pedidos_atualizados = 0
    for pedido in pedidos_fob_sem_cotacao:
        pedido.cotacao_id = cotacao_fob_global.id
        if not pedido.transportadora:
            pedido.transportadora = "FOB - COLETA"
        pedidos_atualizados += 1
        print(f"   ✅ Pedido {pedido.num_pedido}: cotacao_id definido como {cotacao_fob_global.id}")
    
    db.session.commit()
    print(f"\n🎉 RESULTADO: {pedidos_atualizados} pedidos FOB atualizados com cotação!")
    return pedidos_atualizados

def atualizar_status_todos_pedidos():
    """
    2. Atualiza o status de todos os pedidos baseado na lógica status_calculado
    """
    print("\n" + "="*60)
    print("2️⃣ ATUALIZANDO STATUS DE TODOS OS PEDIDOS")
    print("="*60)
    
    pedidos = Pedido.query.all()
    print(f"📊 Processando {len(pedidos)} pedidos...")
    
    atualizados = 0
    status_count = {}
    
    for pedido in pedidos:
        status_atual = pedido.status
        status_correto = pedido.status_calculado
        
        # Contabiliza estatísticas
        status_count[status_correto] = status_count.get(status_correto, 0) + 1
        
        if status_atual != status_correto:
            print(f"   🔄 Pedido {pedido.num_pedido}: '{status_atual}' → '{status_correto}'")
            pedido.status = status_correto
            atualizados += 1
    
    if atualizados > 0:
        db.session.commit()
        print(f"\n🎉 RESULTADO: {atualizados} status de pedidos atualizados!")
    else:
        print(f"\n✅ RESULTADO: Todos os status já estavam corretos!")
    
    print("\n📈 ESTATÍSTICAS DE STATUS:")
    for status, count in status_count.items():
        print(f"   • {status}: {count} pedidos")
    
    return atualizados

def verificar_nfs_nao_sincronizadas():
    """
    3. Verifica NFs que deveriam estar preenchidas nos pedidos mas não estão
    """
    print("\n" + "="*60)
    print("3️⃣ VERIFICANDO NFs NÃO SINCRONIZADAS")
    print("="*60)
    
    # Buscar itens de embarque ativos com NF preenchida
    itens_com_nf = EmbarqueItem.query.join(Embarque).filter(
        EmbarqueItem.nota_fiscal.isnot(None),
        EmbarqueItem.nota_fiscal != '',
        EmbarqueItem.status == 'ativo',
        Embarque.status == 'ativo'
    ).all()
    
    print(f"📊 Encontrados {len(itens_com_nf)} itens de embarque com NF preenchida")
    
    nfs_corrigidas = 0
    problemas_encontrados = []
    
    for item in itens_com_nf:
        pedido = None
        
        # Buscar pedido correspondente
        if item.separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
        
        if not pedido and item.pedido:
            pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
        
        if not pedido:
            problemas_encontrados.append(f"Pedido {item.pedido} (lote: {item.separacao_lote_id}) não encontrado")
            continue
        
        # Verificar se a NF do pedido está sincronizada
        if not pedido.nf or pedido.nf != item.nota_fiscal:
            nf_anterior = pedido.nf
            pedido.nf = item.nota_fiscal
            nfs_corrigidas += 1
            
            print(f"   🔧 Pedido {pedido.num_pedido}: NF corrigida '{nf_anterior or 'None'}' → '{item.nota_fiscal}'")
            
            # Para pedidos FOB, garantir que tenham cotacao_id
            if pedido.transportadora == "FOB - COLETA" and not pedido.cotacao_id:
                transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
                if transportadora_fob:
                    cotacao_fob = Cotacao.query.filter_by(
                        transportadora_id=transportadora_fob.id,
                        tipo_carga='FOB'
                    ).first()
                    if cotacao_fob:
                        pedido.cotacao_id = cotacao_fob.id
                        print(f"      📋 Cotação FOB também corrigida: {cotacao_fob.id}")
    
    if nfs_corrigidas > 0:
        db.session.commit()
        print(f"\n🎉 RESULTADO: {nfs_corrigidas} NFs sincronizadas com os pedidos!")
    else:
        print(f"\n✅ RESULTADO: Todas as NFs já estavam sincronizadas!")
    
    if problemas_encontrados:
        print(f"\n⚠️ PROBLEMAS ENCONTRADOS ({len(problemas_encontrados)}):")
        for problema in problemas_encontrados[:5]:  # Mostra apenas os 5 primeiros
            print(f"   • {problema}")
        if len(problemas_encontrados) > 5:
            print(f"   • ... e mais {len(problemas_encontrados) - 5} problemas")
    
    return nfs_corrigidas, len(problemas_encontrados)

def verificar_status_apos_correcoes():
    """
    Verificação final: mostra estatísticas dos pedidos após todas as correções
    """
    print("\n" + "="*60)
    print("📊 VERIFICAÇÃO FINAL - ESTATÍSTICAS ATUALIZADAS")
    print("="*60)
    
    # Estatísticas gerais
    total_pedidos = Pedido.query.count()
    pedidos_fob = Pedido.query.filter_by(transportadora="FOB - COLETA").count()
    pedidos_com_nf = Pedido.query.filter(Pedido.nf.isnot(None), Pedido.nf != '').count()
    pedidos_com_cotacao = Pedido.query.filter(Pedido.cotacao_id.isnot(None)).count()
    
    print(f"📈 ESTATÍSTICAS GERAIS:")
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
        print(f"   • {status}: {count} pedidos")
    
    # Pedidos FOB específicos
    if pedidos_fob > 0:
        pedidos_fob_sem_cotacao = Pedido.query.filter(
            Pedido.transportadora == "FOB - COLETA",
            Pedido.cotacao_id.is_(None)
        ).count()
        
        print(f"\n🚛 PEDIDOS FOB:")
        print(f"   • Total FOB: {pedidos_fob}")
        print(f"   • FOB sem cotação: {pedidos_fob_sem_cotacao}")
        print(f"   • FOB com cotação: {pedidos_fob - pedidos_fob_sem_cotacao}")

def main():
    """Função principal que executa todas as operações de manutenção"""
    
    print("🔧 SCRIPT DE MANUTENÇÃO COMPLETO DO SISTEMA DE PEDIDOS")
    print("=" * 70)
    print("Este script irá:")
    print("1️⃣ Criar cotações para pedidos FOB sem cotacao_id")
    print("2️⃣ Atualizar status de todos os pedidos")
    print("3️⃣ Sincronizar NFs que faltam nos pedidos")
    print("=" * 70)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Operação 1: Criar cotações FOB
            fob_atualizados = criar_cotacoes_fob()
            
            # Operação 2: Atualizar status
            status_atualizados = atualizar_status_todos_pedidos()
            
            # Operação 3: Verificar NFs
            nfs_corrigidas, problemas = verificar_nfs_nao_sincronizadas()
            
            # Verificação final
            verificar_status_apos_correcoes()
            
            # Resumo final
            print("\n" + "="*60)
            print("🎉 RESUMO FINAL DA MANUTENÇÃO")
            print("="*60)
            print(f"✅ Pedidos FOB com cotação criada: {fob_atualizados}")
            print(f"✅ Status de pedidos atualizados: {status_atualizados}")
            print(f"✅ NFs sincronizadas: {nfs_corrigidas}")
            if problemas > 0:
                print(f"⚠️ Problemas que precisam atenção: {problemas}")
            print("\n🚀 Manutenção concluída com sucesso!")
            
        except Exception as e:
            print(f"\n❌ ERRO durante a manutenção: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    main() 