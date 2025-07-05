#!/usr/bin/env python3
"""
Diagnóstico detalhado do problema do Claude AI
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 DIAGNÓSTICO DETALHADO DO CLAUDE AI\n")

# Lista de módulos para testar
modules_to_test = [
    ("multi_agent_system", "get_multi_agent_system"),
    ("advanced_integration", "get_advanced_ai_integration"),
    ("nlp_enhanced_analyzer", "get_nlp_enhanced_analyzer"),
    ("intelligent_query_analyzer", "get_intelligent_query_analyzer"),
    ("enhanced_claude_integration", "get_enhanced_claude_system"),
    ("suggestion_engine", "get_suggestion_engine"),
    ("human_in_loop_learning", "get_human_learning_system"),
    ("input_validator", "InputValidator"),
    ("data_analyzer", "get_vendedor_analyzer"),
    ("alert_engine", "get_alert_engine"),
    ("mapeamento_semantico", "get_mapeamento_semantico"),
    ("mcp_connector", "MCPSistemaOnline"),
    ("lifelong_learning", "get_lifelong_learning"),
    ("conversation_context", "get_conversation_context"),
    ("auto_command_processor", "get_auto_processor"),
    ("security_guard", "get_security_guard"),
    ("claude_code_generator", "get_code_generator"),
    ("sistema_real_data", "get_sistema_real_data"),
    ("excel_generator", "ExcelGenerator")
]

print("📋 Testando imports dos módulos do Claude AI:\n")

problematic_modules = []
working_modules = []

for module_name, function_name in modules_to_test:
    try:
        # Tentar importar o módulo
        if module_name == "input_validator":
            exec(f"from app.claude_ai.{module_name} import {function_name}")
        else:
            exec(f"from app.claude_ai.{module_name} import {function_name}")
        
        print(f"✅ {module_name:<30} - OK")
        working_modules.append(module_name)
        
    except ImportError as e:
        print(f"❌ {module_name:<30} - IMPORT ERROR: {str(e)}")
        problematic_modules.append((module_name, str(e)))
        
    except Exception as e:
        print(f"⚠️  {module_name:<30} - OTHER ERROR: {type(e).__name__}: {str(e)}")
        problematic_modules.append((module_name, f"{type(e).__name__}: {str(e)}"))

# Teste específico para ml_models_real (está em utils)
try:
    from app.utils.ml_models_real import get_ml_models_system
    print(f"✅ {'ml_models_real (utils)':<30} - OK")
    working_modules.append("ml_models_real")
except Exception as e:
    print(f"❌ {'ml_models_real (utils)':<30} - ERROR: {str(e)}")
    problematic_modules.append(("ml_models_real", str(e)))

# Teste específico para config_ai
try:
    import config_ai
    print(f"✅ {'config_ai':<30} - OK")
    working_modules.append("config_ai")
except Exception as e:
    print(f"❌ {'config_ai':<30} - ERROR: {str(e)}")
    problematic_modules.append(("config_ai", str(e)))

# Resumo
print("\n" + "="*70)
print(f"📊 RESUMO DO DIAGNÓSTICO:")
print(f"✅ Módulos funcionando: {len(working_modules)}")
print(f"❌ Módulos com problemas: {len(problematic_modules)}")

if problematic_modules:
    print("\n🔴 MÓDULOS PROBLEMÁTICOS DETALHADOS:")
    for module, error in problematic_modules:
        print(f"\n📌 {module}:")
        print(f"   Erro: {error}")
        
        # Tentar identificar a causa raiz
        if "ClaudeRealIntegration" in error:
            print("   💡 Causa: Import circular com ClaudeRealIntegration")
        elif "No module named" in error:
            print("   💡 Causa: Módulo não existe ou caminho incorreto")
        elif "cannot import name" in error:
            print("   💡 Causa: Função/classe não existe no módulo")

print("\n" + "="*70)

# Teste específico do ClaudeRealIntegration
print("\n🧪 TESTE ESPECÍFICO: ClaudeRealIntegration")
try:
    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
    print("✅ ClaudeRealIntegration importa corretamente")
    
    # Tentar criar instância
    try:
        instance = ClaudeRealIntegration()
        print("✅ Instância criada com sucesso")
        print(f"   Modo real: {instance.modo_real}")
    except Exception as e:
        print(f"❌ Erro ao criar instância: {e}")
        
except Exception as e:
    print(f"❌ Erro ao importar ClaudeRealIntegration: {e}")

print("\n🏁 Diagnóstico concluído!") 