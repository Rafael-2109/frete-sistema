#!/usr/bin/env python3
"""
Script para testar a ordenação das colunas Produção e Disponível
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.routes import converter_projecao_para_resumo
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal

def testar_ordenacao():
    """Testa a ordenação das novas colunas"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("TESTE DE ORDENAÇÃO DAS COLUNAS")
        print("="*70)
        
        # Simular alguns produtos com dados variados
        produtos_teste = []
        
        # Produto 1: Tem produção alta, disponível em D+3
        prod1 = {
            'cod_produto': 'PROD001',
            'nome_produto': 'Produto 1',
            'estoque_atual': 100,
            'menor_estoque_d7': 50,
            'qtd_disponivel': 200,
            'dias_disponivel': 3,
            'projecao': []
        }
        resumo1 = converter_projecao_para_resumo(prod1)
        resumo1['qtd_total_producao'] = 5000  # Produção alta
        produtos_teste.append(resumo1)
        
        # Produto 2: Tem produção baixa, disponível em D+1
        prod2 = {
            'cod_produto': 'PROD002',
            'nome_produto': 'Produto 2',
            'estoque_atual': 0,
            'menor_estoque_d7': 0,
            'qtd_disponivel': 500,
            'dias_disponivel': 1,
            'projecao': []
        }
        resumo2 = converter_projecao_para_resumo(prod2)
        resumo2['qtd_total_producao'] = 100  # Produção baixa
        produtos_teste.append(resumo2)
        
        # Produto 3: Sem produção, disponível em D+3 mas com qtd maior
        prod3 = {
            'cod_produto': 'PROD003',
            'nome_produto': 'Produto 3',
            'estoque_atual': -50,
            'menor_estoque_d7': -100,
            'qtd_disponivel': 1000,
            'dias_disponivel': 3,
            'projecao': []
        }
        resumo3 = converter_projecao_para_resumo(prod3)
        resumo3['qtd_total_producao'] = 0  # Sem produção
        produtos_teste.append(resumo3)
        
        # Produto 4: Produção média, sem disponibilidade
        prod4 = {
            'cod_produto': 'PROD004',
            'nome_produto': 'Produto 4',
            'estoque_atual': -100,
            'menor_estoque_d7': -200,
            'qtd_disponivel': None,
            'dias_disponivel': None,
            'projecao': []
        }
        resumo4 = converter_projecao_para_resumo(prod4)
        resumo4['qtd_total_producao'] = 2000  # Produção média
        produtos_teste.append(resumo4)
        
        print("\n📊 PRODUTOS DE TESTE:")
        print("-"*70)
        for p in produtos_teste:
            print(f"{p['cod_produto']}: Produção={p.get('qtd_total_producao', 0)}, "
                  f"Disponível=D+{p.get('dias_disponivel', 'N/A')} "
                  f"({p.get('qtd_disponivel', 0)} un), Status={p['status_ruptura']}")
        
        # Testar ordenação por Produção
        print("\n🏭 ORDENAÇÃO POR PRODUÇÃO (DECRESCENTE):")
        print("-"*70)
        produtos_copy = produtos_teste.copy()
        produtos_copy.sort(key=lambda x: x.get('qtd_total_producao', 0), reverse=True)
        for p in produtos_copy:
            print(f"{p['cod_produto']}: {p.get('qtd_total_producao', 0)}")
        
        # Testar ordenação por Disponível (lógica especial)
        print("\n📅 ORDENAÇÃO POR DISPONÍVEL (CRESCENTE - D+ crescente, qtd decrescente):")
        print("-"*70)
        
        def sort_key_disponivel_asc(x):
            dias = x.get('dias_disponivel')
            qtd = x.get('qtd_disponivel', 0) if x.get('qtd_disponivel') else 0
            if dias is None:
                return (999999, 0)
            return (dias, -qtd)
        
        produtos_copy = produtos_teste.copy()
        produtos_copy.sort(key=sort_key_disponivel_asc)
        for p in produtos_copy:
            dias = p.get('dias_disponivel')
            qtd = p.get('qtd_disponivel', 0)
            if dias is not None:
                print(f"{p['cod_produto']}: D+{dias} ({qtd} un)")
            else:
                print(f"{p['cod_produto']}: Indisponível")
        
        print("\n📅 ORDENAÇÃO POR DISPONÍVEL (DECRESCENTE - D+ decrescente, qtd crescente):")
        print("-"*70)
        
        def sort_key_disponivel_desc(x):
            dias = x.get('dias_disponivel')
            qtd = x.get('qtd_disponivel', 0) if x.get('qtd_disponivel') else 0
            if dias is None:
                return (-999999, 0)
            return (-dias, qtd)
        
        produtos_copy = produtos_teste.copy()
        produtos_copy.sort(key=sort_key_disponivel_desc)
        for p in produtos_copy:
            dias = p.get('dias_disponivel')
            qtd = p.get('qtd_disponivel', 0)
            if dias is not None:
                print(f"{p['cod_produto']}: D+{dias} ({qtd} un)")
            else:
                print(f"{p['cod_produto']}: Indisponível")
        
        print("\n" + "="*70)
        print("✅ TESTE CONCLUÍDO!")
        print("="*70)

if __name__ == "__main__":
    testar_ordenacao()