#!/usr/bin/env python3
"""
📊 ANÁLISE DE REDUNDÂNCIAS NOS LOADERS
Verificar se há duplicação de código entre database_loader e context_loader
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any

def analisar_redundancias_loaders():
    """Analisa redundâncias entre database_loader e context_loader"""
    
    resultado = {
        'analise_geral': {
            'database_loader': {'arquivo': 'database_loader.py', 'linhas': 0, 'funcoes': []},
            'context_loader': {'arquivo': 'context_loader.py', 'linhas': 0, 'funcoes': []},
            'data_provider': {'arquivo': 'data_provider.py', 'linhas': 0, 'funcoes': []},
            'timestamp': datetime.now().isoformat()
        },
        'redundancias_encontradas': [],
        'sobreposicoes_funcionais': [],
        'recomendacoes': []
    }
    
    # Analisar database_loader
    try:
        with open('data/loaders/database_loader.py', 'r', encoding='utf-8') as f:
            content_db = f.read()
            resultado['analise_geral']['database_loader']['linhas'] = len(content_db.splitlines())
            
            # Extrair funções do database_loader
            funcoes_db = []
            for linha in content_db.splitlines():
                if linha.strip().startswith('def '):
                    funcao = linha.strip().split('def ')[1].split('(')[0]
                    funcoes_db.append(funcao)
            resultado['analise_geral']['database_loader']['funcoes'] = funcoes_db
            
    except Exception as e:
        resultado['analise_geral']['database_loader']['erro'] = str(e)
    
    # Analisar context_loader
    try:
        with open('data/loaders/context_loader.py', 'r', encoding='utf-8') as f:
            content_ctx = f.read()
            resultado['analise_geral']['context_loader']['linhas'] = len(content_ctx.splitlines())
            
            # Extrair funções do context_loader
            funcoes_ctx = []
            for linha in content_ctx.splitlines():
                if linha.strip().startswith('def '):
                    funcao = linha.strip().split('def ')[1].split('(')[0]
                    funcoes_ctx.append(funcao)
            resultado['analise_geral']['context_loader']['funcoes'] = funcoes_ctx
            
    except Exception as e:
        resultado['analise_geral']['context_loader']['erro'] = str(e)
    
    # Analisar data_provider
    try:
        with open('data/providers/data_provider.py', 'r', encoding='utf-8') as f:
            content_dp = f.read()
            resultado['analise_geral']['data_provider']['linhas'] = len(content_dp.splitlines())
            
            # Extrair funções do data_provider
            funcoes_dp = []
            for linha in content_dp.splitlines():
                if linha.strip().startswith('def '):
                    funcao = linha.strip().split('def ')[1].split('(')[0]
                    funcoes_dp.append(funcao)
            resultado['analise_geral']['data_provider']['funcoes'] = funcoes_dp
            
    except Exception as e:
        resultado['analise_geral']['data_provider']['erro'] = str(e)
    
    # Verificar redundâncias
    funcoes_db = resultado['analise_geral']['database_loader']['funcoes']
    funcoes_ctx = resultado['analise_geral']['context_loader']['funcoes']
    funcoes_dp = resultado['analise_geral']['data_provider']['funcoes']
    
    # Verificar se context_loader importa funções do database_loader
    try:
        with open('data/loaders/context_loader.py', 'r', encoding='utf-8') as f:
            content_ctx = f.read()
            if "from .database_loader import" in content_ctx:
                resultado['redundancias_encontradas'].append({
                    'tipo': 'import_dependency',
                    'descricao': 'context_loader importa funções do database_loader',
                    'detalhes': 'Há dependência direta entre os dois loaders'
                })
    except:
        pass
    
    # Verificar funções similares de carregamento
    funcoes_carregamento_db = [f for f in funcoes_db if f.startswith('_carregar_dados_')]
    funcoes_carregamento_ctx = [f for f in funcoes_ctx if f.startswith('_carregar_')]
    funcoes_carregamento_dp = [f for f in funcoes_dp if f.startswith('buscar_') or f.startswith('_carregar_')]
    
    if funcoes_carregamento_db:
        resultado['sobreposicoes_funcionais'].append({
            'componente': 'database_loader',
            'funcoes_carregamento': funcoes_carregamento_db,
            'total': len(funcoes_carregamento_db)
        })
    
    if funcoes_carregamento_ctx:
        resultado['sobreposicoes_funcionais'].append({
            'componente': 'context_loader',
            'funcoes_carregamento': funcoes_carregamento_ctx,
            'total': len(funcoes_carregamento_ctx)
        })
    
    if funcoes_carregamento_dp:
        resultado['sobreposicoes_funcionais'].append({
            'componente': 'data_provider',
            'funcoes_carregamento': funcoes_carregamento_dp,
            'total': len(funcoes_carregamento_dp)
        })
    
    # Gerar recomendações
    if len(funcoes_carregamento_db) > 5:
        resultado['recomendacoes'].append({
            'prioridade': 'alta',
            'categoria': 'database_loader',
            'problema': f'Arquivo muito grande ({resultado["analise_geral"]["database_loader"]["linhas"]} linhas) com muitas funções de carregamento',
            'solucao': 'Dividir em arquivos específicos por domínio'
        })
    
    if "from .database_loader import" in content_ctx:
        resultado['recomendacoes'].append({
            'prioridade': 'media',
            'categoria': 'context_loader',
            'problema': 'Dependência direta do database_loader',
            'solucao': 'Avaliar se context_loader é realmente necessário ou se pode ser consolidado'
        })
    
    # Verificar se há sobreposição entre data_provider e database_loader
    if len(funcoes_carregamento_dp) > 3 and len(funcoes_carregamento_db) > 3:
        resultado['recomendacoes'].append({
            'prioridade': 'alta',
            'categoria': 'arquitetura',
            'problema': 'Possível sobreposição entre data_provider e database_loader',
            'solucao': 'Consolidar responsabilidades ou eliminar um dos componentes'
        })
    
    # Avaliação final
    total_linhas = sum([
        resultado['analise_geral']['database_loader']['linhas'],
        resultado['analise_geral']['context_loader']['linhas'],
        resultado['analise_geral']['data_provider']['linhas']
    ])
    
    resultado['avaliacao_final'] = {
        'total_linhas_loaders': total_linhas,
        'arquivos_analisados': 3,
        'redundancias_criticas': len([r for r in resultado['recomendacoes'] if r['prioridade'] == 'alta']),
        'status': 'precisa_otimizacao' if total_linhas > 60000 else 'adequado',
        'recomendacao_principal': 'CONSOLIDAR' if len(resultado['recomendacoes']) > 2 else 'MANTER'
    }
    
    return resultado

if __name__ == "__main__":
    print("📊 ANÁLISE DE REDUNDÂNCIAS NOS LOADERS")
    print("=" * 50)
    
    resultado = analisar_redundancias_loaders()
    
    print("\n🔍 RESUMO DA ANÁLISE:")
    print(f"database_loader: {resultado['analise_geral']['database_loader']['linhas']} linhas")
    print(f"context_loader: {resultado['analise_geral']['context_loader']['linhas']} linhas")
    print(f"data_provider: {resultado['analise_geral']['data_provider']['linhas']} linhas")
    
    print("\n⚠️ PROBLEMAS ENCONTRADOS:")
    for problema in resultado['redundancias_encontradas']:
        print(f"- {problema['descricao']}")
    
    print("\n🎯 RECOMENDAÇÕES:")
    for rec in resultado['recomendacoes']:
        print(f"[{rec['prioridade'].upper()}] {rec['categoria']}: {rec['problema']}")
        print(f"  Solução: {rec['solucao']}")
    
    print(f"\n📊 AVALIAÇÃO FINAL: {resultado['avaliacao_final']['recomendacao_principal']}")
    
    # Salvar relatório
    with open('ANALISE_REDUNDANCIA_LOADERS.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Relatório salvo em ANALISE_REDUNDANCIA_LOADERS.json") 