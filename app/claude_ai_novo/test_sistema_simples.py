#!/usr/bin/env python3
"""
Teste simples do sistema claude_ai_novo
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_orchestrator():
    """Testa se o orchestrator carrega"""
    try:
        from app.claude_ai_novo.orchestrators import MainOrchestrator
        orchestrator = MainOrchestrator()
        print("✅ MainOrchestrator carregou com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao carregar MainOrchestrator: {e}")
        return False

def test_components():
    """Testa componentes principais"""
    components = {
        'analyzers': 'app.claude_ai_novo.analyzers.analyzer_manager.AnalyzerManager',
        'processors': 'app.claude_ai_novo.processors.processor_manager.ProcessorManager',
        'enrichers': 'app.claude_ai_novo.enrichers.enricher_manager.EnricherManager',
        'memorizers': 'app.claude_ai_novo.memorizers.memory_manager.MemoryManager',
        'loaders': 'app.claude_ai_novo.loaders.loader_manager.LoaderManager',
        'providers': 'app.claude_ai_novo.providers.provider_manager.ProviderManager',
        'scanning': 'app.claude_ai_novo.scanning.scanning_manager.ScanningManager',
        'mappers': 'app.claude_ai_novo.mappers.mapper_manager.MapperManager'
    }
    
    results = {}
    for name, path in components.items():
        try:
            module_path, class_name = path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            instance = cls()
            print(f"✅ {name}: {class_name} carregou com sucesso!")
            results[name] = True
        except Exception as e:
            print(f"❌ {name}: Erro - {e}")
            results[name] = False
    
    return results

def test_integration():
    """Testa integração básica"""
    try:
        from app.claude_ai_novo.orchestrators import MainOrchestrator
        orchestrator = MainOrchestrator()
        
        # Tenta inicializar componentes
        orchestrator.initialize_components()
        print("✅ Componentes inicializados!")
        
        # Tenta conectar módulos
        orchestrator._connect_modules()
        print("✅ Módulos conectados!")
        
        return True
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False

if __name__ == "__main__":
    print("🔍 TESTE SIMPLES DO SISTEMA CLAUDE AI NOVO")
    print("=" * 60)
    
    print("\n1. Testando Orchestrator...")
    test_orchestrator()
    
    print("\n2. Testando Componentes...")
    results = test_components()
    
    print("\n3. Testando Integração...")
    test_integration()
    
    print("\n📊 RESUMO:")
    total = len(results)
    success = sum(1 for v in results.values() if v)
    print(f"Componentes funcionando: {success}/{total}")