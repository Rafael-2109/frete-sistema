#!/usr/bin/env python3
"""
Script para Corrigir Status de Pedidos baseado em EmbarqueItems
================================================================

Este script corrige o status dos pedidos analisando:
1. EmbarqueItems ativos com Embarques ativos -> Sincroniza NF e status
2. EmbarqueItems inativos/cancelados -> Marca como NF no CD se houver NF
3. Garante que cotacao_id seja preenchido quando necessário

Autor: Sistema de Fretes
Data: 2025-08-06
"""

import logging
from datetime import datetime
from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem, Embarque
from app.monitoramento.models import EntregaMonitorada

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def corrigir_status_pedidos():
    """
    Corrige o status dos pedidos baseado em EmbarqueItems e Embarques
    """
    
    app = create_app()
    with app.app_context():
        logger.info("🚀 Iniciando correção de status de pedidos...")
        
        # Estatísticas
        total_pedidos = Pedido.query.count()
        pedidos_corrigidos = 0
        pedidos_faturados = 0
        pedidos_cotados = 0
        pedidos_nf_cd = 0
        pedidos_com_erro = 0
        
        logger.info(f"📊 Total de pedidos no sistema: {total_pedidos}")
        
        # Buscar todos os pedidos com separacao_lote_id
        pedidos = Pedido.query.filter(
            Pedido.separacao_lote_id.isnot(None)
        ).all()
        
        logger.info(f"🔍 Analisando {len(pedidos)} pedidos com lote de separação...")
        
        for i, pedido in enumerate(pedidos, 1):
            try:
                if i % 100 == 0:
                    logger.info(f"   Processando {i}/{len(pedidos)}...")
                
                status_original = pedido.status
                nf_original = pedido.nf
                nf_cd_original = pedido.nf_cd
                cotacao_original = pedido.cotacao_id
                
                # Buscar EmbarqueItems do pedido
                items_embarque = EmbarqueItem.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).all()
                
                if not items_embarque:
                    # Sem EmbarqueItems, não fazer nada
                    continue
                
                # Separar items ativos e inativos
                items_ativos = []
                items_inativos = []
                
                for item in items_embarque:
                    embarque = Embarque.query.get(item.embarque_id)
                    
                    if item.status == 'ativo' and embarque and embarque.status == 'ativo':
                        items_ativos.append(item)
                    else:
                        items_inativos.append(item)
                
                # CENÁRIO 1: Tem EmbarqueItem ATIVO com Embarque ATIVO
                if items_ativos:
                    # Pegar o item ativo mais recente com NF
                    item_com_nf = None
                    for item in items_ativos:
                        if item.nota_fiscal and item.nota_fiscal.strip():
                            item_com_nf = item
                            break
                    
                    if item_com_nf:
                        # TEM NF - Status será FATURADO
                        if pedido.nf != item_com_nf.nota_fiscal:
                            pedido.nf = item_com_nf.nota_fiscal
                            logger.debug(f"✅ Pedido {pedido.num_pedido}: NF atualizada para {item_com_nf.nota_fiscal}")
                        
                        # Limpar nf_cd se estava marcado
                        if pedido.nf_cd:
                            pedido.nf_cd = False
                        
                        pedidos_faturados += 1
                        
                    else:
                        # SEM NF mas tem embarque ativo - Status será COTADO ou EMBARCADO
                        # Garantir que tem cotacao_id
                        if not pedido.cotacao_id:
                            # Buscar cotacao do embarque ou item
                            for item in items_ativos:
                                if item.cotacao_id:
                                    pedido.cotacao_id = item.cotacao_id
                                    break
                                else:
                                    embarque = Embarque.query.get(item.embarque_id)
                                    if embarque and embarque.cotacao_id:
                                        pedido.cotacao_id = embarque.cotacao_id
                                        break
                            
                            if pedido.cotacao_id:
                                logger.debug(f"✅ Pedido {pedido.num_pedido}: cotacao_id definido como {pedido.cotacao_id}")
                        
                        # Limpar NF se tinha mas não deveria ter
                        if pedido.nf:
                            pedido.nf = None
                        
                        # Limpar nf_cd
                        if pedido.nf_cd:
                            pedido.nf_cd = False
                        
                        pedidos_cotados += 1
                
                # CENÁRIO 2: Só tem EmbarqueItem INATIVO/CANCELADO mas tem NF
                elif items_inativos:
                    # Verificar se algum item inativo tem NF
                    tem_nf = False
                    nf_item = None
                    
                    for item in items_inativos:
                        if item.nota_fiscal and item.nota_fiscal.strip():
                            tem_nf = True
                            nf_item = item.nota_fiscal
                            break
                    
                    if tem_nf:
                        # Marcar como NF no CD
                        if pedido.nf != nf_item:
                            pedido.nf = nf_item
                        
                        if not pedido.nf_cd:
                            pedido.nf_cd = True
                            logger.debug(f"📦 Pedido {pedido.num_pedido}: NF {nf_item} marcada como no CD")
                        
                        pedidos_nf_cd += 1
                    else:
                        # Sem NF e sem embarques ativos - limpar tudo
                        if pedido.nf:
                            pedido.nf = None
                        if pedido.nf_cd:
                            pedido.nf_cd = False
                        if pedido.cotacao_id:
                            pedido.cotacao_id = None
                
                # Verificar se houve mudança
                if (pedido.status != status_original or 
                    pedido.nf != nf_original or 
                    pedido.nf_cd != nf_cd_original or
                    pedido.cotacao_id != cotacao_original):
                    
                    pedidos_corrigidos += 1
                    logger.debug(f"🔄 Pedido {pedido.num_pedido}: Status {status_original} → {pedido.status_calculado}")
                
            except Exception as e:
                pedidos_com_erro += 1
                logger.error(f"❌ Erro ao processar pedido {pedido.num_pedido}: {e}")
        
        # Commit das alterações
        if pedidos_corrigidos > 0:
            logger.info("💾 Salvando alterações no banco...")
            db.session.commit()
        
        # Relatório final
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO FINAL:")
        logger.info(f"Total de pedidos analisados: {len(pedidos)}")
        logger.info(f"✅ Pedidos corrigidos: {pedidos_corrigidos}")
        logger.info(f"   📄 Marcados como FATURADO: {pedidos_faturados}")
        logger.info(f"   🚛 Marcados como COTADO/EMBARCADO: {pedidos_cotados}")
        logger.info(f"   📦 Marcados como NF no CD: {pedidos_nf_cd}")
        logger.info(f"❌ Erros: {pedidos_com_erro}")
        logger.info("=" * 60)
        
        # Verificar pedidos problemáticos após correção
        logger.info("\n🔍 Verificando pedidos problemáticos após correção...")
        
        # Pedidos ABERTO com EmbarqueItem ativo
        problemas = db.session.query(Pedido).join(
            EmbarqueItem,
            Pedido.separacao_lote_id == EmbarqueItem.separacao_lote_id
        ).join(
            Embarque,
            EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            Pedido.status == 'ABERTO',
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo'
        ).count()
        
        if problemas > 0:
            logger.warning(f"⚠️ Ainda existem {problemas} pedidos com status ABERTO mas com embarque ativo")
            
            # Mostrar alguns exemplos
            exemplos = db.session.query(Pedido).join(
                EmbarqueItem,
                Pedido.separacao_lote_id == EmbarqueItem.separacao_lote_id
            ).join(
                Embarque,
                EmbarqueItem.embarque_id == Embarque.id
            ).filter(
                Pedido.status == 'ABERTO',
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).limit(3).all()
            
            for p in exemplos:
                logger.warning(f"   Exemplo: {p.num_pedido} - Lote: {p.separacao_lote_id} - Cotação: {p.cotacao_id}")
        else:
            logger.info("✅ Nenhum pedido com status incorreto encontrado!")
        
        return pedidos_corrigidos

if __name__ == "__main__":
    try:
        logger.info("🚀 Executando correção de status de pedidos...")
        corrigidos = corrigir_status_pedidos()
        logger.info(f"✅ Processo concluído! {corrigidos} pedidos corrigidos.")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        exit(1)