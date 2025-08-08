#!/usr/bin/env python3
"""
Script para corrigir movimentações duplicadas
Reconstrói MovimentacaoPrevista considerando apenas:
- PreSeparacaoItem com recomposto=False OU
- Separacao (quando não há PreSeparacaoItem correspondente)

Uso:
    python corrigir_movimentacoes_duplicadas.py [--produto CODIGO] [--dry-run]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.models import UnificacaoCodigos
from app.estoque.models_tempo_real import MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from decimal import Decimal
from datetime import date, datetime
from collections import defaultdict
import argparse
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reconstruir_movimentacoes_produto(cod_produto, dry_run=False):
    """
    Reconstrói MovimentacaoPrevista para um produto específico
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processando produto {cod_produto}")
    logger.info(f"{'='*60}")
    
    # Obter códigos unificados
    codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
    logger.info(f"Códigos relacionados: {codigos_unificados}")
    
    # Estrutura para acumular movimentações por data
    movimentacoes_por_data = defaultdict(lambda: {'entrada': Decimal('0'), 'saida': Decimal('0')})
    
    # 1. PROCESSAR PRÉ-SEPARAÇÕES (não recompostas)
    logger.info("\n1. Processando Pré-Separações (não recompostas)...")
    pre_sep_count = 0
    
    for codigo in codigos_unificados:
        pre_seps = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.cod_produto == codigo,
            PreSeparacaoItem.recomposto == False  # Apenas não recompostas
        ).all()
        
        for pre_sep in pre_seps:
            if pre_sep.data_expedicao_editada and pre_sep.qtd_selecionada_usuario:
                qtd = Decimal(str(pre_sep.qtd_selecionada_usuario))
                movimentacoes_por_data[pre_sep.data_expedicao_editada]['saida'] += qtd
                pre_sep_count += 1
                logger.debug(f"  PreSep {pre_sep.separacao_lote_id}: {qtd} em {pre_sep.data_expedicao_editada}")
    
    logger.info(f"  Total pré-separações processadas: {pre_sep_count}")
    
    # 2. PROCESSAR SEPARAÇÕES (apenas se não houver PreSeparação correspondente)
    logger.info("\n2. Processando Separações diretas...")
    
    # Buscar pedidos com status ABERTO ou COTADO
    pedidos_abertos = Pedido.query.filter(
        Pedido.status.in_(['ABERTO', 'COTADO'])
    ).all()
    
    lotes_com_pre_sep = set()
    sep_count = 0
    sep_ignoradas = 0
    
    # Identificar lotes que têm pré-separação
    for codigo in codigos_unificados:
        pre_seps = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.cod_produto == codigo
        ).all()
        for ps in pre_seps:
            if ps.separacao_lote_id:
                lotes_com_pre_sep.add(ps.separacao_lote_id)
    
    logger.info(f"  Lotes com pré-separação: {len(lotes_com_pre_sep)}")
    
    # Processar separações
    for pedido in pedidos_abertos:
        if not pedido.separacao_lote_id:
            continue
            
        for codigo in codigos_unificados:
            seps = Separacao.query.filter(
                Separacao.cod_produto == codigo,
                Separacao.separacao_lote_id == pedido.separacao_lote_id
            ).all()
            
            for sep in seps:
                # Ignorar se este lote tem pré-separação
                if sep.separacao_lote_id in lotes_com_pre_sep:
                    sep_ignoradas += 1
                    logger.debug(f"  Ignorando Sep {sep.separacao_lote_id} (tem pré-sep)")
                    continue
                
                if sep.expedicao and sep.qtd_saldo:
                    qtd = Decimal(str(sep.qtd_saldo))
                    movimentacoes_por_data[sep.expedicao]['saida'] += qtd
                    sep_count += 1
                    logger.debug(f"  Sep {sep.separacao_lote_id}: {qtd} em {sep.expedicao}")
    
    logger.info(f"  Total separações processadas: {sep_count}")
    logger.info(f"  Total separações ignoradas (têm pré-sep): {sep_ignoradas}")
    
    # 3. LIMPAR MOVIMENTAÇÕES ANTIGAS
    if not dry_run:
        logger.info("\n3. Limpando movimentações antigas...")
        for codigo in codigos_unificados:
            deleted = MovimentacaoPrevista.query.filter_by(
                cod_produto=codigo
            ).delete()
            logger.info(f"  Removidas {deleted} movimentações do código {codigo}")
    else:
        logger.info("\n3. [DRY-RUN] Movimentações antigas seriam limpas")
    
    # 4. CRIAR NOVAS MOVIMENTAÇÕES
    logger.info("\n4. Criando novas movimentações...")
    novas_movimentacoes = 0
    
    for data_mov, valores in movimentacoes_por_data.items():
        if valores['saida'] > 0 or valores['entrada'] > 0:
            logger.info(f"  {data_mov}: Entrada={valores['entrada']}, Saída={valores['saida']}")
            
            if not dry_run:
                # Criar para cada código unificado
                for codigo in codigos_unificados:
                    mov = MovimentacaoPrevista(
                        cod_produto=codigo,
                        data_prevista=data_mov,
                        entrada_prevista=valores['entrada'],
                        saida_prevista=valores['saida']
                    )
                    db.session.add(mov)
                    novas_movimentacoes += 1
    
    if not dry_run:
        db.session.commit()
        logger.info(f"\n✅ {novas_movimentacoes} movimentações criadas")
    else:
        logger.info(f"\n[DRY-RUN] {novas_movimentacoes} movimentações seriam criadas")
    
    return {
        'pre_separacoes': pre_sep_count,
        'separacoes': sep_count,
        'separacoes_ignoradas': sep_ignoradas,
        'movimentacoes_criadas': novas_movimentacoes
    }


