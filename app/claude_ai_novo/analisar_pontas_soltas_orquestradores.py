"""
🔍 ANÁLISE DE PONTAS SOLTAS NOS ORQUESTRADORES
Investigar se os 108 módulos órfãos são resultado de problemas nos orquestradores principais
"""

import os
import re
import json
from typing import Dict, List, Any, Set
from datetime import datetime
from pathlib import Path

def encontrar_imports_em_arquivo(arquivo_path: str) -> List[str]:
    """Encontra todos os imports em um arquivo"""
    imports = []
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Padrões de import
        patterns = [
            r'from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',
            r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',
            r'from\s+\.([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',
            r'from\s+\.\.([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)
            
    except Exception as e:
        print(f"❌ Erro ao ler {arquivo_path}: {e}")
    
    return imports

def analisar_orquestrador(arquivo_path: str) -> Dict[str, Any]:
    """Analisa um arquivo orquestrador específico"""
    
    print(f"\n🔍 Analisando orquestrador: {arquivo_path}")
    
    if not os.path.exists(arquivo_path):
        return {
            'arquivo': arquivo_path,
            'existe': False,
            'error': 'Arquivo não encontrado'
        }
    
    # Estatísticas básicas
    with open(arquivo_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    linhas = content.split('\n')
    
    # Encontrar imports
    imports = encontrar_imports_em_arquivo(arquivo_path)
    
    # Detectar funções/classes que deveriam importar módulos
    funcoes_carga = []
    for linha in linhas:
        if 'get_' in linha and ('system' in linha or 'manager' in linha or 'agent' in linha):
            funcoes_carga.append(linha.strip())
    
    # Detectar tentativas de importação (que podem estar falhando)
    tentativas_import = []
    for linha in linhas:
        if 'import' in linha and '#' not in linha:
            tentativas_import.append(linha.strip())
    
    # Detectar imports com try/except (indicativo de problemas)
    imports_condicionais = []
    in_try_block = False
    for linha in linhas:
        if 'try:' in linha:
            in_try_block = True
        elif 'except' in linha and in_try_block:
            in_try_block = False
        elif in_try_block and 'import' in linha:
            imports_condicionais.append(linha.strip())
    
    # Detectar comentários de TODO/FIXME (indicativo de problemas)
    todos_fixmes = []
    for linha in linhas:
        if any(palavra in linha.upper() for palavra in ['TODO', 'FIXME', 'HACK', 'BROKEN']):
            todos_fixmes.append(linha.strip())
    
    resultado = {
        'arquivo': arquivo_path,
        'existe': True,
        'tamanho_linhas': len(linhas),
        'total_imports': len(imports),
        'imports_unicos': len(set(imports)),
        'funcoes_carga': funcoes_carga,
        'tentativas_import': tentativas_import,
        'imports_condicionais': imports_condicionais,
        'todos_fixmes': todos_fixmes,
        'imports_detalhados': imports,
        'problemas_detectados': []
    }
    
    # Detectar problemas específicos
    if len(imports_condicionais) > 0:
        resultado['problemas_detectados'].append(f"Imports condicionais detectados: {len(imports_condicionais)}")
    
    if len(todos_fixmes) > 0:
        resultado['problemas_detectados'].append(f"TODOs/FIXMEs encontrados: {len(todos_fixmes)}")
    
    if len(imports) < 5:
        resultado['problemas_detectados'].append(f"Poucos imports para um orquestrador: {len(imports)}")
    
    return resultado

def analisar_pontas_soltas_principais():
    """Analisa os principais orquestradores em busca de pontas soltas"""
    
    print("🔍 ANÁLISE DE PONTAS SOLTAS NOS ORQUESTRADORES")
    print("=" * 80)
    
    # Definir orquestradores principais
    orquestradores_principais = [
        'integration/integration_manager.py',
        'integration/advanced/advanced_integration.py',
        '__init__.py',
        'multi_agent/system.py', 
        'multi_agent/multi_agent_orchestrator.py',
        'coordinators/system.py',
        'coordinators/integration_coordinator.py',
        'orchestrators/main_orchestrator.py',
        'providers/providers/data_provider.py',
        'data/data_manager.py'
    ]
    
    resultados = {}
    
    for orquestrador in orquestradores_principais:
        resultado = analisar_orquestrador(orquestrador)
        resultados[orquestrador] = resultado
    
    # Análise consolidada
    print("\n📊 ANÁLISE CONSOLIDADA:")
    print("=" * 80)
    
    orquestradores_existentes = [k for k, v in resultados.items() if v['existe']]
    orquestradores_faltando = [k for k, v in resultados.items() if not v['existe']]
    
    print(f"✅ Orquestradores existentes: {len(orquestradores_existentes)}")
    print(f"❌ Orquestradores faltando: {len(orquestradores_faltando)}")
    
    if orquestradores_faltando:
        print("\n❌ ORQUESTRADORES FALTANDO:")
        for orq in orquestradores_faltando:
            print(f"   - {orq}")
    
    # Análise de problemas nos existentes
    print("\n🔍 PROBLEMAS NOS ORQUESTRADORES EXISTENTES:")
    for orq, resultado in resultados.items():
        if resultado['existe'] and resultado['problemas_detectados']:
            print(f"\n📂 {orq}:")
            for problema in resultado['problemas_detectados']:
                print(f"   ⚠️ {problema}")
    
    # Análise de imports
    print("\n📦 ANÁLISE DE IMPORTS:")
    todos_imports = set()
    imports_por_orquestrador = {}
    
    for orq, resultado in resultados.items():
        if resultado['existe']:
            imports_orq = set(resultado['imports_detalhados'])
            todos_imports.update(imports_orq)
            imports_por_orquestrador[orq] = imports_orq
            
            print(f"\n📂 {orq}:")
            print(f"   Total imports: {resultado['total_imports']}")
            print(f"   Imports únicos: {resultado['imports_unicos']}")
            
            # Mostrar imports internos (que conectam com outros módulos)
            imports_internos = [imp for imp in imports_orq if 'claude_ai_novo' in imp or imp.startswith('.')]
            if imports_internos:
                print(f"   Imports internos: {len(imports_internos)}")
                for imp in imports_internos[:5]:  # Mostrar só os primeiros 5
                    print(f"     - {imp}")
                if len(imports_internos) > 5:
                    print(f"     ... e mais {len(imports_internos) - 5}")
    
    # Detectar possíveis pontas soltas
    print("\n🔗 DETECÇÃO DE PONTAS SOLTAS:")
    
    # Verificar se há pastas com módulos que não são importados
    pastas_esperadas = ['analyzers', 'processors', 'learners', 'providers', 'coordinators']
    
    for pasta in pastas_esperadas:
        if os.path.exists(pasta):
            # Listar arquivos Python na pasta
            arquivos_pasta = []
            for arquivo in os.listdir(pasta):
                if arquivo.endswith('.py') and arquivo != '__init__.py':
                    arquivos_pasta.append(arquivo[:-3])  # Remove .py
            
            # Verificar se esses arquivos são importados
            importados = 0
            for arquivo in arquivos_pasta:
                for imports_orq in imports_por_orquestrador.values():
                    if any(arquivo in imp for imp in imports_orq):
                        importados += 1
                        break
            
            taxa_importacao = (importados / len(arquivos_pasta)) * 100 if arquivos_pasta else 0
            
            print(f"\n📁 {pasta}/:")
            print(f"   Arquivos encontrados: {len(arquivos_pasta)}")
            print(f"   Arquivos importados: {importados}")
            print(f"   Taxa de importação: {taxa_importacao:.1f}%")
            
            if taxa_importacao < 50:
                print(f"   ⚠️ PONTA SOLTA DETECTADA - {100-taxa_importacao:.1f}% dos módulos órfãos!")
    
    # Salvar relatório detalhado
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'orquestradores_analisados': len(orquestradores_principais),
        'orquestradores_existentes': len(orquestradores_existentes),
        'orquestradores_faltando': len(orquestradores_faltando),
        'total_imports_unicos': len(todos_imports),
        'resultados_detalhados': resultados,
        'conclusoes': {
            'pontas_soltas_detectadas': len(orquestradores_faltando) > 0,
            'problemas_nos_existentes': sum(1 for r in resultados.values() if r.get('existe') and r.get('problemas_detectados')),
            'taxa_integracao_geral': (len(orquestradores_existentes) / len(orquestradores_principais)) * 100
        }
    }
    
    with open('RELATORIO_PONTAS_SOLTAS_ORQUESTRADORES.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório salvo em: RELATORIO_PONTAS_SOLTAS_ORQUESTRADORES.json")
    
    # Conclusões
    print("\n🎯 CONCLUSÕES:")
    print("=" * 80)
    
    if len(orquestradores_faltando) > 0:
        print(f"❌ PONTAS SOLTAS CRÍTICAS: {len(orquestradores_faltando)} orquestradores principais faltando")
        print("   Isso explica porque os módulos aparecem como órfãos!")
    
    if relatorio['conclusoes']['problemas_nos_existentes'] > 0:
        print(f"⚠️ PROBLEMAS EM EXISTENTES: {relatorio['conclusoes']['problemas_nos_existentes']} orquestradores com problemas")
    
    taxa_integracao = relatorio['conclusoes']['taxa_integracao_geral']
    if taxa_integracao < 70:
        print(f"🔴 INTEGRAÇÃO CRÍTICA: Apenas {taxa_integracao:.1f}% dos orquestradores principais funcionando")
    elif taxa_integracao < 90:
        print(f"🟡 INTEGRAÇÃO PARCIAL: {taxa_integracao:.1f}% dos orquestradores principais funcionando")
    else:
        print(f"🟢 INTEGRAÇÃO BOA: {taxa_integracao:.1f}% dos orquestradores principais funcionando")
    
    return relatorio

if __name__ == "__main__":
    try:
        relatorio = analisar_pontas_soltas_principais()
        print("\n✅ Análise concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante análise: {e}")
        import traceback
        traceback.print_exc() 