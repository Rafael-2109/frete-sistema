#!/usr/bin/env python3
"""
🧪 TESTAR SISTEMA ATIVADO
========================

Testa se todas as conexões foram estabelecidas corretamente.
"""

import os
import sys
import asyncio
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente para teste local
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

async def testar_sistema():
    """Testa o sistema completo"""
    print("\n🧪 TESTANDO SISTEMA CLAUDE AI NOVO ATIVADO\n")
    
    # 1. Testar OrchestratorManager
    print("1️⃣ TESTANDO ORCHESTRATOR MANAGER:")
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        orchestrator = get_orchestrator_manager()
        
        # Testar query simples
        result = await orchestrator.process_query("Como está o sistema?")
        print(f"   ✅ Query processada: {type(result)}")
        print(f"   Resposta: {str(result)[:200]}...")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Testar SessionOrchestrator
    print("\n2️⃣ TESTANDO SESSION ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator
        session_orch = SessionOrchestrator()
        
        # Verificar conexões
        print(f"   IntegrationManager: {'✅' if hasattr(session_orch, 'integration_manager') else '❌'}")
        print(f"   LearningCore: {'✅' if session_orch.learning_core else '❌'}")
        print(f"   SecurityGuard: {'✅' if session_orch.security_guard else '❌'}")
        
        # Criar sessão
        session_id = session_orch.create_session(user_id=1)
        print(f"   ✅ Sessão criada: {session_id}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Testar IntegrationManager
    print("\n3️⃣ TESTANDO INTEGRATION MANAGER:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        manager = get_integration_manager()
        
        # Verificar status
        status = manager.get_integration_status()
        print(f"   Orchestrator ativo: {status.get('orchestrator_active')}")
        print(f"   Dados disponíveis: {status.get('data_provider_available')}")
        print(f"   Claude disponível: {status.get('claude_integration_available')}")
        
        # Testar query
        result = await manager.process_unified_query("Quantas entregas existem?")
        print(f"   ✅ Query processada via Integration")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Testar Loaders
    print("\n4️⃣ TESTANDO DATA LOADERS:")
    try:
        from app.claude_ai_novo.loaders.domain import get_pedido_loader
        loader = get_pedido_loader()
        
        # Verificar se está em modo real
        mock_mode = getattr(loader, 'mock_mode', True)
        print(f"   Modo: {'❌ Mock' if mock_mode else '✅ Real'}")
        
        # Tentar carregar dados
        data = loader.load_data({'limit': 5})
        print(f"   ✅ Dados carregados: {data.get('count', 0)} registros")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Testar Sistema Completo
    print("\n5️⃣ TESTANDO SISTEMA COMPLETO:")
    try:
        from app.claude_transition import processar_consulta_transicao
        
        queries = [
            "Status do sistema",
            "Quantas entregas estão atrasadas?",
            "Quais pedidos estão pendentes?"
        ]
        
        for query in queries:
            print(f"\n   Testando: '{query}'")
            response = processar_consulta_transicao(query)
            print(f"   Resposta: {response[:150]}...")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n✅ Teste concluído!\n")

if __name__ == "__main__":
    # Executar testes
    asyncio.run(testar_sistema()) 