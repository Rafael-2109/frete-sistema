#!/usr/bin/env python3
"""
Script de diagnóstico para verificar produtos novos importados do Odoo
que não têm MovimentacaoEstoque nem CadastroPalletizacao inicial
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.estoque.models import MovimentacaoEstoque
from sqlalchemy import func
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnosticar_produtos_novos():
    """Diagnóstico completo de produtos novos"""
    
    app = create_app()
    
    with app.app_context():
        logger.info("=" * 70)
        logger.info("DIAGNÓSTICO DE PRODUTOS NOVOS IMPORTADOS DO ODOO")
        logger.info("=" * 70)
        
        # 1. Contar total de produtos na CarteiraPrincipal
        total_produtos = db.session.query(
            func.count(func.distinct(CarteiraPrincipal.cod_produto))
        ).filter(
            CarteiraPrincipal.ativo == True
        ).scalar()
        
        logger.info(f"\n📊 Total de produtos distintos ativos na CarteiraPrincipal: {total_produtos}")
        
        # 2. Produtos sem CadastroPalletizacao
        produtos_carteira = db.session.query(
            CarteiraPrincipal.cod_produto.distinct()
        ).filter(
            CarteiraPrincipal.ativo == True
        ).subquery()
        
        produtos_sem_palletizacao = db.session.query(
            produtos_carteira.c.cod_produto
        ).outerjoin(
            CadastroPalletizacao,
            produtos_carteira.c.cod_produto == CadastroPalletizacao.cod_produto
        ).filter(
            CadastroPalletizacao.cod_produto == None
        ).all()
        
        logger.info(f"\n❌ Produtos SEM CadastroPalletizacao: {len(produtos_sem_palletizacao)}")
        if produtos_sem_palletizacao and len(produtos_sem_palletizacao) <= 10:
            for produto in produtos_sem_palletizacao[:10]:
                logger.info(f"   - {produto[0]}")
        
        # 3. Produtos sem MovimentacaoEstoque
        produtos_sem_movimentacao = db.session.query(
            produtos_carteira.c.cod_produto
        ).outerjoin(
            MovimentacaoEstoque,
            produtos_carteira.c.cod_produto == MovimentacaoEstoque.cod_produto
        ).filter(
            MovimentacaoEstoque.cod_produto == None
        ).all()
        
        logger.info(f"\n❌ Produtos SEM MovimentacaoEstoque: {len(produtos_sem_movimentacao)}")
        if produtos_sem_movimentacao and len(produtos_sem_movimentacao) <= 10:
            for produto in produtos_sem_movimentacao[:10]:
                logger.info(f"   - {produto[0]}")
        
        # 4. Produtos que não aparecem (sem ambos)
        produtos_sem_ambos = set()
        for produto in produtos_sem_palletizacao:
            if produto in produtos_sem_movimentacao:
                produtos_sem_ambos.add(produto[0])
        
        logger.info(f"\n⚠️ Produtos SEM AMBOS (Palletização E Movimentação): {len(produtos_sem_ambos)}")
        if produtos_sem_ambos and len(produtos_sem_ambos) <= 10:
            for produto in list(produtos_sem_ambos)[:10]:
                logger.info(f"   - {produto}")
        
        # 5. Verificar se esses produtos existem na CarteiraPrincipal
        if produtos_sem_ambos:
            logger.info("\n🔍 Verificando detalhes dos produtos sem ambos:")
            
            for cod_produto in list(produtos_sem_ambos)[:5]:  # Primeiros 5
                items = CarteiraPrincipal.query.filter_by(
                    cod_produto=cod_produto,
                    ativo=True
                ).all()
                
                if items:
                    logger.info(f"\n   Produto: {cod_produto}")
                    logger.info(f"   Nome: {items[0].nome_produto}")
                    logger.info(f"   Pedidos: {', '.join(set(item.num_pedido for item in items))}")
                    logger.info(f"   Total de itens: {len(items)}")
                    
                    # Somar quantidades
                    qtd_total = sum(item.qtd_saldo_produto_pedido or 0 for item in items)
                    logger.info(f"   Qtd Total (saldo): {qtd_total}")
        
        # 6. Verificar se produtos com created_by='ImportacaoOdoo' existem
        produtos_importacao_odoo = CadastroPalletizacao.query.filter_by(
            created_by='ImportacaoOdoo'
        ).count()
        
        logger.info(f"\n✅ Produtos criados automaticamente pela ImportacaoOdoo: {produtos_importacao_odoo}")
        
        # 7. Verificar últimas importações
        ultimas_importacoes = CarteiraPrincipal.query.order_by(
            CarteiraPrincipal.created_at.desc()
        ).limit(5).all()
        
        logger.info("\n📅 Últimas 5 importações na CarteiraPrincipal:")
        for item in ultimas_importacoes:
            logger.info(f"   - {item.created_at}: {item.num_pedido}/{item.cod_produto}")
        
        # 8. Resumo final
        logger.info("\n" + "=" * 70)
        logger.info("RESUMO DO DIAGNÓSTICO:")
        logger.info("=" * 70)
        
        if len(produtos_sem_ambos) > 0:
            logger.warning(f"⚠️ PROBLEMA IDENTIFICADO: {len(produtos_sem_ambos)} produtos não têm Palletização nem Movimentação")
            logger.info("\n📌 SOLUÇÃO RECOMENDADA:")
            logger.info("1. Verificar se a importação está criando CadastroPalletizacao (linha 1342-1354 do carteira_service.py)")
            logger.info("2. Verificar logs da última importação para erros")
            logger.info("3. Executar manualmente a criação de CadastroPalletizacao para produtos faltantes")
            
            # Oferecer correção
            logger.info("\n🔧 Para corrigir automaticamente, execute:")
            logger.info("   python diagnostico_produtos_novos.py --fix")
        else:
            logger.info("✅ Todos os produtos têm pelo menos Palletização ou Movimentação")
        
        return len(produtos_sem_ambos)

def corrigir_produtos_sem_cadastro():
    """Corrige produtos sem CadastroPalletizacao"""
    
    app = create_app()
    
    with app.app_context():
        logger.info("\n🔧 INICIANDO CORREÇÃO AUTOMÁTICA...")
        
        # Buscar produtos sem palletização
        produtos_carteira = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).distinct().filter(
            CarteiraPrincipal.ativo == True
        ).all()
        
        contador = 0
        for cod_produto, nome_produto in produtos_carteira:
            # Verificar se existe em CadastroPalletizacao
            existe = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if not existe:
                # Criar com valores padrão
                novo_cadastro = CadastroPalletizacao(
                    cod_produto=cod_produto,
                    nome_produto=nome_produto or cod_produto,
                    palletizacao=1.0,
                    peso_bruto=1.0,
                    created_by='CorrecaoAutomatica',
                    updated_by='CorrecaoAutomatica'
                )
                db.session.add(novo_cadastro)
                contador += 1
                logger.info(f"   ✅ Criado cadastro para: {cod_produto}")
        
        if contador > 0:
            db.session.commit()
            logger.info(f"\n✅ {contador} produtos corrigidos com sucesso!")
        else:
            logger.info("\n✅ Nenhum produto precisou de correção")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        corrigir_produtos_sem_cadastro()
    else:
        problemas = diagnosticar_produtos_novos()
        if problemas > 0:
            logger.info("\n💡 Dica: Execute com --fix para corrigir automaticamente")
            sys.exit(1)
        else:
            sys.exit(0)