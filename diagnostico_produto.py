#!/usr/bin/env python3
"""
Script de diagnóstico completo para o produto 4320162
Verifica consistência entre Separações, PreSeparações e Movimentações de Estoque

Uso:
    python diagnostico_produto_4320162.py [codigo_produto]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem, CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from decimal import Decimal
from datetime import date, datetime, timedelta
from collections import defaultdict
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analisar_produto(cod_produto='4320162'):
    """
    Análise completa do produto
    """
    logger.info("\n" + "="*80)
    logger.info(f"DIAGNÓSTICO COMPLETO DO PRODUTO {cod_produto}")
    logger.info("="*80)
    
    # 1. VERIFICAR CÓDIGOS UNIFICADOS
    logger.info("\n1. CÓDIGOS UNIFICADOS:")
    logger.info("-" * 40)
    codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
    logger.info(f"Códigos relacionados: {codigos_unificados}")
    
    # 2. ESTOQUE TEMPO REAL
    logger.info("\n2. ESTOQUE TEMPO REAL:")
    logger.info("-" * 40)
    estoque_real = EstoqueTempoReal.query.filter_by(cod_produto=cod_produto).first()
    if estoque_real:
        logger.info(f"Saldo atual: {estoque_real.saldo_atual}")
        logger.info(f"Menor estoque D7: {estoque_real.menor_estoque_d7}")
        logger.info(f"Atualizado em: {estoque_real.atualizado_em}")
    else:
        logger.warning("❌ Produto não encontrado em EstoqueTempoReal")
    
    # 3. MOVIMENTAÇÃO ESTOQUE (HISTÓRICO)
    logger.info("\n3. MOVIMENTAÇÃO ESTOQUE (Histórico):")
    logger.info("-" * 40)
    total_mov_estoque = Decimal('0')
    for codigo in codigos_unificados:
        movs = MovimentacaoEstoque.query.filter_by(
            cod_produto=codigo,
            ativo=True
        ).all()
        
        for mov in movs:
            total_mov_estoque += Decimal(str(mov.qtd_movimentacao))
            logger.debug(f"  {codigo}: {mov.tipo_movimentacao} = {mov.qtd_movimentacao} ({mov.data_movimentacao})")
    
    logger.info(f"Total MovimentacaoEstoque: {total_mov_estoque}")
    
    # 4. SEPARAÇÕES COM STATUS ABERTO E COTADO
    logger.info("\n4. SEPARAÇÕES (Status ABERTO e COTADO):")
    logger.info("-" * 40)
    
    # Buscar pedidos com status ABERTO ou COTADO
    pedidos_abertos = Pedido.query.filter(
        Pedido.status.in_(['ABERTO', 'COTADO'])
    ).all()
    
    lotes_ids = [p.separacao_lote_id for p in pedidos_abertos if p.separacao_lote_id]
    
    # Buscar separações desses lotes
    total_separacoes = Decimal('0')
    separacoes_por_data = defaultdict(Decimal)
    
    for codigo in codigos_unificados:
        seps = Separacao.query.filter(
            Separacao.cod_produto == codigo,
            Separacao.separacao_lote_id.in_(lotes_ids) if lotes_ids else False
        ).all()
        
        for sep in seps:
            qtd = Decimal(str(sep.qtd_saldo or 0))
            total_separacoes += qtd
            if sep.expedicao:
                separacoes_por_data[sep.expedicao] += qtd
            logger.info(f"  Lote: {sep.separacao_lote_id} | Pedido: {sep.num_pedido} | "
                       f"Qtd: {qtd} | Expedição: {sep.expedicao}")
    
    logger.info(f"Total Separações (ABERTO/COTADO): {total_separacoes}")
    
    # 5. PRÉ-SEPARAÇÕES
    logger.info("\n5. PRÉ-SEPARAÇÕES:")
    logger.info("-" * 40)
    
    total_pre_separacoes = Decimal('0')
    pre_separacoes_por_data = defaultdict(Decimal)
    
    for codigo in codigos_unificados:
        pre_seps = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.cod_produto == codigo,
            PreSeparacaoItem.recomposto == False  # Apenas não recompostas
        ).all()
        
        for pre_sep in pre_seps:
            qtd = Decimal(str(pre_sep.qtd_selecionada_usuario or 0))
            total_pre_separacoes += qtd
            if pre_sep.data_expedicao_editada:
                pre_separacoes_por_data[pre_sep.data_expedicao_editada] += qtd
            logger.info(f"  Lote: {pre_sep.separacao_lote_id} | Pedido: {pre_sep.num_pedido} | "
                       f"Qtd: {qtd} | Expedição: {pre_sep.data_expedicao_editada} | "
                       f"Recomposto: {pre_sep.recomposto}")
    
    logger.info(f"Total Pré-Separações (não recompostas): {total_pre_separacoes}")
    
    # 6. CARTEIRA DE PEDIDOS
    logger.info("\n6. CARTEIRA DE PEDIDOS:")
    logger.info("-" * 40)
    
    total_carteira = Decimal('0')
    for codigo in codigos_unificados:
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == codigo,
            CarteiraPrincipal.ativo == True
        ).all()
        
        for item in itens:
            qtd = Decimal(str(item.qtd_saldo_produto_pedido or 0))
            total_carteira += qtd
    
    logger.info(f"Total Carteira (qtd_saldo): {total_carteira}")
    
    # 7. MOVIMENTAÇÃO PREVISTA
    logger.info("\n7. MOVIMENTAÇÃO PREVISTA (Próximos 28 dias):")
    logger.info("-" * 40)
    
    hoje = date.today()
    total_saidas_previstas = Decimal('0')
    total_entradas_previstas = Decimal('0')
    
    for i in range(28):
        data_check = hoje + timedelta(days=i)
        saida_dia = Decimal('0')
        entrada_dia = Decimal('0')
        
        for codigo in codigos_unificados:
            mov_prev = MovimentacaoPrevista.query.filter_by(
                cod_produto=codigo,
                data_prevista=data_check
            ).first()
            
            if mov_prev:
                saida_dia += Decimal(str(mov_prev.saida_prevista or 0))
                entrada_dia += Decimal(str(mov_prev.entrada_prevista or 0))
        
        if saida_dia > 0 or entrada_dia > 0:
            logger.info(f"  D+{i} ({data_check}): Entrada={entrada_dia}, Saída={saida_dia}")
            total_saidas_previstas += saida_dia
            total_entradas_previstas += entrada_dia
    
    logger.info(f"Total Entradas Previstas: {total_entradas_previstas}")
    logger.info(f"Total Saídas Previstas: {total_saidas_previstas}")
    
    # 8. ANÁLISE DE CONSISTÊNCIA
    logger.info("\n" + "="*80)
    logger.info("ANÁLISE DE CONSISTÊNCIA:")
    logger.info("="*80)
    
    # Comparar estoque calculado vs EstoqueTempoReal
    logger.info("\n📊 ESTOQUE ATUAL:")
    logger.info(f"  MovimentacaoEstoque (calculado): {total_mov_estoque}")
    logger.info(f"  EstoqueTempoReal (registrado): {estoque_real.saldo_atual if estoque_real else 'N/A'}")
    
    if estoque_real:
        diff_estoque = abs(total_mov_estoque - estoque_real.saldo_atual)
        if diff_estoque < Decimal('0.001'):
            logger.info("  ✅ Estoque consistente")
        else:
            logger.error(f"  ❌ DIFERENÇA: {diff_estoque}")
    
    # Comparar saídas futuras
    logger.info("\n📅 SAÍDAS FUTURAS:")
    logger.info(f"  Separações (ABERTO/COTADO): {total_separacoes}")
    logger.info(f"  Pré-Separações (não recompostas): {total_pre_separacoes}")
    logger.info(f"  Carteira (qtd_saldo): {total_carteira}")
    logger.info(f"  MovimentacaoPrevista (saídas): {total_saidas_previstas}")
    
    # Verificar duplicação
    saidas_esperadas = total_separacoes + total_pre_separacoes
    logger.info(f"\n🔍 VERIFICAÇÃO DE DUPLICAÇÃO:")
    logger.info(f"  Saídas esperadas (Sep + PreSep): {saidas_esperadas}")
    logger.info(f"  Saídas registradas (MovPrevista): {total_saidas_previstas}")
    
    if abs(saidas_esperadas - total_saidas_previstas) < Decimal('0.001'):
        logger.info("  ✅ Sem duplicação detectada")
    elif total_saidas_previstas > saidas_esperadas:
        excesso = total_saidas_previstas - saidas_esperadas
        logger.error(f"  ❌ POSSÍVEL DUPLICAÇÃO: {excesso} unidades a mais")
    else:
        falta = saidas_esperadas - total_saidas_previstas
        logger.warning(f"  ⚠️ FALTANDO: {falta} unidades não registradas")
    
    # Detalhe por data
    logger.info("\n📆 DETALHAMENTO POR DATA DE EXPEDIÇÃO:")
    todas_datas = set(separacoes_por_data.keys()) | set(pre_separacoes_por_data.keys())
    
    for data_exp in sorted(todas_datas):
        sep_qtd = separacoes_por_data.get(data_exp, Decimal('0'))
        pre_qtd = pre_separacoes_por_data.get(data_exp, Decimal('0'))
        
        # Buscar MovimentacaoPrevista para esta data
        mov_prev_qtd = Decimal('0')
        for codigo in codigos_unificados:
            mov_prev = MovimentacaoPrevista.query.filter_by(
                cod_produto=codigo,
                data_prevista=data_exp
            ).first()
            if mov_prev:
                mov_prev_qtd += Decimal(str(mov_prev.saida_prevista or 0))
        
        logger.info(f"\n  Data: {data_exp}")
        logger.info(f"    Separações: {sep_qtd}")
        logger.info(f"    Pré-Separações: {pre_qtd}")
        logger.info(f"    Total esperado: {sep_qtd + pre_qtd}")
        logger.info(f"    MovPrevista: {mov_prev_qtd}")
        
        diff = mov_prev_qtd - (sep_qtd + pre_qtd)
        if abs(diff) < Decimal('0.001'):
            logger.info(f"    ✅ OK")
        elif diff > 0:
            logger.error(f"    ❌ EXCESSO: {diff}")
        else:
            logger.warning(f"    ⚠️ FALTA: {abs(diff)}")
    
    # 9. VERIFICAR LOTES DUPLICADOS
    logger.info("\n🔍 VERIFICAÇÃO DE LOTES:")
    logger.info("-" * 40)
    
    # Verificar se há lotes que aparecem em PreSeparacao e Separacao
    lotes_pre = set()
    lotes_sep = set()
    
    for codigo in codigos_unificados:
        pre_seps = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.cod_produto == codigo
        ).all()
        for ps in pre_seps:
            if ps.separacao_lote_id:
                lotes_pre.add(ps.separacao_lote_id)
        
        seps = Separacao.query.filter(
            Separacao.cod_produto == codigo
        ).all()
        for s in seps:
            if s.separacao_lote_id:
                lotes_sep.add(s.separacao_lote_id)
    
    lotes_comuns = lotes_pre & lotes_sep
    if lotes_comuns:
        logger.warning(f"Lotes que aparecem em PreSeparacao E Separacao: {lotes_comuns}")
        for lote in lotes_comuns:
            # Verificar detalhes
            pre_qtd = Decimal('0')
            sep_qtd = Decimal('0')
            
            for codigo in codigos_unificados:
                pre = PreSeparacaoItem.query.filter_by(
                    cod_produto=codigo,
                    separacao_lote_id=lote
                ).all()
                for p in pre:
                    pre_qtd += Decimal(str(p.qtd_selecionada_usuario or 0))
                
                sep = Separacao.query.filter_by(
                    cod_produto=codigo,
                    separacao_lote_id=lote
                ).all()
                for s in sep:
                    sep_qtd += Decimal(str(s.qtd_saldo or 0))
            
            logger.info(f"  Lote {lote}:")
            logger.info(f"    PreSeparacao: {pre_qtd}")
            logger.info(f"    Separacao: {sep_qtd}")
            
            # Verificar se PreSeparacao está recomposta
            pre_recomp = PreSeparacaoItem.query.filter_by(
                separacao_lote_id=lote
            ).first()
            if pre_recomp:
                logger.info(f"    Recomposto: {pre_recomp.recomposto}")
    else:
        logger.info("✅ Nenhum lote duplicado entre PreSeparacao e Separacao")
    
    return {
        'estoque_atual': total_mov_estoque,
        'estoque_tempo_real': estoque_real.saldo_atual if estoque_real else None,
        'separacoes': total_separacoes,
        'pre_separacoes': total_pre_separacoes,
        'carteira': total_carteira,
        'mov_prevista': total_saidas_previstas
    }


def main():
    """
    Executa o diagnóstico
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Permitir passar código como argumento
            cod_produto = sys.argv[1] if len(sys.argv) > 1 else '4320162'
            resultado = analisar_produto(cod_produto)
            
            logger.info("\n" + "="*80)
            logger.info("RESUMO FINAL:")
            logger.info("="*80)
            
            for chave, valor in resultado.items():
                logger.info(f"{chave}: {valor}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Erro durante análise: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())