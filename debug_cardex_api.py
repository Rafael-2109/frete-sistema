#!/usr/bin/env python3
"""
Script para debugar o problema do cardex com valores zerados
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
import json

def debug_cardex(cod_produto='4310071'):
    """Debug da API de cardex"""
    
    app = create_app()
    
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"DEBUG CARDEX - Produto: {cod_produto}")
        print(f"{'='*60}")
        
        # 1. Testar projeção completa
        print("\n1. Testando ServicoEstoqueSimples.get_projecao_completa()...")
        projecao = ServicoEstoqueSimples.get_projecao_completa(cod_produto, dias=3)
        
        if not projecao:
            print("   ❌ Projeção retornou None ou vazio")
            return
            
        print(f"   ✅ Projeção obtida")
        print(f"   - Estoque atual: {projecao.get('estoque_atual', 'N/A')}")
        print(f"   - Menor estoque D7: {projecao.get('menor_estoque_d7', 'N/A')}")
        print(f"   - Dia ruptura: {projecao.get('dia_ruptura', 'N/A')}")
        
        # 2. Verificar estrutura da projeção
        print("\n2. Analisando estrutura da projeção...")
        projecao_dias = projecao.get('projecao', [])
        
        if not projecao_dias:
            print("   ❌ Campo 'projecao' está vazio")
            return
            
        print(f"   ✅ Encontrados {len(projecao_dias)} dias de projeção")
        
        # 3. Analisar primeiros 3 dias
        print("\n3. Detalhamento dos primeiros 3 dias:")
        for i, dia in enumerate(projecao_dias[:3]):
            print(f"\n   D+{i}:")
            print(f"   - Data: {dia.get('data', 'N/A')}")
            print(f"   - saldo_inicial: {dia.get('saldo_inicial', 'N/A')}")
            print(f"   - entrada: {dia.get('entrada', 'N/A')}")
            print(f"   - saida: {dia.get('saida', 'N/A')}")
            print(f"   - saldo: {dia.get('saldo', 'N/A')}")
            print(f"   - saldo_final: {dia.get('saldo_final', 'N/A')}")
            
            # Verificar se os campos estão zerados
            if dia.get('saldo_inicial', 0) == 0 and dia.get('saldo_final', 0) == 0:
                print(f"   ⚠️ PROBLEMA: saldo_inicial e saldo_final estão zerados!")
        
        # 4. Simular mapeamento da API
        print("\n4. Simulando mapeamento da API cardex:")
        for i, dia_proj in enumerate(projecao_dias[:3]):
            estoque_inicial = float(dia_proj.get('saldo_inicial', 0))
            saidas = float(dia_proj.get('saida', 0))
            producao = float(dia_proj.get('entrada', 0))
            saldo = float(dia_proj.get('saldo', estoque_inicial - saidas))
            estoque_final = float(dia_proj.get('saldo_final', 0))
            
            print(f"\n   D+{i} (após mapeamento):")
            print(f"   - estoque_inicial: {estoque_inicial}")
            print(f"   - saidas: {saidas}")
            print(f"   - producao: {producao}")
            print(f"   - saldo: {saldo}")
            print(f"   - estoque_final: {estoque_final}")
        
        # 5. Verificar se é problema de estoque negativo
        print("\n5. Verificação de estoque negativo:")
        estoque_atual = projecao.get('estoque_atual', 0)
        if estoque_atual < 0:
            print(f"   ⚠️ Estoque atual é NEGATIVO: {estoque_atual}")
            print(f"   Isso pode estar causando problemas no cálculo")
        
        # 6. Salvar JSON completo para análise
        print("\n6. Salvando JSON completo em debug_cardex_output.json...")
        with open('debug_cardex_output.json', 'w') as f:
            json.dump(projecao, f, indent=2, default=str)
        print("   ✅ Arquivo salvo")
        
        print(f"\n{'='*60}")
        print("RESUMO:")
        print(f"{'='*60}")
        
        # Identificar problema principal
        problemas = []
        if estoque_atual <= 0:
            problemas.append("Estoque atual negativo ou zero")
        
        primeiro_dia = projecao_dias[0] if projecao_dias else {}
        if primeiro_dia.get('saldo_inicial', 0) == 0:
            problemas.append("saldo_inicial do D+0 está zerado")
        if primeiro_dia.get('saldo_final', 0) == 0:
            problemas.append("saldo_final do D+0 está zerado")
            
        if problemas:
            print("❌ PROBLEMAS ENCONTRADOS:")
            for p in problemas:
                print(f"   - {p}")
        else:
            print("✅ Dados parecem estar corretos")
        
        return projecao


if __name__ == '__main__':
    # Permite passar código do produto como argumento
    cod_produto = sys.argv[1] if len(sys.argv) > 1 else '4310071'
    debug_cardex(cod_produto)