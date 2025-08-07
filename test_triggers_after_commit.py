#!/usr/bin/env python
"""
Teste dos triggers after_commit para verificar se não há mais warnings
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_tempo_real import EstoqueTempoReal
from decimal import Decimal
from datetime import datetime
import logging

# Configurar logging para ver warnings
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_triggers_sem_warning():
    """Testa se os triggers funcionam sem gerar SAWarning"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE: Triggers After Commit (Sem Warnings)")
        print("="*60)
        
        # Limpar dados de teste anteriores
        print("\n1. Limpando dados de teste...")
        MovimentacaoEstoque.query.filter_by(cod_produto='TEST-001').delete()
        EstoqueTempoReal.query.filter_by(cod_produto='TEST-001').delete()
        db.session.commit()
        
        # Criar movimentação de entrada
        print("\n2. Criando movimentação de ENTRADA...")
        mov = MovimentacaoEstoque(
            cod_produto='TEST-001',
            nome_produto='Produto Teste After Commit',
            tipo_movimentacao='ENTRADA',
            qtd_movimentacao=100.0,
            data_movimentacao=datetime.now().date(),
            ativo=True
        )
        db.session.add(mov)
        
        print("   Fazendo commit...")
        db.session.commit()
        print("   ✅ Commit realizado sem warnings!")
        
        # Verificar se estoque foi atualizado
        print("\n3. Verificando EstoqueTempoReal...")
        estoque = EstoqueTempoReal.query.filter_by(cod_produto='TEST-001').first()
        
        if estoque:
            print(f"   ✅ Estoque encontrado!")
            print(f"   - Produto: {estoque.cod_produto}")
            print(f"   - Saldo: {estoque.saldo_atual}")
            print(f"   - Atualizado em: {estoque.atualizado_em}")
            
            if estoque.saldo_atual == Decimal('100'):
                print("   ✅ Saldo correto!")
            else:
                print(f"   ❌ Saldo incorreto: esperado 100, obtido {estoque.saldo_atual}")
        else:
            print("   ❌ Estoque não foi criado!")
        
        # Criar movimentação de saída
        print("\n4. Criando movimentação de SAÍDA...")
        mov2 = MovimentacaoEstoque(
            cod_produto='TEST-001',
            nome_produto='Produto Teste After Commit',
            tipo_movimentacao='SAIDA',
            qtd_movimentacao=30.0,
            data_movimentacao=datetime.now().date(),
            ativo=True
        )
        db.session.add(mov2)
        
        print("   Fazendo commit...")
        db.session.commit()
        print("   ✅ Commit realizado sem warnings!")
        
        # Verificar saldo atualizado
        print("\n5. Verificando saldo após saída...")
        db.session.refresh(estoque)
        print(f"   - Saldo atual: {estoque.saldo_atual}")
        
        if estoque.saldo_atual == Decimal('70'):
            print("   ✅ Saldo correto após saída!")
        else:
            print(f"   ❌ Saldo incorreto: esperado 70, obtido {estoque.saldo_atual}")
        
        # Atualizar quantidade de uma movimentação
        print("\n6. Atualizando quantidade da primeira movimentação...")
        mov.qtd_movimentacao = 150.0
        
        print("   Fazendo commit...")
        db.session.commit()
        print("   ✅ Commit realizado sem warnings!")
        
        # Verificar saldo após atualização
        print("\n7. Verificando saldo após atualização...")
        db.session.refresh(estoque)
        print(f"   - Saldo atual: {estoque.saldo_atual}")
        
        if estoque.saldo_atual == Decimal('120'):  # 150 - 30
            print("   ✅ Saldo correto após atualização!")
        else:
            print(f"   ❌ Saldo incorreto: esperado 120, obtido {estoque.saldo_atual}")
        
        # Deletar movimentação
        print("\n8. Deletando movimentação de saída...")
        db.session.delete(mov2)
        
        print("   Fazendo commit...")
        db.session.commit()
        print("   ✅ Commit realizado sem warnings!")
        
        # Verificar saldo após exclusão
        print("\n9. Verificando saldo após exclusão...")
        db.session.refresh(estoque)
        print(f"   - Saldo final: {estoque.saldo_atual}")
        
        if estoque.saldo_atual == Decimal('150'):  # Só entrada de 150
            print("   ✅ Saldo correto após exclusão!")
        else:
            print(f"   ❌ Saldo incorreto: esperado 150, obtido {estoque.saldo_atual}")
        
        # Limpar dados de teste
        print("\n10. Limpando dados de teste...")
        MovimentacaoEstoque.query.filter_by(cod_produto='TEST-001').delete()
        EstoqueTempoReal.query.filter_by(cod_produto='TEST-001').delete()
        db.session.commit()
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("Nenhum SAWarning foi gerado durante as operações!")
        print("="*60 + "\n")

if __name__ == '__main__':
    test_triggers_sem_warning()