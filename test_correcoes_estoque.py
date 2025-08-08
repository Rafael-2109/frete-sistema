#!/usr/bin/env python3
"""
Script para testar as correções no sistema de estoque:
1. Estoque inicial considerando unificação de códigos
2. Exibição correta das saídas no cardex

Uso:
    python test_correcoes_estoque.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.models import UnificacaoCodigos, MovimentacaoEstoque
from app.carteira.models import PreSeparacaoItem
from decimal import Decimal
from datetime import date, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_unificacao_inicial():
    """
    Testa se o estoque inicial está considerando unificação de códigos
    """
    logger.info("\n" + "="*60)
    logger.info("TESTE 1: Estoque Inicial com Unificação de Códigos")
    logger.info("="*60)
    
    # Buscar um produto que tenha unificação
    unificacao = UnificacaoCodigos.query.filter_by(ativo=True).first()
    
    if not unificacao:
        logger.warning("Nenhuma unificação ativa encontrada para teste")
        return False
    
    cod_origem = str(unificacao.codigo_origem)
    cod_destino = str(unificacao.codigo_destino)
    
    logger.info(f"Testando unificação: {cod_origem} → {cod_destino}")
    
    # Recalcular estoque do código destino
    estoque = ServicoEstoqueTempoReal.recalcular_estoque_produto(cod_destino)
    
    # Calcular manualmente o saldo esperado
    saldo_esperado = Decimal('0')
    codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_destino)
    
    logger.info(f"Códigos relacionados: {codigos_relacionados}")
    
    for codigo in codigos_relacionados:
        movs = MovimentacaoEstoque.query.filter_by(
            cod_produto=codigo,
            ativo=True
        ).all()
        
        for mov in movs:
            saldo_esperado += Decimal(str(mov.qtd_movimentacao))
            logger.debug(f"  {codigo}: {mov.tipo_movimentacao} = {mov.qtd_movimentacao}")
    
    logger.info(f"Saldo calculado: {estoque.saldo_atual}")
    logger.info(f"Saldo esperado: {saldo_esperado}")
    
    if abs(estoque.saldo_atual - saldo_esperado) < Decimal('0.001'):
        logger.info("✅ TESTE 1 PASSOU: Estoque inicial considera unificação corretamente")
        return True
    else:
        logger.error(f"❌ TESTE 1 FALHOU: Diferença de {estoque.saldo_atual - saldo_esperado}")
        return False


def test_saidas_cardex():
    """
    Testa se as saídas estão aparecendo corretamente no cardex
    """
    logger.info("\n" + "="*60)
    logger.info("TESTE 2: Exibição de Saídas no Cardex")
    logger.info("="*60)
    
    # Buscar um produto com movimentação prevista
    mov_prevista = MovimentacaoPrevista.query.filter(
        MovimentacaoPrevista.saida_prevista > 0
    ).first()
    
    if not mov_prevista:
        logger.warning("Nenhuma movimentação prevista de saída encontrada")
        return False
    
    cod_produto = mov_prevista.cod_produto
    logger.info(f"Testando produto: {cod_produto}")
    logger.info(f"Data prevista: {mov_prevista.data_prevista}")
    logger.info(f"Saída prevista: {mov_prevista.saida_prevista}")
    
    # Obter projeção completa
    projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
    
    if not projecao:
        logger.error("Não foi possível obter projeção")
        return False
    
    # Verificar se a saída aparece na projeção
    teste_passou = False
    for dia in projecao['projecao']:
        if dia['data'] == mov_prevista.data_prevista.isoformat():
            logger.info(f"Dia encontrado: {dia['data']}")
            logger.info(f"  Saldo inicial: {dia['saldo_inicial']}")
            logger.info(f"  Entrada: {dia['entrada']}")
            logger.info(f"  Saída: {dia['saida']}")  # Campo correto
            logger.info(f"  Saldo final: {dia['saldo_final']}")
            
            if dia['saida'] >= float(mov_prevista.saida_prevista):
                logger.info("✅ TESTE 2 PASSOU: Saída aparece corretamente na projeção")
                teste_passou = True
            else:
                logger.error(f"❌ Saída incorreta: esperado >= {mov_prevista.saida_prevista}, obtido {dia['saida']}")
            break
    
    if not teste_passou:
        logger.error("❌ TESTE 2 FALHOU: Dia com saída não encontrado na projeção")
        
    return teste_passou


def test_pre_separacao_trigger():
    """
    Testa se criação de pré-separação atualiza movimentação prevista
    """
    logger.info("\n" + "="*60)
    logger.info("TESTE 3: Trigger de Pré-Separação")
    logger.info("="*60)
    
    # Buscar um produto qualquer
    produto = EstoqueTempoReal.query.first()
    
    if not produto:
        logger.warning("Nenhum produto encontrado para teste")
        return False
    
    cod_produto = produto.cod_produto
    data_expedicao = date.today() + timedelta(days=3)
    qtd_teste = Decimal('10')
    
    logger.info(f"Testando produto: {cod_produto}")
    logger.info(f"Data expedição: {data_expedicao}")
    logger.info(f"Quantidade: {qtd_teste}")
    
    # Verificar movimentação prevista antes
    mov_antes = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_antes = Decimal(str(mov_antes.saida_prevista)) if mov_antes else Decimal('0')
    logger.info(f"Saída antes: {saida_antes}")
    
    # Criar pré-separação de teste
    pre_sep = PreSeparacaoItem(
        separacao_lote_id=f"TEST_{date.today().isoformat()}",
        num_pedido="TEST_001",
        cod_produto=cod_produto,
        cnpj_cliente="00000000000000",
        nome_produto=f"Produto {cod_produto}",
        qtd_original_carteira=qtd_teste,
        qtd_selecionada_usuario=qtd_teste,
        qtd_restante_calculada=Decimal('0'),
        data_expedicao_editada=data_expedicao,
        recomposto=False,
        status='CRIADO'
    )
    
    db.session.add(pre_sep)
    db.session.commit()
    
    # Verificar movimentação prevista depois
    mov_depois = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_depois = Decimal(str(mov_depois.saida_prevista)) if mov_depois else Decimal('0')
    logger.info(f"Saída depois: {saida_depois}")
    
    diferenca = saida_depois - saida_antes
    logger.info(f"Diferença: {diferenca}")
    
    # Limpar teste
    db.session.delete(pre_sep)
    db.session.commit()
    
    if abs(diferenca - qtd_teste) < Decimal('0.001'):
        logger.info("✅ TESTE 3 PASSOU: Trigger atualiza movimentação prevista corretamente")
        return True
    else:
        logger.error(f"❌ TESTE 3 FALHOU: Esperado diferença de {qtd_teste}, obtido {diferenca}")
        return False


def main():
    """
    Executa todos os testes
    """
    app = create_app()
    
    with app.app_context():
        resultados = []
        
        # Executar testes
        resultados.append(("Unificação Inicial", test_unificacao_inicial()))
        resultados.append(("Saídas no Cardex", test_saidas_cardex()))
        resultados.append(("Trigger Pré-Separação", test_pre_separacao_trigger()))
        
        # Resumo
        logger.info("\n" + "="*60)
        logger.info("RESUMO DOS TESTES")
        logger.info("="*60)
        
        total = len(resultados)
        passou = sum(1 for _, r in resultados if r)
        
        for nome, resultado in resultados:
            status = "✅ PASSOU" if resultado else "❌ FALHOU"
            logger.info(f"{nome}: {status}")
        
        logger.info(f"\nTotal: {passou}/{total} testes passaram")
        
        return 0 if passou == total else 1


if __name__ == "__main__":
    sys.exit(main())