#!/usr/bin/env python3
"""
Script para Corrigir separacao_lote_id em EntregasMonitoradas
===========================================================

Este script corrige retroativamente os 95% de EntregasMonitoradas
que não têm separacao_lote_id preenchido, causando problemas na
sincronização de status dos pedidos.

Autor: Sistema de Fretes
Data: 2025-08-06
"""

import logging
from datetime import datetime
from app import create_app, db
from app.monitoramento.models import EntregaMonitorada
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def corrigir_separacao_lote_id():
    """
    Corrige o campo separacao_lote_id em EntregasMonitoradas
    buscando o lote através da NF -> Pedido ou NF -> EmbarqueItem
    """
    
    app = create_app()
    with app.app_context():
        logger.info("🚀 Iniciando correção de separacao_lote_id...")
        
        # Estatísticas
        total_entregas = EntregaMonitorada.query.count()
        entregas_sem_lote = EntregaMonitorada.query.filter(
            EntregaMonitorada.separacao_lote_id.is_(None)
        ).count()
        
        logger.info(f"📊 Total de entregas: {total_entregas}")
        logger.info(f"📊 Entregas SEM lote: {entregas_sem_lote} ({entregas_sem_lote/total_entregas*100:.1f}%)")
        
        if entregas_sem_lote == 0:
            logger.info("✅ Nenhuma entrega precisa de correção!")
            return
        
        # Buscar todas as entregas sem lote
        entregas = EntregaMonitorada.query.filter(
            EntregaMonitorada.separacao_lote_id.is_(None)
        ).all()
        
        corrigidas = 0
        nao_encontradas = 0
        erros = 0
        
        logger.info(f"🔧 Processando {len(entregas)} entregas...")
        
        for i, entrega in enumerate(entregas, 1):
            try:
                if i % 100 == 0:
                    logger.info(f"   Processando {i}/{len(entregas)}...")
                
                # Estratégia 1: Buscar pelo Pedido via NF
                pedido = Pedido.query.filter_by(nf=entrega.numero_nf).first()
                
                if pedido and pedido.separacao_lote_id:
                    entrega.separacao_lote_id = pedido.separacao_lote_id
                    corrigidas += 1
                    logger.debug(f"✅ NF {entrega.numero_nf}: Lote {pedido.separacao_lote_id} (via Pedido)")
                    continue
                
                # Estratégia 2: Buscar pelo EmbarqueItem via NF
                item_embarque = EmbarqueItem.query.filter_by(
                    nota_fiscal=entrega.numero_nf,
                    status='ativo'
                ).first()
                
                if item_embarque and item_embarque.separacao_lote_id:
                    entrega.separacao_lote_id = item_embarque.separacao_lote_id
                    corrigidas += 1
                    logger.debug(f"✅ NF {entrega.numero_nf}: Lote {item_embarque.separacao_lote_id} (via EmbarqueItem)")
                    continue
                
                # Não encontrou lote
                nao_encontradas += 1
                logger.debug(f"⚠️ NF {entrega.numero_nf}: Lote não encontrado")
                
            except Exception as e:
                erros += 1
                logger.error(f"❌ Erro ao processar NF {entrega.numero_nf}: {e}")
        
        # Commit das alterações
        if corrigidas > 0:
            logger.info("💾 Salvando alterações no banco...")
            db.session.commit()
        
        # Relatório final
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO FINAL:")
        logger.info(f"✅ Corrigidas: {corrigidas} ({corrigidas/entregas_sem_lote*100:.1f}%)")
        logger.info(f"⚠️ Não encontradas: {nao_encontradas} ({nao_encontradas/entregas_sem_lote*100:.1f}%)")
        logger.info(f"❌ Erros: {erros}")
        logger.info("=" * 60)
        
        # Verificar resultado
        entregas_sem_lote_depois = EntregaMonitorada.query.filter(
            EntregaMonitorada.separacao_lote_id.is_(None)
        ).count()
        
        logger.info(f"📊 Entregas SEM lote DEPOIS: {entregas_sem_lote_depois} ({entregas_sem_lote_depois/total_entregas*100:.1f}%)")
        
        if entregas_sem_lote_depois < entregas_sem_lote:
            reducao = entregas_sem_lote - entregas_sem_lote_depois
            logger.info(f"🎉 Redução de {reducao} entregas sem lote ({reducao/entregas_sem_lote*100:.1f}% de melhoria)")
        
        return corrigidas

if __name__ == "__main__":
    try:
        logger.info("🚀 Executando correção de separacao_lote_id...")
        corrigidas = corrigir_separacao_lote_id()
        logger.info(f"✅ Processo concluído! {corrigidas} entregas corrigidas.")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        exit(1)