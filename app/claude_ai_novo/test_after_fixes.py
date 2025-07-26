#!/usr/bin/env python3
"""
Teste após correções dos blocos try/except
"""

import sys
import os
from datetime import datetime

# Adicionar diretórios ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

print("🧪 TESTE APÓS CORREÇÕES DE TRY/EXCEPT")
print("="*60)
print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Lista de módulos críticos para testar
critical_modules = [
    ("flask_fallback", "app.claude_ai_novo.utils.flask_fallback"),
    ("base_classes", "app.claude_ai_novo.utils.base_classes"),
    ("knowledge_memory", "app.claude_ai_novo.memorizers.knowledge_memory"),
    ("data_provider", "app.claude_ai_novo.providers.data_provider"),
    ("orchestrator_manager", "app.claude_ai_novo.orchestrators.orchestrator_manager"),
]

success_count = 0
error_count = 0

print("\n📦 Testando imports críticos...\n")

for name, module_path in critical_modules:
    try:
        print(f"✓ Testando {name}...", end=" ")
        module = __import__(module_path, fromlist=[''])
        print("✅ OK!")
        success_count += 1
    except Exception as e:
        print(f"❌ ERRO: {e}")
        error_count += 1

# Testar sistema de transição
print("\n✓ Testando sistema de transição...")
try:
    from app.claude_transition import ClaudeAITransition
    transition = ClaudeAITransition()
    init_result = transition.inicializar_sistema()
    
    if init_result['sistema_novo_ok']:
        print("  ✅ Sistema novo OK!")
        success_count += 1
    else:
        print(f"  ⚠️ Sistema novo com erro: {init_result.get('erro_novo', 'N/A')}")
        error_count += 1
        
except Exception as e:
    print(f"  ❌ Erro ao testar transição: {e}")
    error_count += 1

# Resumo
print("\n" + "="*60)
print(f"📊 RESUMO DOS TESTES:")
print(f"  ✅ Sucesso: {success_count}")
print(f"  ❌ Erros: {error_count}")
print("="*60)

if error_count == 0:
    print("\n🎉 TODOS OS TESTES PASSARAM!")
    print("✅ As correções de try/except foram aplicadas com sucesso!")
else:
    print(f"\n⚠️ Ainda há {error_count} erros para corrigir.")
    
print("\n💡 Próximo passo: Reiniciar o servidor Flask para aplicar todas as correções.")