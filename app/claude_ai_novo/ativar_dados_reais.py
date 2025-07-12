#!/usr/bin/env python3
"""
🚀 ATIVAR DADOS REAIS NO CLAUDE AI NOVO
======================================

Este script garante que o sistema use dados reais do banco
em vez de respostas genéricas.
"""

import os
import sys
import asyncio
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

async def testar_dados_reais():
    """Testa se o sistema está usando dados reais"""
    
    print("🚀 ATIVANDO DADOS REAIS NO CLAUDE AI NOVO\n")
    
    # 1. Testar IntegrationManager
    print("1️⃣ TESTANDO INTEGRATION MANAGER:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        integration = get_integration_manager()
        
        # Testar query simples
        result = await integration.process_unified_query("Como estão as entregas do Atacadão?")
        
        print(f"   ✅ IntegrationManager: {integration.orchestrator_manager is not None}")
        print(f"   📊 Resultado: {type(result)}")
        if isinstance(result, dict):
            print(f"   📝 Resposta: {result.get('response', 'N/A')[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Testar CoordinatorManager
    print("\n2️⃣ TESTANDO COORDINATOR MANAGER:")
    try:
        from app.claude_ai_novo.coordinators import get_coordinator_manager
        coordinator = get_coordinator_manager()
        
        # Verificar agentes
        print(f"   ✅ Agentes disponíveis: {len(coordinator.agents)}")
        for agent_name in coordinator.agents:
            print(f"      - {agent_name}")
        
        # Testar coordenação
        coord_result = coordinator.coordinate_query(
            "entregas do atacadão",
            {"domain": "entregas"}
        )
        
        print(f"   📊 Coordenador usado: {coord_result.get('coordinator_used', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Testar Loaders de Dados
    print("\n3️⃣ TESTANDO DATA LOADERS:")
    try:
        from app.claude_ai_novo.loaders.domain import (
            get_entregas_loader, get_pedidos_loader, get_fretes_loader
        )
        
        # Testar EntregasLoader
        entregas_loader = get_entregas_loader()
        print(f"   ✅ EntregasLoader disponível")
        
        # Tentar carregar dados
        entregas_data = entregas_loader.load_by_filters({"cliente": "atacadão"})
        print(f"   📊 Entregas encontradas: {len(entregas_data.get('entregas', []))}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Testar MainOrchestrator
    print("\n4️⃣ TESTANDO MAIN ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
        main_orch = get_main_orchestrator()
        
        # Executar workflow
        workflow_result = main_orch.execute_workflow(
            "intelligent_coordination",
            "intelligent_query",
            {
                "query": "Como estão as entregas do Atacadão?",
                "context": {}
            }
        )
        
        print(f"   ✅ Workflow executado")
        print(f"   📊 Resultado tradicional: {workflow_result.get('traditional_result', {}).get('success', False)}")
        print(f"   🧠 Resultado inteligente: {workflow_result.get('intelligent_result') is not None}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Teste completo via OrchestratorManager
    print("\n5️⃣ TESTE COMPLETO VIA ORCHESTRATOR MANAGER:")
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        orchestrator = get_orchestrator_manager()
        
        # Query completa
        full_result = await orchestrator.process_query(
            "Como estão as entregas do Atacadão?",
            {"user_id": 1}
        )
        
        print(f"   ✅ Query processada")
        print(f"   📊 Sucesso: {full_result.get('success', False)}")
        print(f"   🎯 Orchestrator usado: {full_result.get('orchestrator', 'N/A')}")
        
        # Extrair resposta real
        if full_result.get('result'):
            result_data = full_result['result']
            if isinstance(result_data, dict):
                # Procurar resposta em diferentes lugares
                response = (
                    result_data.get('result') or
                    result_data.get('response') or
                    result_data.get('intelligent_result', {}).get('response') or
                    result_data.get('coordination_result', {}).get('response') or
                    "Sem resposta"
                )
                print(f"   📝 Resposta: {str(response)[:200]}...")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n✅ TESTE CONCLUÍDO!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Se vir 'Sistema operacional e processando' = resposta genérica")
    print("2. Se vir dados específicos = dados reais ativados")
    print("3. Verificar logs do Render para mais detalhes")

if __name__ == "__main__":
    asyncio.run(testar_dados_reais()) 