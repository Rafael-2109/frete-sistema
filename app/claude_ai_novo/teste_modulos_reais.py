#!/usr/bin/env python3
"""
🔍 TESTE COM MÓDULOS REAIS
=========================

Teste usando apenas os módulos que realmente existem.
"""

def test_modulos_reais():
    """Testa módulos que realmente existem"""
    print("🔍 TESTANDO MÓDULOS REAIS")
    print("=" * 40)
    
    success_count = 0
    total_tests = 0
    
    # Managers que existem
    managers_reais = [
        ("analyzers", "get_analyzer_manager"),
        ("mappers", "get_mapper_manager"), 
        ("validators", "get_validator_manager"),
        ("processors", "get_processor_manager"),
        ("providers", "get_provider_manager"),
        ("memorizers", "get_memory_manager"),
        ("suggestions", "get_suggestions_manager"),
        ("scanning", "get_scanning_manager"),
        ("integration", "get_integration_manager"),
        ("orchestrators", "get_orchestrator_manager")
    ]
    
    for module_name, function_name in managers_reais:
        total_tests += 1
        try:
            module = __import__(f"app.claude_ai_novo.{module_name}", fromlist=[function_name])
            get_manager = getattr(module, function_name)
            manager = get_manager()
            print(f"✅ {module_name}: {function_name}() - {type(manager).__name__}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module_name}: {e}")
    
    # Enrichers (sem manager)
    total_tests += 1
    try:
        from app.claude_ai_novo.enrichers import get_semantic_enricher, get_context_enricher
        semantic = get_semantic_enricher()
        context = get_context_enricher()
        print(f"✅ enrichers: get_semantic_enricher() + get_context_enricher()")
        success_count += 1
    except Exception as e:
        print(f"❌ enrichers: {e}")
    
    # Utils (data_manager)
    total_tests += 1
    try:
        from app.claude_ai_novo.utils import get_data_manager
        data_manager = get_data_manager()
        print(f"✅ utils: get_data_manager() - {type(data_manager).__name__}")
        success_count += 1
    except Exception as e:
        print(f"❌ utils: {e}")
    
    # Flask fallback
    total_tests += 1
    try:
        from app.claude_ai_novo.utils.flask_fallback import get_current_user
        user = get_current_user()
        print(f"✅ flask_fallback: get_current_user() - {type(user)}")
        success_count += 1
    except Exception as e:
        print(f"❌ flask_fallback: {e}")
    
    # Módulos não usados mas existem
    modulos_existentes = ["commands", "conversers", "coordinators", "learners", "tools", "security"]
    
    print(f"\n📋 MÓDULOS EXISTENTES MAS NÃO USADOS:")
    for module_name in modulos_existentes:
        total_tests += 1
        try:
            module = __import__(f"app.claude_ai_novo.{module_name}")
            print(f"✅ {module_name}: Módulo existe")
            success_count += 1
        except Exception as e:
            print(f"❌ {module_name}: {e}")
    
    # Resultado
    print("=" * 40)
    success_rate = (success_count / total_tests) * 100
    print(f"🎯 RESULTADO: {success_count}/{total_tests} ({success_rate:.1f}%)")
    print(f"📊 Módulos com managers: {len(managers_reais)}")
    print(f"📊 Módulos especiais: enrichers (2 funções), utils (data_manager)")
    print(f"📊 Módulos não integrados: {len(modulos_existentes)}")
    
    return success_rate

if __name__ == "__main__":
    test_modulos_reais() 