#!/usr/bin/env python
"""
Script para testar se os triggers do estoque estão funcionando
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_triggers():
    """Testa se os triggers estão funcionando"""
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Verificar se triggers estão registrados
            from sqlalchemy import event
            from app.estoque.models import MovimentacaoEstoque
            
            listeners_insert = event.contains(MovimentacaoEstoque, 'after_insert')
            listeners_update = event.contains(MovimentacaoEstoque, 'after_update')
            
            print("\n=== VERIFICAÇÃO DE TRIGGERS ===")
            print(f"✅ Trigger after_insert registrado: {listeners_insert}")
            print(f"✅ Trigger after_update registrado: {listeners_update}")
            
            # 2. Verificar tabelas híbridas
            from app.estoque.models_hibrido import EstoqueAtual, EstoqueProjecaoCache
            
            count_atual = EstoqueAtual.query.count()
            count_projecao = EstoqueProjecaoCache.query.count()
            
            print("\n=== TABELAS HÍBRIDAS ===")
            print(f"📊 Registros em EstoqueAtual: {count_atual}")
            print(f"📊 Registros em EstoqueProjecaoCache: {count_projecao}")
            
            # 3. Testar criação de movimentação
            print("\n=== TESTE DE TRIGGER COM MOVIMENTAÇÃO ===")
            
            # Buscar um produto existente
            produto_teste = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.cod_produto.isnot(None)
            ).first()
            
            if produto_teste:
                cod_produto = produto_teste.cod_produto
                nome_produto = produto_teste.nome_produto or "Produto Teste"
                
                # Verificar estoque antes
                estoque_antes = EstoqueAtual.query.filter_by(cod_produto=cod_produto).first()
                qtd_antes = estoque_antes.estoque_atual if estoque_antes else 0
                print(f"Produto: {cod_produto} - Estoque antes: {qtd_antes}")
                
                # Criar nova movimentação
                nova_mov = MovimentacaoEstoque(
                    cod_produto=cod_produto,
                    nome_produto=nome_produto,
                    tipo_movimentacao="ENTRADA TESTE TRIGGER",
                    qtd_movimentacao=100,
                    data_movimentacao=datetime.now(),
                    local_movimentacao="TESTE",
                    observacao="Teste de trigger",
                    ativo=True
                )
                
                db.session.add(nova_mov)
                db.session.commit()
                print(f"✅ Movimentação criada: ID {nova_mov.id}")
                
                # Verificar estoque depois
                db.session.expire_all()  # Forçar recarregar do banco
                estoque_depois = EstoqueAtual.query.filter_by(cod_produto=cod_produto).first()
                qtd_depois = estoque_depois.estoque_atual if estoque_depois else 0
                print(f"Estoque depois: {qtd_depois}")
                
                if qtd_depois > qtd_antes:
                    print("✅ TRIGGER FUNCIONOU! Estoque foi atualizado automaticamente")
                else:
                    print("❌ TRIGGER NÃO FUNCIONOU! Estoque não foi atualizado")
                
                # Limpar teste
                db.session.delete(nova_mov)
                db.session.commit()
                print("🧹 Movimentação de teste removida")
                
            else:
                print("⚠️ Nenhum produto encontrado para teste")
                
            # 4. Verificar produtos marcados para recálculo
            from app.estoque.triggers_hibrido import produtos_para_recalcular
            print(f"\n📋 Produtos pendentes de recálculo: {len(produtos_para_recalcular)}")
            if produtos_para_recalcular:
                print(f"   Produtos: {list(produtos_para_recalcular)[:5]}...")
                
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    testar_triggers()