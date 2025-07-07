#!/usr/bin/env python3
"""
🔍 ANÁLISE COMPLETA DO MÓDULO CLAUDE_AI
Script para analisar todos os arquivos e identificar duplicações, rotas e funções
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set

def analisar_arquivo(caminho: str) -> Dict:
    """Analisa um arquivo Python e extrai informações importantes"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Estatísticas básicas
        linhas = conteudo.split('\n')
        total_linhas = len(linhas)
        linhas_codigo = len([l for l in linhas if l.strip() and not l.strip().startswith('#')])
        
        # Extrair rotas Flask
        rotas = []
        for i, linha in enumerate(linhas, 1):
            if '@' in linha and 'route(' in linha:
                rota_match = re.search(r'@.*\.route\([\'"]([^\'"]+)[\'"]', linha)
                if rota_match:
                    rota = rota_match.group(1)
                    # Buscar métodos HTTP
                    metodos = []
                    if 'methods=' in linha:
                        metodos_match = re.search(r'methods=\[(.*?)\]', linha)
                        if metodos_match:
                            metodos = [m.strip().strip('"\'') for m in metodos_match.group(1).split(',')]
                    
                    # Buscar nome da função na próxima linha
                    if i < len(linhas):
                        proxima_linha = linhas[i].strip()
                        if proxima_linha.startswith('def '):
                            nome_funcao = proxima_linha.split('(')[0].replace('def ', '')
                            rotas.append({
                                'rota': rota,
                                'metodos': metodos or ['GET'],
                                'funcao': nome_funcao,
                                'linha': i
                            })
        
        # Extrair funções
        funcoes = []
        for i, linha in enumerate(linhas, 1):
            if linha.strip().startswith('def '):
                nome_funcao = linha.split('(')[0].replace('def ', '').strip()
                funcoes.append({
                    'nome': nome_funcao,
                    'linha': i,
                    'is_private': nome_funcao.startswith('_')
                })
        
        # Extrair classes
        classes = []
        for i, linha in enumerate(linhas, 1):
            if linha.strip().startswith('class '):
                nome_classe = linha.split('(')[0].replace('class ', '').strip().rstrip(':')
                classes.append({
                    'nome': nome_classe,
                    'linha': i
                })
        
        # Extrair imports
        imports = []
        for i, linha in enumerate(linhas, 1):
            if linha.strip().startswith(('import ', 'from ')):
                imports.append({
                    'import': linha.strip(),
                    'linha': i
                })
        
        # Detectar possíveis duplicações baseado em nomes de funções
        palavras_chave = ['claude', 'ai', 'real', 'integration', 'processor', 'analyzer', 'generator', 'free', 'mode', 'advanced', 'system']
        tem_duplicacao = any(palavra in os.path.basename(caminho).lower() for palavra in palavras_chave)
        
        return {
            'nome_arquivo': os.path.basename(caminho),
            'tamanho_kb': round(os.path.getsize(caminho) / 1024, 1),
            'total_linhas': total_linhas,
            'linhas_codigo': linhas_codigo,
            'rotas': rotas,
            'funcoes': funcoes,
            'classes': classes,
            'imports': imports,
            'possivel_duplicacao': tem_duplicacao
        }
    
    except Exception as e:
        return {
            'nome_arquivo': os.path.basename(caminho),
            'erro': str(e)
        }

def detectar_duplicacoes_funcoes(arquivos: List[Dict]) -> List[Dict]:
    """Detecta funções com nomes similares entre arquivos"""
    duplicacoes = []
    
    # Coletar todas as funções de todos os arquivos
    todas_funcoes = {}
    for arquivo in arquivos:
        if 'funcoes' in arquivo:
            for funcao in arquivo['funcoes']:
                nome = funcao['nome']
                if nome not in todas_funcoes:
                    todas_funcoes[nome] = []
                todas_funcoes[nome].append({
                    'arquivo': arquivo['nome_arquivo'],
                    'linha': funcao['linha']
                })
    
    # Encontrar duplicatas
    for nome, ocorrencias in todas_funcoes.items():
        if len(ocorrencias) > 1:
            duplicacoes.append({
                'nome_funcao': nome,
                'ocorrencias': ocorrencias
            })
    
    return duplicacoes

