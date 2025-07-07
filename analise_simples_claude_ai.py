#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALISE COMPLETA DO MODULO CLAUDE_AI
Script para analisar todos os arquivos e identificar duplicacoes, rotas e funcoes
"""

import os
import re
from pathlib import Path
from datetime import datetime

def analisar_arquivo(caminho):
    """Analisa um arquivo Python e extrai informacoes importantes"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Estatisticas basicas
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
                    # Buscar metodos HTTP
                    metodos = []
                    if 'methods=' in linha:
                        metodos_match = re.search(r'methods=\[(.*?)\]', linha)
                        if metodos_match:
                            metodos = [m.strip().strip('"\'') for m in metodos_match.group(1).split(',')]
                    
                    # Buscar nome da funcao na proxima linha
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
        
        # Extrair funcoes
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
        
        return {
            'nome_arquivo': os.path.basename(caminho),
            'tamanho_kb': round(os.path.getsize(caminho) / 1024, 1),
            'total_linhas': total_linhas,
            'linhas_codigo': linhas_codigo,
            'rotas': rotas,
            'funcoes': funcoes,
            'classes': classes
        }
    
    except Exception as e:
        return {
            'nome_arquivo': os.path.basename(caminho),
            'erro': str(e)
        }

def analisar_modulo_claude_ai():
    """Analise completa do modulo claude_ai"""
    print("\n" + "="*80)
    print("ANALISE COMPLETA DO MODULO CLAUDE_AI")
    print("="*80 + "\n")
    
    # Caminho do modulo
    caminho_modulo = Path("app/claude_ai")
    
    if not caminho_modulo.exists():
        print("ERRO: Modulo claude_ai nao encontrado!")
        return
    
    # Listar todos os arquivos Python
    arquivos_python = list(caminho_modulo.glob("*.py"))
    
    print(f"Analisando {len(arquivos_python)} arquivos Python...")
    
    # Analisar cada arquivo
    resultados = []
    for arquivo in arquivos_python:
        resultado = analisar_arquivo(str(arquivo))
        resultados.append(resultado)
    
    # Ordenar por tamanho (maiores primeiro)
    resultados.sort(key=lambda x: x.get('tamanho_kb', 0), reverse=True)
    
    # Relatorio geral
    print("\n" + "="*80)
    print("RELATORIO GERAL")
    print("="*80)
    
    total_arquivos = len(resultados)
    total_linhas = sum(r.get('total_linhas', 0) for r in resultados)
    total_kb = sum(r.get('tamanho_kb', 0) for r in resultados)
    total_rotas = sum(len(r.get('rotas', [])) for r in resultados)
    total_funcoes = sum(len(r.get('funcoes', [])) for r in resultados)
    total_classes = sum(len(r.get('classes', [])) for r in resultados)
    
    print(f"Total de arquivos: {total_arquivos}")
    print(f"Total de linhas: {total_linhas:,}")
    print(f"Total de KB: {total_kb:,.1f}")
    print(f"Total de rotas: {total_rotas}")
    print(f"Total de funcoes: {total_funcoes}")
    print(f"Total de classes: {total_classes}")
    
    # Top 10 arquivos maiores
    print("\n" + "="*80)
    print("TOP 10 ARQUIVOS MAIORES")
    print("="*80)
    
    for i, arquivo in enumerate(resultados[:10], 1):
        if 'erro' in arquivo:
            print(f"{i:2d}. {arquivo['nome_arquivo']} - ERRO: {arquivo['erro']}")
        else:
            print(f"{i:2d}. {arquivo['nome_arquivo']} - {arquivo['tamanho_kb']} KB - {arquivo['total_linhas']} linhas - {len(arquivo.get('rotas', []))} rotas")
    
    # Analise de rotas por arquivo
    print("\n" + "="*80)
    print("ROTAS POR ARQUIVO")
    print("="*80)
    
    for arquivo in resultados:
        if 'rotas' in arquivo and arquivo['rotas']:
            print(f"\n{arquivo['nome_arquivo']} ({len(arquivo['rotas'])} rotas):")
            for rota in arquivo['rotas']:
                metodos = '/'.join(rota['metodos'])
                print(f"   * {rota['rota']} ({metodos}) -> {rota['funcao']}()")
    
    # Analise de classes por arquivo
    print("\n" + "="*80)
    print("CLASSES POR ARQUIVO") 
    print("="*80)
    
    for arquivo in resultados:
        if 'classes' in arquivo and arquivo['classes']:
            print(f"\n{arquivo['nome_arquivo']} ({len(arquivo['classes'])} classes):")
            for classe in arquivo['classes']:
                print(f"   * {classe['nome']} (linha {classe['linha']})")
    
    # Funcoes por arquivo (apenas nomes)
    print("\n" + "="*80)
    print("PRINCIPAIS FUNCOES POR ARQUIVO")
    print("="*80)
    
    for arquivo in resultados:
        if 'funcoes' in arquivo and arquivo['funcoes']:
            funcoes_publicas = [f for f in arquivo['funcoes'] if not f['is_private']]
            if funcoes_publicas:
                print(f"\n{arquivo['nome_arquivo']} ({len(funcoes_publicas)} funcoes publicas):")
                for funcao in funcoes_publicas[:10]:  # Top 10 funcoes
                    print(f"   * {funcao['nome']}()")
    
    # Sugestoes de organizacao
    print("\n" + "="*80)
    print("SUGESTOES DE ORGANIZACAO")
    print("="*80)
    
    print("Estrutura sugerida:")
    print("   app/claude_ai/")
    print("   |-- core/")
    print("   |   |-- __init__.py")
    print("   |   |-- integration.py      # Claude base integration")
    print("   |   |-- processor.py        # Query processing")
    print("   |   +-- config.py           # Configuration")
    print("   |-- features/")
    print("   |   |-- __init__.py")
    print("   |   |-- chat.py             # Chat functionality")
    print("   |   |-- analysis.py         # Data analysis")
    print("   |   |-- excel.py            # Excel generation")
    print("   |   +-- security.py         # Security features")
    print("   |-- utils/")
    print("   |   |-- __init__.py")
    print("   |   |-- validators.py       # Input validation")
    print("   |   |-- formatters.py       # Data formatting")
    print("   |   +-- helpers.py          # Helper functions")
    print("   |-- api/")
    print("   |   |-- __init__.py")
    print("   |   |-- routes.py           # API routes")
    print("   |   +-- handlers.py         # Request handlers")
    print("   +-- data/")
    print("       |-- __init__.py")
    print("       |-- models.py           # Database models")
    print("       +-- queries.py          # Database queries")
    
    print("\nProximos passos:")
    print("1. Consolidar funcoes duplicadas")
    print("2. Reorganizar arquivos por funcionalidade")
    print("3. Mover rotas para modulos especificos")
    print("4. Criar interfaces claras entre modulos")
    print("5. Documentar APIs e dependencias")
    
    return resultados

if __name__ == "__main__":
    print(f"Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    resultados = analisar_modulo_claude_ai()
    
    print(f"\nFim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("\n" + "="*80) 