#!/usr/bin/env python3
"""
Debug do problema do JOIN com Pedido.status.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from datetime import datetime

def test_join_issue():
    """Testa o problema do JOIN."""
    app = create_app()
    
    with app.app_context():
        print("\n🧪 DEBUG: Testando problema do JOIN com status...\n")
        
        # Limpar dados de teste
        print("Limpando dados antigos...")
        Pedido.query.filter(Pedido.num_pedido.like('DEBUG%')).delete()
        Separacao.query.filter(Separacao.num_pedido.like('DEBUG%')).delete()
        CarteiraPrincipal.query.filter(CarteiraPrincipal.num_pedido.like('DEBUG%')).delete()
        db.session.commit()
        
        # Criar dados de teste
        print("\nCriando dados de teste...")
        
        # Criar Pedido com status FATURADO
        pedido = Pedido(
            num_pedido='DEBUG001',
            separacao_lote_id='LOTE_DEBUG_001',
            status='FATURADO',
            cnpj_cpf='00000000000000',
            raz_social_red='Empresa Debug',
            data_pedido=datetime.now().date()
        )
        db.session.add(pedido)
        
        # Criar Separacao
        separacao = Separacao(
            separacao_lote_id='LOTE_DEBUG_001',
            num_pedido='DEBUG001',
            cod_produto='PROD_DEBUG',
            nome_produto='Produto Debug',
            qtd_saldo=100.0,
            valor_saldo=1000.0,
            cnpj_cpf='00000000000000',
            raz_social_red='Empresa Debug',
            cod_uf='SP',
            nome_cidade='São Paulo'
        )
        db.session.add(separacao)
        
        db.session.commit()
        print(f"✅ Criado Pedido DEBUG001 com status='FATURADO' e lote='LOTE_DEBUG_001'")
        print(f"✅ Criada Separacao para DEBUG001 com lote='LOTE_DEBUG_001'")
        
        # Verificar Pedido direto
        print("\n📋 Verificando Pedido diretamente:")
        pedido_check = Pedido.query.filter_by(num_pedido='DEBUG001').first()
        if pedido_check:
            print(f"  - num_pedido: {pedido_check.num_pedido}")
            print(f"  - separacao_lote_id: {pedido_check.separacao_lote_id}")
            print(f"  - status: {pedido_check.status}")
        else:
            print("  ❌ Pedido não encontrado!")
        
        # Verificar Separacao direta
        print("\n📦 Verificando Separacao diretamente:")
        sep_check = Separacao.query.filter_by(num_pedido='DEBUG001').first()
        if sep_check:
            print(f"  - num_pedido: {sep_check.num_pedido}")
            print(f"  - separacao_lote_id: {sep_check.separacao_lote_id}")
        else:
            print("  ❌ Separacao não encontrada!")
        
        # Testar JOIN com filtro de status
        print("\n🔍 Testando JOIN com filtro de status ABERTO/COTADO:")
        query_filtrado = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == 'DEBUG001',
            Separacao.separacao_lote_id.isnot(None),
            db.or_(
                Pedido.status.in_(['ABERTO', 'COTADO']),
                Pedido.status.is_(None)
            )
        ).all()
        
        print(f"  Resultado com filtro: {query_filtrado}")
        if not query_filtrado:
            print("  ✅ CORRETO: Não encontrou (status='FATURADO' foi filtrado)")
        else:
            print("  ❌ ERRO: Encontrou mesmo com status='FATURADO'")
        
        # Testar JOIN sem filtro para debug
        print("\n🔍 Testando JOIN sem filtro de status:")
        query_sem_filtro = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status,
            Pedido.num_pedido
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == 'DEBUG001',
            Separacao.separacao_lote_id.isnot(None)
        ).all()
        
        print(f"  Resultado sem filtro:")
        for lote, status, num in query_sem_filtro:
            print(f"    - lote={lote}, status={status}, num_pedido={num}")
        
        # Testar query para ignorados
        print("\n🔍 Testando query de ignorados (status != ABERTO/COTADO):")
        query_ignorados = db.session.query(
            Separacao.separacao_lote_id,
            Pedido.status
        ).join(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        ).filter(
            Separacao.num_pedido == 'DEBUG001',
            Separacao.separacao_lote_id.isnot(None),
            ~Pedido.status.in_(['ABERTO', 'COTADO'])
        ).all()
        
        print(f"  Resultado ignorados:")
        for lote, status in query_ignorados:
            print(f"    - lote={lote}, status={status}")
        if query_ignorados:
            print("  ✅ CORRETO: Encontrou pedido FATURADO para ignorar")
        
        # Limpar dados de teste
        print("\n🧹 Limpando dados de teste...")
        Pedido.query.filter(Pedido.num_pedido.like('DEBUG%')).delete()
        Separacao.query.filter(Separacao.num_pedido.like('DEBUG%')).delete()
        db.session.commit()
        print("✅ Dados de teste limpos")

if __name__ == '__main__':
    test_join_issue()