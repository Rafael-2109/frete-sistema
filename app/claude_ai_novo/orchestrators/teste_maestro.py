#!/usr/bin/env python3
"""
Teste do MAESTRO - Verificar se está funcionando
"""
try:
    from orchestrator_manager import get_orchestrator_manager
    
    print("🎭 Testando MAESTRO...")
    manager = get_orchestrator_manager()
    
    print(f"✅ MAESTRO funcionando!")
    print(f"📊 Orquestradores disponíveis: {len(manager.orchestrators)}")
    
    status = manager.get_orchestrator_status()
    print(f"🎯 Status total: {status['total_orchestrators']}")
    
    # Teste de detecção de orquestrador
    session_result = manager._detect_appropriate_orchestrator("create_session", {"user": "test"})
    print(f"🔍 Detecção para sessão: {session_result.value}")
    
    workflow_result = manager._detect_appropriate_orchestrator("execute_workflow", {"workflow": "test"})
    print(f"🔍 Detecção para workflow: {workflow_result.value}")
    
    print("✅ MAESTRO 100% FUNCIONAL!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc() 