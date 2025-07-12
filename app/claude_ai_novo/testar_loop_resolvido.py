"""
Teste para validar que o loop infinito foi resolvido
"""

import sys
import os
import time
import asyncio
import threading

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.claude_ai_novo.integration.integration_manager import IntegrationManager
from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator


def test_no_circular_imports():
    """Testa se não há mais imports circulares"""
    print("\n🔍 Testando imports...")
    
    try:
        # Importar todos os módulos
        integration_manager = IntegrationManager()
        orchestrator_manager = OrchestratorManager()
        session_orchestrator = SessionOrchestrator()
        
        print("✅ Todos os módulos importados sem erro")
        
        # Verificar que SessionOrchestrator não tem mais referências circulares
        assert not hasattr(session_orchestrator, 'integration_manager'), \
            "SessionOrchestrator ainda tem integration_manager!"
        assert not hasattr(session_orchestrator, 'main_orchestrator'), \
            "SessionOrchestrator ainda tem main_orchestrator!"
        
        print("✅ Propriedades circulares removidas com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        return False


async def test_query_processing():
    """Testa processamento de query sem loop"""
    print("\n🔄 Testando processamento de query...")
    
    integration_manager = IntegrationManager()
    
    # Query que causava loop
    query = "Como estão as entregas do Atacadão?"
    context = {"user_id": "test", "session_id": "test123"}
    
    # Contador de chamadas
    call_count = 0
    original_process = integration_manager.process_unified_query
    
    async def count_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 3:
            raise Exception("Loop detectado! Mais de 3 chamadas recursivas")
        return await original_process(*args, **kwargs)
    
    # Substituir método para contar chamadas
    integration_manager.process_unified_query = count_calls
    
    try:
        # Processar query
        start_time = time.time()
        result = await integration_manager.process_unified_query(query, context)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Query processada em {elapsed_time:.2f}s")
        print(f"   Chamadas: {call_count}")
        print(f"   Resposta: {str(result)[:100]}...")
        
        # Verificações
        assert call_count <= 2, f"Muitas chamadas recursivas: {call_count}"
        assert elapsed_time < 5.0, f"Processamento muito lento: {elapsed_time}s"
        assert result is not None, "Resultado nulo"
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return False


def test_session_orchestrator_direct():
    """Testa SessionOrchestrator diretamente"""
    print("\n🎯 Testando SessionOrchestrator...")
    
    session_orchestrator = SessionOrchestrator()
    
    # Criar sessão
    session_id = session_orchestrator.create_session(user_id=1)
    print(f"✅ Sessão criada: {session_id}")
    
    # Testar workflow
    result = session_orchestrator.execute_session_workflow(
        session_id=session_id,
        workflow_type='query',
        workflow_data={
            'query': 'Status das entregas',
            'context': {}
        }
    )
    
    print(f"✅ Workflow executado: {result.get('status')}")
    
    # Verificar que não usa mais integration_manager
    assert 'integration_manager' not in str(result), \
        "Resultado ainda menciona integration_manager"
    
    return True


def test_timeout_protection():
    """Testa proteção contra travamento"""
    print("\n⏱️ Testando proteção de timeout...")
    
    async def run_with_timeout():
        integration_manager = IntegrationManager()
        query = "Como estão as entregas do Atacadão?"
        
        try:
            result = await asyncio.wait_for(
                integration_manager.process_unified_query(query, {}),
                timeout=5.0
            )
            return result
        except asyncio.TimeoutError:
            raise Exception("Timeout! Sistema travou")
    
    try:
        # Executar com timeout
        result = asyncio.run(run_with_timeout())
        print("✅ Sistema respondeu dentro do timeout")
        return True
        
    except Exception as e:
        print(f"❌ {e}")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🚀 TESTE DE RESOLUÇÃO DO LOOP INFINITO")
    print("="*60)
    
    tests = [
        ("Imports sem circularidade", test_no_circular_imports),
        ("SessionOrchestrator direto", test_session_orchestrator_direct),
        ("Proteção de timeout", test_timeout_protection)
    ]
    
    # Teste assíncrono separado
    async_test = ("Processamento sem loop", test_query_processing)
    
    results = []
    
    # Executar testes síncronos
    for test_name, test_func in tests:
        print(f"\n[{len(results)+1}/{len(tests)+1}] {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            results.append((test_name, False))
    
    # Executar teste assíncrono
    print(f"\n[{len(tests)+1}/{len(tests)+1}] {async_test[0]}")
    try:
        success = asyncio.run(async_test[1]())
        results.append((async_test[0], success))
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        results.append((async_test[0], False))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 LOOP INFINITO RESOLVIDO COM SUCESSO!")
        return True
    else:
        print("\n⚠️ Ainda há problemas a resolver")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 