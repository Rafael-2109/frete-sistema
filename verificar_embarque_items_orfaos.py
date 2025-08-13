#!/usr/bin/env python3
"""
Script para verificar e corrigir EmbarqueItems órfãos
======================================================

Identifica EmbarqueItems que deveriam ter NF mas não têm,
e tenta vincular com as NFs correspondentes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import EmbarqueItem, Embarque
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.separacao.models import Separacao
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verificar_embarque_items_orfaos():
    """
    Verifica EmbarqueItems sem NF que deveriam ter
    """
    app = create_app()
    with app.app_context():
        logger.info("=" * 60)
        logger.info("🔍 VERIFICAÇÃO DE EMBARQUEITEMS ÓRFÃOS")
        logger.info("=" * 60)
        
        # 1. Buscar EmbarqueItems ativos sem NF
        items_sem_nf = EmbarqueItem.query.join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            Embarque.status == 'ativo',
            EmbarqueItem.status == 'ativo',
            db.or_(
                EmbarqueItem.nota_fiscal.is_(None),
                EmbarqueItem.nota_fiscal == ''
            )
        ).all()
        
        logger.info(f"📊 Total de EmbarqueItems ativos sem NF: {len(items_sem_nf)}")
        
        if not items_sem_nf:
            logger.info("✅ Nenhum EmbarqueItem órfão encontrado!")
            return
        
        # 2. Analisar cada item
        orfaos_verdadeiros = []
        com_erro_validacao = []
        possiveis_vinculos = []
        
        for item in items_sem_nf:
            # Verificar se tem erro de validação
            if item.erro_validacao:
                com_erro_validacao.append({
                    'id': item.id,
                    'pedido': item.pedido,
                    'lote': item.separacao_lote_id,
                    'erro': item.erro_validacao
                })
                continue
            
            # Buscar NF correspondente ao pedido
            nf_correspondente = RelatorioFaturamentoImportado.query.filter_by(
                origem=item.pedido,
                ativo=True
            ).first()
            
            if nf_correspondente:
                # Verificar se NF já está vinculada a outro EmbarqueItem
                outro_item = EmbarqueItem.query.filter_by(
                    nota_fiscal=nf_correspondente.numero_nf
                ).first()
                
                if not outro_item:
                    possiveis_vinculos.append({
                        'item_id': item.id,
                        'pedido': item.pedido,
                        'lote': item.separacao_lote_id,
                        'nf_numero': nf_correspondente.numero_nf,
                        'nf_data': nf_correspondente.data_fatura
                    })
                else:
                    logger.warning(f"⚠️ NF {nf_correspondente.numero_nf} já vinculada ao EmbarqueItem {outro_item.id}")
            else:
                orfaos_verdadeiros.append({
                    'id': item.id,
                    'pedido': item.pedido,
                    'lote': item.separacao_lote_id,
                    'cliente': item.cliente
                })
        
        # 3. Relatório
        logger.info("\n" + "=" * 60)
        logger.info("📋 RELATÓRIO DE ANÁLISE")
        logger.info("=" * 60)
        
        if com_erro_validacao:
            logger.info(f"\n❌ {len(com_erro_validacao)} items com erro de validação:")
            for item in com_erro_validacao[:10]:  # Mostrar até 10
                logger.info(f"   ID {item['id']}: Pedido {item['pedido']} - Erro: {item['erro']}")
        
        if orfaos_verdadeiros:
            logger.info(f"\n🔴 {len(orfaos_verdadeiros)} items órfãos verdadeiros (sem NF correspondente):")
            for item in orfaos_verdadeiros[:10]:  # Mostrar até 10
                logger.info(f"   ID {item['id']}: Pedido {item['pedido']} - Cliente: {item['cliente']}")
        
        if possiveis_vinculos:
            logger.info(f"\n🟡 {len(possiveis_vinculos)} items com possível vínculo:")
            for item in possiveis_vinculos[:10]:  # Mostrar até 10
                logger.info(f"   ID {item['item_id']}: Pedido {item['pedido']} -> NF {item['nf_numero']}")
        
        # 4. Perguntar se deseja corrigir
        if possiveis_vinculos:
            logger.info("\n" + "=" * 60)
            resposta = input(f"❓ Deseja vincular as {len(possiveis_vinculos)} NFs encontradas? (s/n): ")
            
            if resposta.lower() == 's':
                corrigidos = 0
                erros = 0
                
                for vinculo in possiveis_vinculos:
                    try:
                        item = EmbarqueItem.query.get(vinculo['item_id'])
                        if item:
                            item.nota_fiscal = vinculo['nf_numero']
                            
                            # Limpar erro de validação se for relacionado a NF
                            if item.erro_validacao in ['NF_PENDENTE_FATURAMENTO', 'NF_DIVERGENTE']:
                                item.erro_validacao = None
                            
                            db.session.commit()
                            corrigidos += 1
                            logger.info(f"✅ Vinculado: EmbarqueItem {item.id} -> NF {vinculo['nf_numero']}")
                    except Exception as e:
                        erros += 1
                        logger.error(f"❌ Erro ao vincular EmbarqueItem {vinculo['item_id']}: {e}")
                        db.session.rollback()
                
                logger.info(f"\n📊 Resultado: {corrigidos} vinculados, {erros} erros")
        
        # 5. Verificar EmbarqueItems com NF mas sem MovimentacaoEstoque
        logger.info("\n" + "=" * 60)
        logger.info("🔍 VERIFICANDO EMBARQUEITEMS COM NF MAS SEM MOVIMENTAÇÃO")
        logger.info("=" * 60)
        
        from app.estoque.models import MovimentacaoEstoque
        
        items_com_nf = EmbarqueItem.query.join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            Embarque.status == 'ativo',
            EmbarqueItem.status == 'ativo',
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != ''
        ).all()
        
        sem_movimentacao = []
        
        for item in items_com_nf:
            # Verificar se existe movimentação para esta NF
            mov = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.like(f"%NF {item.nota_fiscal}%")
            ).first()
            
            if not mov:
                sem_movimentacao.append({
                    'id': item.id,
                    'pedido': item.pedido,
                    'nf': item.nota_fiscal,
                    'lote': item.separacao_lote_id
                })
        
        if sem_movimentacao:
            logger.info(f"⚠️ {len(sem_movimentacao)} EmbarqueItems com NF mas sem MovimentacaoEstoque:")
            for item in sem_movimentacao[:10]:
                logger.info(f"   ID {item['id']}: NF {item['nf']} - Pedido {item['pedido']}")
            
            logger.info(f"\n💡 Execute o processamento de faturamento para criar as movimentações faltantes")
        else:
            logger.info("✅ Todos os EmbarqueItems com NF possuem MovimentacaoEstoque!")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ VERIFICAÇÃO CONCLUÍDA")
        logger.info("=" * 60)

if __name__ == "__main__":
    verificar_embarque_items_orfaos()