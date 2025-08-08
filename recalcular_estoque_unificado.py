#!/usr/bin/env python3
"""
Script para recalcular o estoque de todos os produtos considerando unificação de códigos.
Isso corrige o problema onde o estoque inicial não estava considerando a unificação.

Uso:
    python recalcular_estoque_unificado.py [--produto COD_PRODUTO]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.models_tempo_real import EstoqueTempoReal
from app.estoque.models import UnificacaoCodigos, MovimentacaoEstoque
from decimal import Decimal
import argparse
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def recalcular_produto(cod_produto):
    """
    Recalcula o estoque de um produto específico considerando unificação
    """
    try:
        logger.info(f"Recalculando produto {cod_produto}...")
        
        # Usar método do serviço
        estoque = ServicoEstoqueTempoReal.recalcular_estoque_produto(cod_produto)
        
        logger.info(f"✅ Produto {cod_produto}: saldo_atual = {estoque.saldo_atual}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao recalcular produto {cod_produto}: {e}")
        return False


def recalcular_todos():
    """
    Recalcula o estoque de todos os produtos
    """
    logger.info("Iniciando recálculo de todos os produtos...")
    
    # Buscar todos os produtos no EstoqueTempoReal
    produtos = EstoqueTempoReal.query.all()
    total = len(produtos)
    
    logger.info(f"Total de produtos para recalcular: {total}")
    
    sucesso = 0
    erro = 0
    
    for i, produto in enumerate(produtos, 1):
        logger.info(f"[{i}/{total}] Processando {produto.cod_produto}...")
        
        if recalcular_produto(produto.cod_produto):
            sucesso += 1
        else:
            erro += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Recálculo concluído!")
    logger.info(f"✅ Sucesso: {sucesso}")
    logger.info(f"❌ Erro: {erro}")
    logger.info(f"Total: {total}")
    
    return sucesso, erro


def main():
    parser = argparse.ArgumentParser(
        description='Recalcula estoque considerando unificação de códigos'
    )
    parser.add_argument(
        '--produto',
        help='Código do produto específico (se não informado, recalcula todos)'
    )
    parser.add_argument(
        '--criar-faltantes',
        action='store_true',
        help='Criar registros EstoqueTempoReal para produtos que não existem'
    )
    
    args = parser.parse_args()
    
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        try:
            if args.criar_faltantes:
                logger.info("Criando registros faltantes...")
                
                # Buscar todos os produtos únicos em MovimentacaoEstoque
                produtos_mov = db.session.query(
                    MovimentacaoEstoque.cod_produto,
                    MovimentacaoEstoque.nome_produto
                ).filter(
                    MovimentacaoEstoque.ativo == True
                ).distinct().all()
                
                criados = 0
                for cod_produto, nome_produto in produtos_mov:
                    # Verificar se já existe
                    existe = EstoqueTempoReal.query.filter_by(
                        cod_produto=cod_produto
                    ).first()
                    
                    if not existe:
                        logger.info(f"Criando registro para {cod_produto}...")
                        ServicoEstoqueTempoReal.inicializar_produto(
                            cod_produto, 
                            nome_produto
                        )
                        criados += 1
                
                logger.info(f"✅ {criados} registros criados")
            
            if args.produto:
                # Recalcular produto específico
                sucesso = recalcular_produto(args.produto)
                return 0 if sucesso else 1
            else:
                # Recalcular todos
                sucesso, erro = recalcular_todos()
                return 0 if erro == 0 else 1
                
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())