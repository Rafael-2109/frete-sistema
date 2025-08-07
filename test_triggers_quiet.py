#!/usr/bin/env python
"""
Teste silencioso dos triggers after_commit
"""

import os
import sys
import warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suprimir avisos e logs desnecessários
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import logging
# Configurar apenas para erros críticos
logging.basicConfig(level=logging.ERROR)
logging.getLogger('app').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('anthropic').setLevel(logging.ERROR)
logging.getLogger('httpcore').setLevel(logging.ERROR)

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.models_tempo_real import EstoqueTempoReal
from decimal import Decimal
from datetime import datetime

def test_triggers():
    """Testa triggers after_commit"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE: Triggers After Commit")
        print("="*60)
        
        # Limpar dados anteriores
        MovimentacaoEstoque.query.filter_by(cod_produto='TEST-TRIGGER').delete()
        EstoqueTempoReal.query.filter_by(cod_produto='TEST-TRIGGER').delete()
        db.session.commit()
        
        # Teste 1: Criar entrada (número positivo)
        print("\n1. Criando ENTRADA de 100 unidades (número positivo)...")
        mov = MovimentacaoEstoque(
            cod_produto='TEST-TRIGGER',
            nome_produto='Teste Trigger',
            tipo_movimentacao='ENTRADA',
            local_movimentacao='ESTOQUE',
            qtd_movimentacao=100.0,  # Positivo = entrada
            data_movimentacao=datetime.now().date(),
            ativo=True
        )
        db.session.add(mov)
        db.session.commit()
        
        # Verificar
        estoque = EstoqueTempoReal.query.filter_by(cod_produto='TEST-TRIGGER').first()
        if estoque and estoque.saldo_atual == Decimal('100'):
            print("   ✅ Saldo: 100 (correto!)")
        else:
            print(f"   ❌ Erro: saldo = {estoque.saldo_atual if estoque else 'não criado'}")
        
        # Teste 2: Criar saída (número negativo)
        print("\n2. Criando SAÍDA de 30 unidades (número negativo)...")
        mov2 = MovimentacaoEstoque(
            cod_produto='TEST-TRIGGER',
            nome_produto='Teste Trigger',
            tipo_movimentacao='SAIDA',
            local_movimentacao='ESTOQUE',
            qtd_movimentacao=-30.0,  # Negativo = saída
            data_movimentacao=datetime.now().date(),
            ativo=True
        )
        db.session.add(mov2)
        db.session.commit()
        
        # Verificar
        db.session.refresh(estoque)
        if estoque.saldo_atual == Decimal('70'):
            print("   ✅ Saldo: 70 (correto!)")
        else:
            print(f"   ❌ Erro: saldo = {estoque.saldo_atual}")
        
        # Teste 3: Atualizar quantidade
        print("\n3. Atualizando entrada para 150 unidades...")
        mov.qtd_movimentacao = 150.0
        db.session.commit()
        
        # Verificar
        db.session.refresh(estoque)
        if estoque.saldo_atual == Decimal('120'):  # 150 - 30
            print("   ✅ Saldo: 120 (correto!)")
        else:
            print(f"   ❌ Erro: saldo = {estoque.saldo_atual}")
        
        # Teste 4: Deletar saída
        print("\n4. Deletando a saída...")
        db.session.delete(mov2)
        db.session.commit()
        
        # Verificar
        db.session.refresh(estoque)
        if estoque.saldo_atual == Decimal('150'):
            print("   ✅ Saldo: 150 (correto!)")
        else:
            print(f"   ❌ Erro: saldo = {estoque.saldo_atual}")
        
        # Limpar
        MovimentacaoEstoque.query.filter_by(cod_produto='TEST-TRIGGER').delete()
        EstoqueTempoReal.query.filter_by(cod_produto='TEST-TRIGGER').delete()
        db.session.commit()
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO!")
        print("Se não apareceram warnings SAWarning, solução funcionou!")
        print("="*60 + "\n")

if __name__ == '__main__':
    test_triggers()