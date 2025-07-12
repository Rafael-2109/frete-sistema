#!/usr/bin/env python3
"""
🔬 VERIFICAR MÉTODOS ASYNC NO MAIN ORCHESTRATOR
==============================================

Analisa detalhadamente os métodos assíncronos para confirmar
se não há riscos de conflito com event loop.
"""

import os
import sys
import ast
import inspect
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def analisar_metodos_async():
    """Analisa métodos async no MainOrchestrator"""
    print("\n🔬 ANÁLISE DETALHADA DOS MÉTODOS ASYNC\n")
    
    # Ler arquivo do MainOrchestrator
    main_orch_path = Path(__file__).parent / "orchestrators" / "main_orchestrator.py"
    
    with open(main_orch_path, 'r', encoding='utf-8') as f:
        codigo = f.read()
    
    # Parse do código
    tree = ast.parse(codigo)
    
    # Encontrar classe MainOrchestrator
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MainOrchestrator":
            print("📋 MÉTODOS ASYNC NO MAIN ORCHESTRATOR:\n")
            
            metodos_async = []
            metodos_sync_com_async = []
            
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef):
                    metodos_async.append(item.name)
                elif isinstance(item, ast.FunctionDef):
                    # Verificar se método sync chama funções async
                    for subnode in ast.walk(item):
                        if isinstance(subnode, ast.Await):
                            metodos_sync_com_async.append(item.name)
                            break
            
            # Listar métodos async
            print("1️⃣ MÉTODOS ASSÍNCRONOS:")
            for metodo in metodos_async:
                print(f"   - {metodo}")
            
            print(f"\n   Total: {len(metodos_async)} métodos async")
            
            # Verificar chamadas
            print("\n2️⃣ ANÁLISE DE CHAMADAS:")
            
            # Verificar quem chama esses métodos
            for metodo in metodos_async:
                print(f"\n   🔍 Analisando '{metodo}':")
                chamadores = []
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                        for subnode in ast.walk(item):
                            if isinstance(subnode, ast.Attribute) and subnode.attr == metodo:
                                chamadores.append(item.name)
                
                if chamadores:
                    print(f"      Chamado por: {', '.join(set(chamadores))}")
                else:
                    print(f"      ⚠️ Não encontradas chamadas diretas")
    
    # Verificar padrões de uso
    print("\n3️⃣ PADRÕES DE USO:")
    
    # Procurar por run_until_complete, asyncio.run, etc
    padroes_risco = []
    padroes_seguros = []
    
    if "run_until_complete" in codigo:
        padroes_risco.append("run_until_complete (pode causar conflito)")
    
    if "asyncio.run(" in codigo:
        padroes_seguros.append("asyncio.run (cria novo event loop)")
    
    if "ThreadPoolExecutor" in codigo:
        padroes_seguros.append("ThreadPoolExecutor (executa em thread separada)")
    
    if "await " in codigo:
        padroes_seguros.append("await (uso correto dentro de async)")
    
    print("\n   ✅ Padrões SEGUROS encontrados:")
    for padrao in padroes_seguros:
        print(f"      - {padrao}")
    
    if padroes_risco:
        print("\n   ⚠️ Padrões de RISCO encontrados:")
        for padrao in padroes_risco:
            print(f"      - {padrao}")
    else:
        print("\n   ✅ Nenhum padrão de risco encontrado!")
    
    # Verificar execute_workflow especificamente
    print("\n4️⃣ ANÁLISE DO execute_workflow:")
    
    # Procurar definição do execute_workflow
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute_workflow":
            print("   ✅ execute_workflow é SÍNCRONO")
            
            # Verificar se chama métodos async
            usa_async = False
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Await):
                    usa_async = True
                    break
            
            if usa_async:
                print("   ⚠️ execute_workflow usa await (precisa ser async)")
            else:
                print("   ✅ execute_workflow NÃO usa await diretamente")
    
    # Recomendações
    print("\n5️⃣ RECOMENDAÇÕES:")
    print("   - Os métodos async internos são seguros se chamados corretamente")
    print("   - execute_workflow é síncrono e não deve chamar async diretamente")
    print("   - Use ThreadPoolExecutor para chamar async de sync (como já foi feito)")
    print("   - Evite run_until_complete em produção (pode conflitar)")

if __name__ == "__main__":
    analisar_metodos_async() 