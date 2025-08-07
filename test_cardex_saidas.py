#!/usr/bin/env python
"""
Teste para verificar se as saídas estão aparecendo corretamente no cardex
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from decimal import Decimal
from datetime import date, timedelta

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("TESTE: Verificar Saídas no Cardex")
    print("="*60)
    
    # 1. Criar produto teste
    cod_produto = 'TEST-CARDEX'
    
    # Limpar dados anteriores
    EstoqueTempoReal.query.filter_by(cod_produto=cod_produto).delete()
    MovimentacaoPrevista.query.filter_by(cod_produto=cod_produto).delete()
    db.session.commit()
    
    # Criar estoque inicial
    print(f"\n1. Criando estoque inicial de 1000 unidades para {cod_produto}")
    estoque = EstoqueTempoReal(
        cod_produto=cod_produto,
        nome_produto='Produto Teste Cardex',
        saldo_atual=Decimal('1000')
    )
    db.session.add(estoque)
    db.session.commit()
    
    # 2. Criar movimentações previstas
    hoje = date.today()
    print("\n2. Criando movimentações previstas:")
    
    for i in range(7):  # 7 dias
        data_prev = hoje + timedelta(days=i)
        
        # Criar saída prevista (valores positivos em saida_prevista)
        mov = MovimentacaoPrevista(
            cod_produto=cod_produto,
            data_prevista=data_prev,
            entrada_prevista=Decimal('50') if i % 2 == 0 else Decimal('0'),  # Produção dias pares
            saida_prevista=Decimal('100')  # Saída de 100 por dia
        )
        db.session.add(mov)
        print(f"   Dia {i} ({data_prev}): Entrada={mov.entrada_prevista}, Saída={mov.saida_prevista}")
    
    db.session.commit()
    
    # 3. Obter projeção completa
    print("\n3. Obtendo projeção completa:")
    projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=7)
    
    if projecao:
        print(f"   Estoque atual: {projecao['estoque_atual']}")
        print("\n   Projeção dia a dia:")
        print("   " + "-"*50)
        print("   Dia | Data       | Inicial | Entrada | Saída | Final")
        print("   " + "-"*50)
        
        for dia in projecao['projecao']:
            print(f"   D{dia['dia']:2d} | {dia['data']} | {dia['saldo_inicial']:7.0f} | {dia['entrada']:7.0f} | {dia['saida']:6.0f} | {dia['saldo_final']:6.0f}")
        
        print("   " + "-"*50)
        
        # Verificar se saídas estão aparecendo
        tem_saidas = any(dia['saida'] > 0 for dia in projecao['projecao'])
        if tem_saidas:
            print("\n   ✅ Saídas estão aparecendo corretamente na projeção!")
        else:
            print("\n   ❌ PROBLEMA: Saídas NÃO estão aparecendo na projeção!")
            
        # Verificar saldo decrescente
        saldos_corretos = True
        for i, dia in enumerate(projecao['projecao']):
            esperado = 1000 + dia['entrada'] - dia['saida']
            if i > 0:
                anterior = projecao['projecao'][i-1]['saldo_final']
                esperado = anterior + dia['entrada'] - dia['saida']
            
            if abs(dia['saldo_final'] - esperado) > 0.01:
                print(f"\n   ❌ Erro no dia {dia['dia']}: esperado {esperado}, obtido {dia['saldo_final']}")
                saldos_corretos = False
        
        if saldos_corretos:
            print("   ✅ Cálculos de saldo estão corretos!")
    else:
        print("   ❌ Erro: Projeção não retornada")
    
    # Limpar dados de teste
    EstoqueTempoReal.query.filter_by(cod_produto=cod_produto).delete()
    MovimentacaoPrevista.query.filter_by(cod_produto=cod_produto).delete()
    db.session.commit()
    
    print("\n" + "="*60)
    print("TESTE CONCLUÍDO")
    print("="*60 + "\n")