#!/usr/bin/env python3
"""
Análise Detalhada do claude_real_integration.py
Estudo completo do "CORAÇÃO" do sistema Claude AI
"""

import ast
import os
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any

def analisar_claude_real_integration():
    """Análise completa do arquivo claude_real_integration.py"""
    
    arquivo = "app/claude_ai/claude_real_integration.py"
    
    print("🔍 ANÁLISE DETALHADA DO CLAUDE_REAL_INTEGRATION.PY")
    print("=" * 70)
    
    # 1. Estatísticas básicas
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        linhas = conteudo.split('\n')
    
    print(f"📊 ESTATÍSTICAS BÁSICAS:")
    print(f"   • Total de linhas: {len(linhas)}")
    print(f"   • Total de caracteres: {len(conteudo)}")
    print(f"   • Total de bytes: {len(conteudo.encode('utf-8'))}")
    
    # 2. Análise de imports
    imports = defaultdict(list)
    from_imports = defaultdict(list)
    
    for linha in linhas:
        linha = linha.strip()
        if linha.startswith('import '):
            modulo = linha.replace('import ', '').split(' as ')[0]
            imports['diretos'].append(modulo)
        elif linha.startswith('from '):
            if ' import ' in linha:
                partes = linha.split(' import ')
                modulo = partes[0].replace('from ', '')
                items = partes[1].split(', ')
                from_imports[modulo].extend(items)
    
    print(f"\n📦 IMPORTS ANALISADOS:")
    print(f"   • Imports diretos: {len(imports['diretos'])}")
    print(f"   • From imports: {len(from_imports)}")
    
    # 3. Análise de classes
    classes = []
    for match in re.finditer(r'^class\s+(\w+)', conteudo, re.MULTILINE):
        classe = match.group(1)
        classes.append(classe)
    
    print(f"\n📋 CLASSES ENCONTRADAS:")
    for classe in classes:
        print(f"   • {classe}")
    
    # 4. Análise de funções
    funcoes_classe = []
    funcoes_independentes = []
    
    # Funções da classe
    for match in re.finditer(r'^\s{4}def\s+(\w+)', conteudo, re.MULTILINE):
        func = match.group(1)
        funcoes_classe.append(func)
    
    # Funções independentes
    for match in re.finditer(r'^def\s+(\w+)', conteudo, re.MULTILINE):
        func = match.group(1)
        funcoes_independentes.append(func)
    
    print(f"\n🔧 FUNÇÕES ANALISADAS:")
    print(f"   • Métodos da classe: {len(funcoes_classe)}")
    print(f"   • Funções independentes: {len(funcoes_independentes)}")
    print(f"   • TOTAL: {len(funcoes_classe) + len(funcoes_independentes)}")
    
    # 5. Análise de dependências críticas
    dependencias_criticas = []
    
    # Buscar por imports de outros módulos do claude_ai
    for modulo, items in from_imports.items():
        if modulo.startswith('.'):
            for item in items:
                dependencias_criticas.append(f"{modulo} -> {item}")
    
    print(f"\n🔗 DEPENDÊNCIAS CRÍTICAS INTERNAS:")
    for dep in dependencias_criticas:
        print(f"   • {dep}")
    
    # 6. Análise de responsabilidades
    responsabilidades = {
        'Integração Anthropic': 'anthropic',
        'Reflexão Avançada': '_processar_com_reflexao_avancada',
        'Processamento Padrão': '_processar_consulta_padrao',
        'Comandos Excel': '_processar_comando_excel',
        'Comandos Desenvolvimento': '_processar_comando_desenvolvimento',
        'Comandos Cursor': '_processar_comando_cursor',
        'Comandos Arquivo': '_processar_comando_arquivo',
        'Carregamento Dados': '_carregar_dados_',
        'Análise Consulta': '_analisar_consulta',
        'Contexto Inteligente': '_carregar_contexto_inteligente',
        'Detecção Intenção': '_detectar_intencao_refinada',
        'Sistemas Avançados': 'multi_agent_system',
        'Cache Redis': 'redis_cache',
        'Contexto Conversacional': 'conversation_context'
    }
    
    funcoes_por_responsabilidade = defaultdict(list)
    
    for func in funcoes_classe + funcoes_independentes:
        for resp, padrao in responsabilidades.items():
            if padrao in func.lower():
                funcoes_por_responsabilidade[resp].append(func)
    
    print(f"\n🎯 RESPONSABILIDADES IDENTIFICADAS:")
    for resp, funcs in funcoes_por_responsabilidade.items():
        if funcs:
            print(f"   • {resp}: {len(funcs)} funções")
            for func in funcs[:3]:  # Primeiras 3
                print(f"     - {func}")
            if len(funcs) > 3:
                print(f"     ... e mais {len(funcs) - 3}")
    
    # 7. Análise de tamanho das funções
    tamanhos_funcoes = []
    
    # Usar regex para encontrar funções e calcular tamanho aproximado
    for match in re.finditer(r'(def\s+\w+.*?)(?=\n\s*def|\nclass|\n\n\w|\Z)', conteudo, re.DOTALL):
        func_content = match.group(1)
        linhas_func = len(func_content.split('\n'))
        tamanhos_funcoes.append(linhas_func)
    
    if tamanhos_funcoes:
        print(f"\n📏 ANÁLISE DE TAMANHO DAS FUNÇÕES:")
        print(f"   • Menor função: {min(tamanhos_funcoes)} linhas")
        print(f"   • Maior função: {max(tamanhos_funcoes)} linhas")
        print(f"   • Média: {sum(tamanhos_funcoes) / len(tamanhos_funcoes):.1f} linhas")
        
        # Funções muito grandes (> 100 linhas)
        funcoes_grandes = [t for t in tamanhos_funcoes if t > 100]
        if funcoes_grandes:
            print(f"   • Funções grandes (>100 linhas): {len(funcoes_grandes)}")
    
    # 8. Sugestões de migração
    print(f"\n🚀 SUGESTÕES DE MIGRAÇÃO:")
    print(f"   1. DECOMPOSIÇÃO:")
    print(f"      • Classe principal -> core/claude_integration.py")
    print(f"      • Comandos -> commands/ (excel, dev, cursor, arquivo)")
    print(f"      • Carregamento dados -> data_loaders/")
    print(f"      • Análise -> analyzers/")
    print(f"      • Processamento -> processors/")
    
    print(f"\n   2. PRIORIDADES:")
    print(f"      • CRÍTICO: Manter compatibilidade com routes.py")
    print(f"      • CRÍTICO: Preservar todas as dependências")
    print(f"      • IMPORTANTE: Dividir por responsabilidades")
    print(f"      • IMPORTANTE: Manter performance")
    
    # 9. Plano de migração detalhado
    print(f"\n📋 PLANO DE MIGRAÇÃO DETALHADO:")
    
    plano_modules = {
        'core/claude_integration.py': [
            'ClaudeRealIntegration (classe principal)',
            'processar_consulta_real',
            '_processar_consulta_padrao',
            '_processar_com_reflexao_avancada',
            '__init__'
        ],
        'commands/excel_commands.py': [
            '_is_excel_command',
            '_processar_comando_excel'
        ],
        'commands/dev_commands.py': [
            '_is_dev_command',
            '_processar_comando_desenvolvimento'
        ],
        'commands/cursor_commands.py': [
            '_is_cursor_command',
            '_processar_comando_cursor'
        ],
        'commands/file_commands.py': [
            '_is_file_command',
            '_processar_comando_arquivo'
        ],
        'data_loaders/': [
            '_carregar_dados_entregas',
            '_carregar_dados_fretes',
            '_carregar_dados_pedidos',
            '_carregar_dados_embarques',
            '_carregar_dados_faturamento',
            '_carregar_dados_transportadoras',
            '_carregar_dados_financeiro'
        ],
        'analyzers/query_analyzer.py': [
            '_analisar_consulta',
            '_detectar_intencao_refinada',
            '_analisar_consulta_profunda'
        ],
        'processors/context_processor.py': [
            '_carregar_contexto_inteligente',
            '_build_contexto_por_intencao'
        ],
        'utils/response_utils.py': [
            '_gerar_resposta_erro',
            '_gerar_resposta_sucesso',
            '_formatar_resultado_cursor'
        ]
    }
    
    for modulo, funcoes in plano_modules.items():
        print(f"\n   📁 {modulo}:")
        for func in funcoes:
            print(f"      • {func}")
    
    print(f"\n✨ RESUMO FINAL:")
    print(f"   • Arquivo MUITO COMPLEXO ({len(linhas)} linhas)")
    print(f"   • Múltiplas responsabilidades identificadas")
    print(f"   • Decomposição em 8+ módulos recomendada")
    print(f"   • Migração deve ser feita em ETAPAS")
    print(f"   • Testes críticos para cada etapa")
    
    return {
        'total_linhas': len(linhas),
        'total_funcoes': len(funcoes_classe) + len(funcoes_independentes),
        'classes': classes,
        'funcoes_classe': funcoes_classe,
        'funcoes_independentes': funcoes_independentes,
        'dependencias_criticas': dependencias_criticas,
        'plano_modules': plano_modules
    }

if __name__ == "__main__":
    resultado = analisar_claude_real_integration()
    print("\n🎯 ANÁLISE COMPLETA FINALIZADA!") 