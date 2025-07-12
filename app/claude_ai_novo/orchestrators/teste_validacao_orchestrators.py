#!/usr/bin/env python3
"""
Teste de Validação dos Orchestrators
====================================

Este arquivo valida o funcionamento dos orchestrators para documentação.
"""
import logging
import sys
import asyncio
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def testar_orchestrator_manager():
    """Testa o OrchestratorManager (MAESTRO)"""
    print("🎭 Testando OrchestratorManager (MAESTRO)...")
    try:
        from orchestrator_manager import get_orchestrator_manager
        
        manager = get_orchestrator_manager()
        
        # Status geral
        status = manager.get_orchestrator_status()
        print(f"   📊 Total de orquestradores: {status['total_orchestrators']}")
        print(f"   🎯 Orquestradores disponíveis: {list(status['orchestrators'].keys())}")
        
        # Teste de detecção
        session_detect = manager._detect_appropriate_orchestrator("create_session", {"user": "test"})
        print(f"   🔍 Detecção para sessão: {session_detect.value}")
        
        workflow_detect = manager._detect_appropriate_orchestrator("execute_workflow", {"workflow": "test"})
        print(f"   🔍 Detecção para workflow: {workflow_detect.value}")
        
        # Teste de operação (CORRIGIDO: usando await)
        result = await manager.orchestrate_operation("test_operation", {"teste": "dados"})
        print(f"   ✅ Operação de teste: {result['success']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no OrchestratorManager: {e}")
        return False

def testar_main_orchestrator():
    """Testa o MainOrchestrator"""
    print("🎯 Testando MainOrchestrator...")
    try:
        from main_orchestrator import MainOrchestrator
        
        orchestrator = MainOrchestrator()
        
        # Teste de workflow
        result = orchestrator.execute_workflow("analyze_query", "test_operation", {"query": "teste"})
        print(f"   ✅ Workflow analyze_query: {result['success']}")
        
        # Teste de coordenação inteligente
        result = orchestrator.execute_workflow("intelligent_coordination", "intelligent_query", {"query": "teste"})
        print(f"   ✅ Coordenação inteligente: {result['success']}")
        
        # Teste de comandos naturais
        result = orchestrator.execute_workflow("natural_commands", "natural_command", {"text": "teste"})
        print(f"   ✅ Comandos naturais: {result['success']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no MainOrchestrator: {e}")
        return False

def testar_session_orchestrator():
    """Testa o SessionOrchestrator"""
    print("🔄 Testando SessionOrchestrator...")
    try:
        from session_orchestrator import get_session_orchestrator
        
        orchestrator = get_session_orchestrator()
        
        # Criar sessão
        session_id = orchestrator.create_session(user_id=1, metadata={"teste": "dados"})
        print(f"   ✅ Sessão criada: {session_id}")
        
        # Inicializar sessão
        init_result = orchestrator.initialize_session(session_id)
        print(f"   ✅ Sessão inicializada: {init_result}")
        
        # Executar workflow
        workflow_result = orchestrator.execute_session_workflow(session_id, "test_workflow", {"data": "teste"})
        print(f"   ✅ Workflow executado: {workflow_result.get('success', 'N/A')}")
        
        # Completar sessão
        complete_result = orchestrator.complete_session(session_id)
        print(f"   ✅ Sessão completada: {complete_result}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no SessionOrchestrator: {e}")
        return False

def testar_workflow_orchestrator():
    """Testa o WorkflowOrchestrator"""
    print("⚙️ Testando WorkflowOrchestrator...")
    try:
        from workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        
        # Teste de workflow
        result = orchestrator.executar_workflow("test_workflow", "analise_completa", {"dados": "teste"})
        print(f"   ✅ Workflow executado: {result['sucesso']}")
        
        # Estatísticas
        stats = orchestrator.obter_estatisticas()
        print(f"   📊 Templates disponíveis: {len(stats['templates_disponiveis'])}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no WorkflowOrchestrator: {e}")
        return False

async def testar_integracao_completa():
    """Testa integração entre orchestrators"""
    print("🔗 Testando integração completa...")
    try:
        from orchestrator_manager import get_orchestrator_manager
        
        manager = get_orchestrator_manager()
        
        # Teste de operação de sessão via manager (CORRIGIDO: usando await)
        session_result = await manager.orchestrate_operation(
            "create_session", 
            {"user_id": 1, "metadata": {"teste": "integracao"}},
            target_orchestrator=manager._detect_appropriate_orchestrator("create_session", {})
        )
        print(f"   ✅ Operação de sessão via manager: {session_result['success']}")
        
        # Teste de workflow via manager (CORRIGIDO: usando await)
        workflow_result = await manager.orchestrate_operation(
            "analise_completa",
            {"dados": "teste_integracao"},
            target_orchestrator=manager._detect_appropriate_orchestrator("workflow", {})
        )
        print(f"   ✅ Operação de workflow via manager: {workflow_result['success']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erro na integração: {e}")
        return False

async def main():
    """Função principal async"""
    print("🧪 TESTE DE VALIDAÇÃO DOS ORCHESTRATORS")
    print("=" * 50)
    
    resultados = {
        "OrchestratorManager": await testar_orchestrator_manager(),
        "MainOrchestrator": testar_main_orchestrator(),
        "SessionOrchestrator": testar_session_orchestrator(),
        "WorkflowOrchestrator": testar_workflow_orchestrator(),
        "Integração": await testar_integracao_completa()
    }
    
    print("\n📋 RESUMO DOS TESTES:")
    print("=" * 50)
    for nome, sucesso in resultados.items():
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{nome}: {status}")
    
    total_sucesso = sum(resultados.values())
    total_testes = len(resultados)
    
    print(f"\n🎯 RESULTADO FINAL: {total_sucesso}/{total_testes} testes passaram")
    
    if total_sucesso == total_testes:
        print("🎉 TODOS OS ORCHESTRATORS FUNCIONANDO CORRETAMENTE!")
        return 0
    else:
        print("⚠️ ALGUNS ORCHESTRATORS APRESENTAM PROBLEMAS")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 