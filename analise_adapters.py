#!/usr/bin/env python3
"""
📊 ANÁLISE DOS ADAPTERS - Verificar importância e uso no sistema
"""

import os
import ast
import json
from datetime import datetime
from typing import Dict, List, Any

def analisar_pasta_adapters() -> Dict[str, Any]:
    """Analisa toda a pasta adapters"""
    
    base_path = "adapters"
    
    resultado = {
        'analise_geral': {
            'pasta_existe': os.path.exists(base_path),
            'arquivos_encontrados': [],
            'linhas_totais': 0,
            'timestamp': datetime.now().isoformat()
        },
        'funcoes_definidas': {},
        'imports_utilizados': {},
        'uso_no_sistema': {},
        'recomendacao': ''
    }
    
    if not os.path.exists(base_path):
        resultado['analise_geral']['erro'] = "Pasta adapters não encontrada"
        return resultado
    
    # Listar arquivos
    arquivos = []
    for arquivo in os.listdir(base_path):
        if arquivo.endswith('.py'):
            arquivos.append(arquivo)
    
    resultado['analise_geral']['arquivos_encontrados'] = arquivos
    
    # Analisar cada arquivo
    for arquivo in arquivos:
        arquivo_path = os.path.join(base_path, arquivo)
        
        try:
            with open(arquivo_path, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
            # Contar linhas
            linhas = len(conteudo.splitlines())
            resultado['analise_geral']['linhas_totais'] += linhas
            
            # Analisar AST
            try:
                tree = ast.parse(conteudo)
                
                # Extrair funções
                funcoes = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        funcoes.append(node.name)
                
                resultado['funcoes_definidas'][arquivo] = {
                    'funcoes': funcoes,
                    'linhas': linhas,
                    'docstring': ast.get_docstring(tree) or "Sem docstring"
                }
                
            except SyntaxError as e:
                resultado['funcoes_definidas'][arquivo] = {
                    'erro': f"Erro de sintaxe: {e}",
                    'linhas': linhas
                }
                
        except Exception as e:
            resultado['funcoes_definidas'][arquivo] = {
                'erro': f"Erro ao ler arquivo: {e}",
                'linhas': 0
            }
    
    return resultado

def buscar_uso_adapters() -> Dict[str, Any]:
    """Busca onde os adapters são usados no sistema"""
    
    uso_real = {
        'intelligence_adapter': {
            'get_conversation_context': [],
            'get_db_session': []
        },
        'data_adapter': {
            'get_sistema_real_data': []
        }
    }
    
    # Buscar imports dos adapters
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and 'adapter' not in file:
                arquivo_path = os.path.join(root, file)
                
                try:
                    with open(arquivo_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                    
                    # Buscar imports e uso das funções
                    if 'adapters' in conteudo:
                        # Verificar intelligence_adapter
                        if 'get_conversation_context' in conteudo:
                            uso_real['intelligence_adapter']['get_conversation_context'].append(arquivo_path)
                        
                        if 'get_db_session' in conteudo:
                            uso_real['intelligence_adapter']['get_db_session'].append(arquivo_path)
                        
                        # Verificar data_adapter
                        if 'get_sistema_real_data' in conteudo:
                            uso_real['data_adapter']['get_sistema_real_data'].append(arquivo_path)
                            
                except Exception:
                    continue
    
    return uso_real

def verificar_funcoes_duplicadas() -> Dict[str, Any]:
    """Verifica se as funções dos adapters existem em outros lugares"""
    
    funcoes_duplicadas = {
        'get_conversation_context': [],
        'get_db_session': [],
        'get_sistema_real_data': []
    }
    
    # Buscar definições das funções
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                arquivo_path = os.path.join(root, file)
                
                try:
                    with open(arquivo_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                    
                    # Buscar definições de função
                    if 'def get_conversation_context' in conteudo:
                        funcoes_duplicadas['get_conversation_context'].append(arquivo_path)
                    
                    if 'def get_db_session' in conteudo:
                        funcoes_duplicadas['get_db_session'].append(arquivo_path)
                    
                    if 'def get_sistema_real_data' in conteudo:
                        funcoes_duplicadas['get_sistema_real_data'].append(arquivo_path)
                        
                except Exception:
                    continue
    
    return funcoes_duplicadas

def gerar_recomendacao(resultado: Dict[str, Any], uso_real: Dict[str, Any], 
                      funcoes_duplicadas: Dict[str, Any]) -> str:
    """Gera recomendação baseada na análise"""
    
    total_usos = 0
    for adapter in uso_real.values():
        for funcao, arquivos in adapter.items():
            total_usos += len(arquivos)
    
    total_duplicatas = 0
    for funcao, arquivos in funcoes_duplicadas.items():
        total_duplicatas += len(arquivos)
    
    # Analisar se é realmente necessário
    if total_usos <= 1:
        return "🗑️ **REMOVER** - Adapters são usados apenas em 1 local ou menos, não justificam a complexidade"
    
    elif total_duplicatas > 3:
        return "⚠️ **CONSOLIDAR** - Muitas implementações duplicadas, consolidar em um local"
    
    elif total_usos >= 3 and total_duplicatas <= 3:
        return "✅ **MANTER** - Adapters são úteis, usados em múltiplos locais e evitam duplicação"
    
    else:
        return "🔄 **AVALIAR** - Uso moderado, avaliar caso a caso se vale a pena manter"

def main():
    """Função principal"""
    
    print("🔍 ANÁLISE DOS ADAPTERS - Sistema Claude AI Novo")
    print("=" * 60)
    
    # Análise da pasta
    resultado = analisar_pasta_adapters()
    
    # Buscar uso real
    uso_real = buscar_uso_adapters()
    
    # Verificar duplicatas
    funcoes_duplicadas = verificar_funcoes_duplicadas()
    
    # Gerar recomendação
    recomendacao = gerar_recomendacao(resultado, uso_real, funcoes_duplicadas)
    
    # Relatório final
    relatorio = {
        'analise_adapters': resultado,
        'uso_real_sistema': uso_real,
        'funcoes_duplicadas': funcoes_duplicadas,
        'recomendacao_final': recomendacao,
        'estatisticas': {
            'total_arquivos_adapters': len(resultado['analise_geral']['arquivos_encontrados']),
            'total_linhas_adapters': resultado['analise_geral']['linhas_totais'],
            'total_usos_sistema': sum(len(arquivos) for adapter in uso_real.values() 
                                   for arquivos in adapter.values()),
            'total_duplicatas': sum(len(arquivos) for arquivos in funcoes_duplicadas.values())
        }
    }
    
    # Salvar relatório
    with open('ANALISE_ADAPTERS_RELATORIO.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    # Exibir resumo
    print("\n📊 RESUMO DA ANÁLISE:")
    print(f"• Arquivos na pasta adapters: {relatorio['estatisticas']['total_arquivos_adapters']}")
    print(f"• Total de linhas: {relatorio['estatisticas']['total_linhas_adapters']}")
    print(f"• Usos no sistema: {relatorio['estatisticas']['total_usos_sistema']}")
    print(f"• Funções duplicadas: {relatorio['estatisticas']['total_duplicatas']}")
    
    print(f"\n🎯 RECOMENDAÇÃO: {recomendacao}")
    
    # Detalhes dos usos
    print("\n📋 DETALHES DOS USOS:")
    for adapter_nome, adapter_funcoes in uso_real.items():
        print(f"\n{adapter_nome}:")
        for funcao, arquivos in adapter_funcoes.items():
            if arquivos:
                print(f"  • {funcao}: {len(arquivos)} usos")
                for arquivo in arquivos[:3]:  # Mostrar apenas primeiros 3
                    print(f"    - {arquivo}")
                if len(arquivos) > 3:
                    print(f"    ... e mais {len(arquivos) - 3} arquivos")
            else:
                print(f"  • {funcao}: ❌ Não usado")
    
    # Detalhes das duplicatas
    print("\n🔄 FUNÇÕES DUPLICADAS:")
    for funcao, arquivos in funcoes_duplicadas.items():
        if len(arquivos) > 1:
            print(f"• {funcao}: {len(arquivos)} implementações")
            for arquivo in arquivos[:3]:
                print(f"  - {arquivo}")
            if len(arquivos) > 3:
                print(f"  ... e mais {len(arquivos) - 3} arquivos")
    
    print(f"\n💾 Relatório completo salvo em: ANALISE_ADAPTERS_RELATORIO.json")

if __name__ == "__main__":
    main() 