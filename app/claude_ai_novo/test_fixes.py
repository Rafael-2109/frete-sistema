#!/usr/bin/env python3
"""
Script de teste para verificar as correções aplicadas ao sistema claude_ai_novo
"""

import os
import sys
import asyncio
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_imports():
    """Testa se os imports funcionam corretamente"""
    print("\n🔍 Testando imports...")
    
    try:
        # Teste 1: Importar generate_api_fallback_response
        print("✓ Importando generate_api_fallback_response...")
        from app.claude_ai_novo.processors.response_processor import generate_api_fallback_response
        result = generate_api_fallback_response("Teste de erro")
        print(f"  Resultado: {result}")
        assert result['success'] == False
        assert 'error' in result
        print("  ✅ Função generate_api_fallback_response funcionando!")
        
    except Exception as e:
        print(f"  ❌ Erro ao importar generate_api_fallback_response: {e}")
        return False
    
    try:
        # Teste 2: Importar BaseModule
        print("\n✓ Importando BaseModule...")
        from app.claude_ai_novo.utils.base_classes import BaseModule
        base = BaseModule()
        assert hasattr(base, 'logger')
        assert hasattr(base, 'components')
        assert hasattr(base, 'db')
        assert hasattr(base, 'config')
        assert hasattr(base, 'initialized')
        assert hasattr(base, 'redis_cache')
        print("  ✅ BaseModule tem todos os atributos necessários!")
        
    except Exception as e:
        print(f"  ❌ Erro ao importar BaseModule: {e}")
        return False
    
    try:
        # Teste 3: Importar OrchestratorManager
        print("\n✓ Importando OrchestratorManager...")
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        manager = get_orchestrator_manager()
        print(f"  ✅ OrchestratorManager carregado: {manager}")
        
    except Exception as e:
        print(f"  ❌ Erro ao importar OrchestratorManager: {e}")
        return False
    
    try:
        # Teste 4: Importar SessionOrchestrator
        print("\n✓ Importando SessionOrchestrator...")
        from app.claude_ai_novo.orchestrators.session_orchestrator import get_session_orchestrator
        session_orch = get_session_orchestrator()
        assert hasattr(session_orch, 'process_query')
        print("  ✅ SessionOrchestrator tem método process_query!")
        
    except Exception as e:
        print(f"  ❌ Erro ao importar SessionOrchestrator: {e}")
        return False
    
    return True

async def test_orchestrator_integration():
    """Testa a integração entre os orquestradores"""
    print("\n🔧 Testando integração dos orquestradores...")
    
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        
        # Obter o manager
        manager = get_orchestrator_manager()
        
        # Testar process_query
        print("\n✓ Testando process_query...")
        result = await manager.process_query(
            query="Teste de integração",
            context={'test': True}
        )
        print(f"  Resultado: {result}")
        print("  ✅ process_query funcionando!")
        
        # Testar status
        print("\n✓ Testando get_orchestrator_status...")
        status = manager.get_orchestrator_status()
        print(f"  Total de orquestradores: {status['total_orchestrators']}")
        print(f"  Orquestradores ativos: {list(status['orchestrators'].keys())}")
        print("  ✅ Status funcionando!")
        
        # Testar health check
        print("\n✓ Testando health_check...")
        health = manager.health_check()
        print(f"  Sistema saudável: {health}")
        print("  ✅ Health check funcionando!")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro na integração: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_response_processor():
    """Testa o ResponseProcessor"""
    print("\n📝 Testando ResponseProcessor...")
    
    try:
        from app.claude_ai_novo.processors.response_processor import get_response_processor
        
        processor = get_response_processor()
        
        # Testar geração de resposta
        print("\n✓ Testando gerar_resposta_otimizada...")
        resposta = processor.gerar_resposta_otimizada(
            consulta="Quais são as entregas pendentes?",
            analise={'dominio': 'entregas', 'tipo_consulta': 'dados'},
            user_context={'user_id': 1}
        )
        print(f"  Resposta gerada com {len(resposta)} caracteres")
        print("  ✅ ResponseProcessor funcionando!")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro no ResponseProcessor: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration_manager():
    """Testa o IntegrationManager"""
    print("\n🔗 Testando IntegrationManager...")
    
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        # Criar instância
        integration = IntegrationManager()
        
        # Testar inicialização
        print("\n✓ Testando initialize_all_modules...")
        result = await integration.initialize_all_modules()
        print(f"  Módulos inicializados: {result.get('modules_initialized', 0)}")
        print(f"  Score de integração: {result.get('integration_score', 0)}%")
        print("  ✅ IntegrationManager funcionando!")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro no IntegrationManager: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Função principal de testes"""
    print("="*60)
    print("🧪 TESTE DO SISTEMA CLAUDE_AI_NOVO")
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)
    
    # Executar testes
    tests_passed = 0
    total_tests = 4
    
    # Teste 1: Imports
    if test_imports():
        tests_passed += 1
    
    # Teste 2: Integração dos orquestradores
    if await test_orchestrator_integration():
        tests_passed += 1
    
    # Teste 3: ResponseProcessor
    if await test_response_processor():
        tests_passed += 1
    
    # Teste 4: IntegrationManager
    if await test_integration_manager():
        tests_passed += 1
    
    # Resultado final
    print("\n" + "="*60)
    print(f"📊 RESULTADO FINAL: {tests_passed}/{total_tests} testes passaram")
    
    if tests_passed == total_tests:
        print("✅ TODOS OS TESTES PASSARAM! Sistema funcionando!")
    else:
        print(f"⚠️ {total_tests - tests_passed} testes falharam. Verificar logs acima.")
    
    print("="*60)

if __name__ == "__main__":
    # Executar testes
    asyncio.run(main())