def detectar_duplicacoes_rotas(arquivos: List[Dict]) -> List[Dict]:
    """Detecta rotas duplicadas entre arquivos"""
    duplicacoes = []
    
    # Coletar todas as rotas de todos os arquivos
    todas_rotas = {}
    for arquivo in arquivos:
        if 'rotas' in arquivo:
            for rota in arquivo['rotas']:
                caminho = rota['rota']
                if caminho not in todas_rotas:
                    todas_rotas[caminho] = []
                todas_rotas[caminho].append({
                    'arquivo': arquivo['nome_arquivo'],
                    'funcao': rota['funcao'],
                    'metodos': rota['metodos']
                })
    
    # Encontrar duplicatas
    for caminho, ocorrencias in todas_rotas.items():
        if len(ocorrencias) > 1:
            duplicacoes.append({
                'rota': caminho,
                'ocorrencias': ocorrencias
            })
    
    return duplicacoes

def analisar_modulo_claude_ai():
    """Análise completa do módulo claude_ai"""
    print("\n" + "="*80)
    print("🔍 ANÁLISE COMPLETA DO MÓDULO CLAUDE_AI")
    print("="*80 + "\n")
    
    # Caminho do módulo
    caminho_modulo = Path("app/claude_ai")
    
    if not caminho_modulo.exists():
        print("❌ Módulo claude_ai não encontrado!")
        return
    
    # Listar todos os arquivos Python
    arquivos_python = list(caminho_modulo.glob("*.py"))
    
    print(f"📁 Analisando {len(arquivos_python)} arquivos Python...\n")
    
    # Analisar cada arquivo
    resultados = []
    for arquivo in arquivos_python:
        print(f"🔍 Analisando {arquivo.name}...")
        resultado = analisar_arquivo(str(arquivo))
        resultados.append(resultado)
    
    # Ordenar por tamanho (maiores primeiro)
    resultados.sort(key=lambda x: x.get('tamanho_kb', 0), reverse=True)
    
    # Relatório geral
    print("\n" + "="*80)
    print("📊 RELATÓRIO GERAL")
    print("="*80)
    
    total_arquivos = len(resultados)
    total_linhas = sum(r.get('total_linhas', 0) for r in resultados)
    total_kb = sum(r.get('tamanho_kb', 0) for r in resultados)
    total_rotas = sum(len(r.get('rotas', [])) for r in resultados)
    total_funcoes = sum(len(r.get('funcoes', [])) for r in resultados)
    total_classes = sum(len(r.get('classes', [])) for r in resultados)
    
    print(f"📁 Total de arquivos: {total_arquivos}")
    print(f"📏 Total de linhas: {total_linhas:,}")
    print(f"💾 Total de KB: {total_kb:,.1f}")
    print(f"🛣️ Total de rotas: {total_rotas}")
    print(f"⚙️ Total de funções: {total_funcoes}")
    print(f"🏗️ Total de classes: {total_classes}")
    
    # Top 10 arquivos maiores
    print("\n" + "="*80)
    print("📈 TOP 10 ARQUIVOS MAIORES")
    print("="*80)
    
    for i, arquivo in enumerate(resultados[:10], 1):
        if 'erro' in arquivo:
            print(f"{i:2d}. {arquivo['nome_arquivo']} - ERRO: {arquivo['erro']}")
        else:
            print(f"{i:2d}. {arquivo['nome_arquivo']} - {arquivo['tamanho_kb']} KB - {arquivo['total_linhas']} linhas - {len(arquivo.get('rotas', []))} rotas")
    
    # Análise de rotas por arquivo
    print("\n" + "="*80)
    print("🛣️ ROTAS POR ARQUIVO")
    print("="*80)
    
    for arquivo in resultados:
        if 'rotas' in arquivo and arquivo['rotas']:
            print(f"\n📁 {arquivo['nome_arquivo']} ({len(arquivo['rotas'])} rotas):")
            for rota in arquivo['rotas']:
                metodos = '/'.join(rota['metodos'])
                print(f"   • {rota['rota']} ({metodos}) → {rota['funcao']}()")
    
    # Análise de classes por arquivo
    print("\n" + "="*80)
    print("🏗️ CLASSES POR ARQUIVO")
    print("="*80)
    
    for arquivo in resultados:
        if 'classes' in arquivo and arquivo['classes']:
            print(f"\n📁 {arquivo['nome_arquivo']} ({len(arquivo['classes'])} classes):")
            for classe in arquivo['classes']:
                print(f"   • {classe['nome']} (linha {classe['linha']})")
    
    # Detectar duplicações
    print("\n" + "="*80)
    print("⚠️ ANÁLISE DE DUPLICAÇÕES")
    print("="*80)
    
    duplicacoes_funcoes = detectar_duplicacoes_funcoes(resultados)
    duplicacoes_rotas = detectar_duplicacoes_rotas(resultados)
    
    if duplicacoes_funcoes:
        print("\n🔄 FUNÇÕES DUPLICADAS:")
        for dup in duplicacoes_funcoes:
            print(f"   • {dup['nome_funcao']}:")
            for ocorrencia in dup['ocorrencias']:
                print(f"     - {ocorrencia['arquivo']} (linha {ocorrencia['linha']})")
    
    if duplicacoes_rotas:
        print("\n🔄 ROTAS DUPLICADAS:")
        for dup in duplicacoes_rotas:
            print(f"   • {dup['rota']}:")
            for ocorrencia in dup['ocorrencias']:
                print(f"     - {ocorrencia['arquivo']} → {ocorrencia['funcao']}()")
    
    # Arquivos com potencial de duplicação
    print("\n" + "="*80)
    print("🎯 ARQUIVOS COM POTENCIAL DE DUPLICAÇÃO")
    print("="*80)
    
    arquivos_duplicacao = [a for a in resultados if a.get('possivel_duplicacao', False)]
    
    if arquivos_duplicacao:
        print("Arquivos com nomes similares que podem ter funcionalidades duplicadas:")
        for arquivo in arquivos_duplicacao:
            print(f"   • {arquivo['nome_arquivo']} - {arquivo.get('tamanho_kb', 0)} KB")
    
    # Sugestões de organização
    print("\n" + "="*80)
    print("💡 SUGESTÕES DE ORGANIZAÇÃO")
    print("="*80)
    
    print("📁 Estrutura sugerida:")
    print("   app/claude_ai/")
    print("   ├── core/")
    print("   │   ├── __init__.py")
    print("   │   ├── integration.py      # Claude base integration")
    print("   │   ├── processor.py        # Query processing")
    print("   │   └── config.py           # Configuration")
    print("   ├── features/")
    print("   │   ├── __init__.py")
    print("   │   ├── chat.py             # Chat functionality")
    print("   │   ├── analysis.py         # Data analysis")
    print("   │   ├── excel.py            # Excel generation")
    print("   │   └── security.py         # Security features")
    print("   ├── utils/")
    print("   │   ├── __init__.py")
    print("   │   ├── validators.py       # Input validation")
    print("   │   ├── formatters.py       # Data formatting")
    print("   │   └── helpers.py          # Helper functions")
    print("   ├── api/")
    print("   │   ├── __init__.py")
    print("   │   ├── routes.py           # API routes")
    print("   │   └── handlers.py         # Request handlers")
    print("   └── data/")
    print("       ├── __init__.py")
    print("       ├── models.py           # Database models")
    print("       └── queries.py          # Database queries")
    
    print("\n🔧 Próximos passos:")
    print("1. Consolidar funções duplicadas")
    print("2. Reorganizar arquivos por funcionalidade")
    print("3. Mover rotas para módulos específicos")
    print("4. Criar interfaces claras entre módulos")
    print("5. Documentar APIs e dependências")
    
    return resultados

if __name__ == "__main__":
    print(f"Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    resultados = analisar_modulo_claude_ai()
    
    print(f"\nFim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("\n" + "="*80) 