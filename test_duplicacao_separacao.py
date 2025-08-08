#!/usr/bin/env python3
"""
Script para testar se a correção de duplicação de movimentação está funcionando.
Testa o cenário: PreSeparacao -> Separacao (não deve duplicar movimentação)

Uso:
    python test_duplicacao_separacao.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.models_tempo_real import MovimentacaoPrevista
from app.carteira.models import PreSeparacaoItem, CarteiraPrincipal
from app.separacao.models import Separacao
from decimal import Decimal
from datetime import date, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def limpar_teste(lote_id, cod_produto, data_expedicao):
    """Limpa dados de teste anteriores"""
    try:
        # Limpar Separacao
        Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).delete()
        
        # Limpar PreSeparacaoItem
        PreSeparacaoItem.query.filter_by(
            separacao_lote_id=lote_id
        ).delete()
        
        # Limpar MovimentacaoPrevista do teste
        MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto,
            data_prevista=data_expedicao
        ).delete()
        
        db.session.commit()
        logger.info("Dados de teste anteriores limpos")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao limpar teste: {e}")


def test_duplicacao():
    """
    Testa se a criação de Separação a partir de PreSeparação não duplica movimentação
    """
    logger.info("\n" + "="*60)
    logger.info("TESTE: Duplicação de Movimentação em Separação")
    logger.info("="*60)
    
    # Dados de teste
    lote_id = f"TEST_DUPLIC_{date.today().isoformat()}"
    cod_produto = "TEST_001"
    num_pedido = "PED_TEST_001"
    data_expedicao = date.today() + timedelta(days=5)
    qtd_teste = Decimal('100')
    
    logger.info(f"Lote de teste: {lote_id}")
    logger.info(f"Produto: {cod_produto}")
    logger.info(f"Data expedição: {data_expedicao}")
    logger.info(f"Quantidade: {qtd_teste}")
    
    # Limpar testes anteriores
    limpar_teste(lote_id, cod_produto, data_expedicao)
    
    # PASSO 1: Verificar movimentação inicial
    logger.info("\n1. Verificando movimentação inicial...")
    mov_inicial = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_inicial = Decimal(str(mov_inicial.saida_prevista)) if mov_inicial else Decimal('0')
    logger.info(f"   Saída inicial: {saida_inicial}")
    
    # PASSO 2: Criar PreSeparacaoItem
    logger.info("\n2. Criando PreSeparacaoItem...")
    pre_sep = PreSeparacaoItem(
        separacao_lote_id=lote_id,
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        cnpj_cliente="00000000000000",
        nome_produto=f"Produto Teste {cod_produto}",
        qtd_original_carteira=qtd_teste,
        qtd_selecionada_usuario=qtd_teste,
        qtd_restante_calculada=Decimal('0'),
        data_expedicao_editada=data_expedicao,
        recomposto=False,  # Não recomposto ainda
        status='CRIADO'
    )
    
    db.session.add(pre_sep)
    db.session.commit()
    logger.info(f"   PreSeparacaoItem criada: {lote_id}")
    
    # PASSO 3: Verificar movimentação após PreSeparacao
    logger.info("\n3. Verificando movimentação após PreSeparacao...")
    mov_apos_pre = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_apos_pre = Decimal(str(mov_apos_pre.saida_prevista)) if mov_apos_pre else Decimal('0')
    logger.info(f"   Saída após PreSeparacao: {saida_apos_pre}")
    logger.info(f"   Diferença: {saida_apos_pre - saida_inicial} (esperado: {qtd_teste})")
    
    # Verificar se PreSeparacao criou movimentação corretamente
    if abs((saida_apos_pre - saida_inicial) - qtd_teste) > Decimal('0.001'):
        logger.error("❌ PreSeparacao não criou movimentação correta!")
        return False
    
    # PASSO 4: Simular transformação em Separação (recomposição)
    logger.info("\n4. Transformando PreSeparacao em Separacao...")
    
    # Marcar como recomposto
    pre_sep.recomposto = True
    pre_sep.status = 'ENVIADO_SEPARACAO'
    
    # Criar Separacao (como acontece na transformação)
    separacao = Separacao(
        separacao_lote_id=lote_id,  # Mesmo lote_id
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        nome_produto=f"Produto Teste {cod_produto}",
        qtd_saldo=float(qtd_teste),
        cnpj_cpf="00000000000000",
        raz_social_red="Cliente Teste",
        nome_cidade="São Paulo",
        cod_uf="SP",
        expedicao=data_expedicao,
        tipo_envio='total'
    )
    
    db.session.add(separacao)
    db.session.commit()
    logger.info(f"   Separacao criada: {lote_id}")
    
    # PASSO 5: Verificar movimentação após Separacao
    logger.info("\n5. Verificando movimentação após Separacao...")
    mov_apos_sep = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_apos_sep = Decimal(str(mov_apos_sep.saida_prevista)) if mov_apos_sep else Decimal('0')
    logger.info(f"   Saída após Separacao: {saida_apos_sep}")
    logger.info(f"   Diferença desde PreSeparacao: {saida_apos_sep - saida_apos_pre}")
    
    # VERIFICAÇÃO FINAL: Não deve ter duplicado
    if abs(saida_apos_sep - saida_apos_pre) < Decimal('0.001'):
        logger.info("\n✅ TESTE PASSOU: Separação NÃO duplicou movimentação!")
        resultado = True
    else:
        logger.error(f"\n❌ TESTE FALHOU: Separação duplicou! Adicionou {saida_apos_sep - saida_apos_pre}")
        resultado = False
    
    # PASSO 6: Limpar dados de teste
    logger.info("\n6. Limpando dados de teste...")
    limpar_teste(lote_id, cod_produto, data_expedicao)
    
    return resultado


def test_separacao_direta():
    """
    Testa se Separação direta (sem PreSeparação) continua gerando movimentação
    """
    logger.info("\n" + "="*60)
    logger.info("TESTE: Separação Direta (deve gerar movimentação)")
    logger.info("="*60)
    
    # Dados de teste
    lote_id = f"TEST_DIRETA_{date.today().isoformat()}"
    cod_produto = "TEST_002"
    num_pedido = "PED_TEST_002"
    data_expedicao = date.today() + timedelta(days=7)
    qtd_teste = Decimal('50')
    
    logger.info(f"Lote de teste: {lote_id}")
    logger.info(f"Produto: {cod_produto}")
    logger.info(f"Quantidade: {qtd_teste}")
    
    # Limpar testes anteriores
    limpar_teste(lote_id, cod_produto, data_expedicao)
    
    # PASSO 1: Verificar movimentação inicial
    logger.info("\n1. Verificando movimentação inicial...")
    mov_inicial = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_inicial = Decimal(str(mov_inicial.saida_prevista)) if mov_inicial else Decimal('0')
    logger.info(f"   Saída inicial: {saida_inicial}")
    
    # PASSO 2: Criar Separação DIRETA (sem PreSeparacao)
    logger.info("\n2. Criando Separação direta...")
    separacao = Separacao(
        separacao_lote_id=lote_id,
        num_pedido=num_pedido,
        cod_produto=cod_produto,
        nome_produto=f"Produto Teste {cod_produto}",
        qtd_saldo=float(qtd_teste),
        cnpj_cpf="00000000000000",
        raz_social_red="Cliente Teste",
        nome_cidade="São Paulo",
        cod_uf="SP",
        expedicao=data_expedicao,
        tipo_envio='total'
    )
    
    db.session.add(separacao)
    db.session.commit()
    logger.info(f"   Separação direta criada: {lote_id}")
    
    # PASSO 3: Verificar movimentação após Separação direta
    logger.info("\n3. Verificando movimentação após Separação direta...")
    mov_apos = MovimentacaoPrevista.query.filter_by(
        cod_produto=cod_produto,
        data_prevista=data_expedicao
    ).first()
    
    saida_apos = Decimal(str(mov_apos.saida_prevista)) if mov_apos else Decimal('0')
    logger.info(f"   Saída após Separação: {saida_apos}")
    logger.info(f"   Diferença: {saida_apos - saida_inicial}")
    
    # VERIFICAÇÃO: Deve ter criado movimentação
    if abs((saida_apos - saida_inicial) - qtd_teste) < Decimal('0.001'):
        logger.info("\n✅ TESTE PASSOU: Separação direta criou movimentação corretamente!")
        resultado = True
    else:
        logger.error(f"\n❌ TESTE FALHOU: Esperado {qtd_teste}, obtido {saida_apos - saida_inicial}")
        resultado = False
    
    # PASSO 4: Limpar dados de teste
    logger.info("\n4. Limpando dados de teste...")
    limpar_teste(lote_id, cod_produto, data_expedicao)
    
    return resultado


def main():
    """
    Executa todos os testes
    """
    app = create_app()
    
    with app.app_context():
        resultados = []
        
        # Executar testes
        resultados.append(("Não duplicação (Pre->Sep)", test_duplicacao()))
        resultados.append(("Separação direta", test_separacao_direta()))
        
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
        
        if passou == total:
            logger.info("\n🎉 CORREÇÃO FUNCIONANDO PERFEITAMENTE!")
        
        return 0 if passou == total else 1


if __name__ == "__main__":
    sys.exit(main())