def main():
    parser = argparse.ArgumentParser(
        description='Corrige movimentações duplicadas no estoque'
    )
    parser.add_argument(
        '--produto',
        help='Código do produto específico (se não informado, processa todos)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a correção sem fazer alterações'
    )
    
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        try:
            if args.dry_run:
                logger.info("🔍 MODO DRY-RUN - Nenhuma alteração será feita")
            
            if args.produto:
                # Processar produto específico
                resultado = reconstruir_movimentacoes_produto(
                    args.produto, 
                    dry_run=args.dry_run
                )
                
                logger.info("\n" + "="*60)
                logger.info("RESUMO DA CORREÇÃO:")
                logger.info("="*60)
                for chave, valor in resultado.items():
                    logger.info(f"{chave}: {valor}")
                
            else:
                # Processar todos os produtos com movimentação
                logger.info("Buscando produtos com movimentações...")
                
                # Buscar produtos únicos de PreSeparacao e Separacao
                produtos = set()
                
                # De pré-separações
                pre_seps = db.session.query(
                    PreSeparacaoItem.cod_produto
                ).filter(
                    PreSeparacaoItem.recomposto == False
                ).distinct().all()
                
                for (cod,) in pre_seps:
                    produtos.add(cod)
                
                # De separações ativas
                pedidos = Pedido.query.filter(
                    Pedido.status.in_(['ABERTO', 'COTADO'])
                ).all()
                
                lotes_ativos = [p.separacao_lote_id for p in pedidos if p.separacao_lote_id]
                
                if lotes_ativos:
                    seps = db.session.query(
                        Separacao.cod_produto
                    ).filter(
                        Separacao.separacao_lote_id.in_(lotes_ativos)
                    ).distinct().all()
                    
                    for (cod,) in seps:
                        produtos.add(cod)
                
                logger.info(f"Total de produtos para processar: {len(produtos)}")
                
                # Processar cada produto
                totais = defaultdict(int)
                
                for i, cod_produto in enumerate(produtos, 1):
                    logger.info(f"\n[{i}/{len(produtos)}] Processando {cod_produto}...")
                    resultado = reconstruir_movimentacoes_produto(
                        cod_produto,
                        dry_run=args.dry_run
                    )
                    
                    for chave, valor in resultado.items():
                        totais[chave] += valor
                
                # Resumo geral
                logger.info("\n" + "="*60)
                logger.info("RESUMO GERAL DA CORREÇÃO:")
                logger.info("="*60)
                logger.info(f"Produtos processados: {len(produtos)}")
                for chave, valor in totais.items():
                    logger.info(f"Total {chave}: {valor}")
            
            if args.dry_run:
                logger.info("\n⚠️ MODO DRY-RUN - Nenhuma alteração foi feita")
                logger.info("Execute sem --dry-run para aplicar as correções")
            else:
                logger.info("\n✅ Correções aplicadas com sucesso!")
            
            return 0
            
        except Exception as e:
            logger.error(f"Erro durante correção: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())