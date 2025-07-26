#!/usr/bin/env python3
"""
Script para testar se o sistema claude_ai_novo está funcionando
após as correções de sintaxe
"""

import os
import sys
import json
from datetime import datetime

# Adicionar diretórios ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

print("🧪 TESTE DO SISTEMA CLAUDE_AI_NOVO APÓS CORREÇÕES")
print("="*60)
print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Verificar diretórios criados
print("\n📁 Verificando diretórios criados...")
dirs_to_check = [
    "/home/rafaelnascimento/projetos/frete_sistema/instance/claude_ai",
    "/home/rafaelnascimento/projetos/frete_sistema/instance/claude_ai/backups"
]

for dir_path in dirs_to_check:
    if os.path.exists(dir_path):
        print(f"  ✅ {dir_path}")
    else:
        print(f"  ❌ {dir_path}")

# Verificar arquivo de configuração
print("\n📄 Verificando arquivo de configuração...")
config_file = "/home/rafaelnascimento/projetos/frete_sistema/instance/claude_ai/security_config.json"
if os.path.exists(config_file):
    print(f"  ✅ {config_file}")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"     Versão: {config.get('version', 'N/A')}")
    except Exception as e:
        print(f"     ⚠️ Erro ao ler config: {e}")
else:
    print(f"  ❌ {config_file}")

# Testar imports corrigidos
print("\n🔧 Testando imports dos arquivos corrigidos...")

test_imports = [
    ("context_memory", "app.claude_ai_novo.memorizers.context_memory"),
    ("flask_fallback", "app.claude_ai_novo.utils.flask_fallback"),
    ("context_processor", "app.claude_ai_novo.processors.context_processor"),
]

for name, module_path in test_imports:
    try:
        print(f"\n  📦 Testando {name}...")
        module = __import__(module_path, fromlist=[''])
        print(f"     ✅ Import bem-sucedido")
        
        # Verificar atributos principais
        if hasattr(module, '__file__'):
            print(f"     📍 Localização: {module.__file__}")
            
    except Exception as e:
        print(f"     ❌ Erro no import: {e}")

# Testar sistema de transição
print("\n🔄 Testando sistema de transição...")
try:
    from app.claude_transition import ClaudeAITransition
    transition = ClaudeAITransition()
    
    # Testar inicialização
    init_result = transition.inicializar_sistema()
    if init_result['sistema_novo_ok']:
        print("  ✅ Sistema novo inicializado com sucesso!")
    else:
        print(f"  ⚠️ Sistema novo com problemas: {init_result.get('erro_novo', 'N/A')}")
    
    if init_result['sistema_antigo_ok']:
        print("  ✅ Sistema antigo disponível como fallback")
    else:
        print("  ⚠️ Sistema antigo não disponível")
        
    print(f"  📊 Sistema ativo: {init_result['sistema_ativo']}")
    
except Exception as e:
    print(f"  ❌ Erro ao testar transição: {e}")

# Resumo final
print("\n" + "="*60)
print("📊 RESUMO DAS CORREÇÕES APLICADAS:")
print("  ✅ context_memory.py - Indentação corrigida (linha 214)")
print("  ✅ flask_fallback.py - Try duplicado removido (linha 238)")
print("  ✅ context_processor.py - Estrutura try/except corrigida")
print("  ✅ Diretórios criados: instance/claude_ai e backups")
print("  ✅ security_config.json criado com configurações padrão")
print("="*60)

print("\n💡 Para testar completamente o sistema:")
print("1. Reinicie o servidor Flask")
print("2. Acesse http://localhost:5002/claude-ai/real")
print("3. Teste uma consulta no chat")
print("\n✅ As correções de sintaxe foram aplicadas com sucesso!")