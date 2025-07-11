#!/usr/bin/env python3
"""
🔍 TESTE DE FALSO POSITIVOS - Pylance Import Errors
==================================================

Script para testar se os imports reportados como erro pelo Pylance
realmente funcionam quando executados.
"""

import sys
import os
from pathlib import Path

# Adicionar paths necessários
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("🔍 TESTANDO FALSO POSITIVOS DO PYLANCE")
print("=" * 50)

def test_import(module_path: str, description: str) -> bool:
    """Testa se um import funciona"""
    try:
        # Tentar importar o módulo
        module = __import__(module_path, fromlist=[''])
        print(f"✅ {description}")
        print(f"   📍 {module_path}")
        print(f"   📄 {getattr(module, '__file__', 'N/A')}")
        return True
    except ImportError as e:
        print(f"❌ {description}")
        print(f"   📍 {module_path}")
        print(f"   🚫 Erro: {e}")
        return False
    except Exception as e:
        print(f"⚠️ {description}")
        print(f"   📍 {module_path}")
        print(f"   ⚠️ Erro inesperado: {e}")
        return False

# Lista dos imports reportados como erro pelo Pylance
imports_para_testar = [
    ("app.claude_ai_novo.mappers.semantic_mapper", "SemanticMapper"),
    ("app.claude_ai_novo.utils.flask_context_wrapper", "FlaskContextWrapper"),
    ("app.claude_ai_novo.utils.flask_fallback", "FlaskFallback"),
    ("app.claude_ai_novo.utils.processor_registry", "ProcessorRegistry"),
    ("app.claude_ai_novo.coordinators.processor_coordinator", "ProcessorCoordinator"),
]

print("1. TESTANDO IMPORTS DE MÓDULOS:")
print("-" * 30)

sucessos = 0
total = len(imports_para_testar)

for module_path, description in imports_para_testar:
    if test_import(module_path, description):
        sucessos += 1
    print()

print("2. TESTANDO IMPORTS DE CLASSES ESPECÍFICAS:")
print("-" * 40)

# Testar imports de classes específicas
classes_para_testar = [
    ("app.claude_ai_novo.mappers.semantic_mapper", "SemanticMapper"),
    ("app.claude_ai_novo.utils.flask_context_wrapper", "FlaskContextWrapper"),
]

sucessos_classes = 0
total_classes = len(classes_para_testar)

for module_path, class_name in classes_para_testar:
    try:
        module = __import__(module_path, fromlist=[class_name])
        classe = getattr(module, class_name)
        print(f"✅ {class_name} importada com sucesso")
        print(f"   📍 {module_path}")
        print(f"   🏷️ Tipo: {type(classe)}")
        sucessos_classes += 1
    except Exception as e:
        print(f"❌ {class_name} - Erro: {e}")
    print()

print("3. VERIFICANDO ARQUIVOS FÍSICOS:")
print("-" * 30)

arquivos_para_verificar = [
    "app/claude_ai_novo/mappers/semantic_mapper.py",
    "app/claude_ai_novo/utils/flask_context_wrapper.py", 
    "app/claude_ai_novo/utils/flask_fallback.py",
    "app/claude_ai_novo/utils/processor_registry.py",
    "app/claude_ai_novo/coordinators/processor_coordinator.py",
]

arquivos_existentes = 0
total_arquivos = len(arquivos_para_verificar)

for arquivo in arquivos_para_verificar:
    caminho_completo = project_root / arquivo
    if caminho_completo.exists():
        tamanho = caminho_completo.stat().st_size
        print(f"✅ {arquivo} ({tamanho:,} bytes)")
        arquivos_existentes += 1
    else:
        print(f"❌ {arquivo} - NÃO ENCONTRADO")

print("\n" + "=" * 50)
print("📊 RESUMO DOS TESTES:")
print(f"   📦 Imports de módulos: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
print(f"   🏷️ Imports de classes: {sucessos_classes}/{total_classes} ({sucessos_classes/total_classes*100:.1f}%)")
print(f"   📄 Arquivos existentes: {arquivos_existentes}/{total_arquivos} ({arquivos_existentes/total_arquivos*100:.1f}%)")

if sucessos == total and sucessos_classes == total_classes and arquivos_existentes == total_arquivos:
    print("\n🎉 CONFIRMADO: SÃO FALSO POSITIVOS!")
    print("   Todos os imports funcionam corretamente.")
    print("   O problema está na configuração do Pylance/VS Code.")
elif sucessos >= total * 0.8:
    print("\n✅ MAIORIA SÃO FALSO POSITIVOS")
    print("   A maioria dos imports funciona - problema de configuração.")
else:
    print("\n⚠️ EXISTEM IMPORTS REALMENTE PROBLEMÁTICOS")
    print("   Alguns imports podem ter problemas reais.")

print("\n🛠️ SOLUÇÕES RECOMENDADAS:")
print("   1. Recarregar VS Code: Ctrl+Shift+P → Developer: Reload Window")  
print("   2. Limpar cache: Ctrl+Shift+P → Python: Clear Language Server Cache")
print("   3. Verificar interpretador: Ctrl+Shift+P → Python: Select Interpreter")
print("   4. Configurações aplicadas: .vscode/settings.json e pyrightconfig.json") 