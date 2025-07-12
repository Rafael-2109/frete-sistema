#!/usr/bin/env python3
"""
🧪 TESTAR CORREÇÃO ASYNC
========================

Testa se a correção do problema de event loop funcionou.
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

async def testar_sistema():
    """Testa o sistema corrigido"""
    print("\n🧪 TESTANDO CORREÇÃO DO PROBLEMA ASYNC\n")
    
    # 1. Testar Claude Transition
    print("1️⃣ TESTANDO CLAUDE TRANSITION:")
    try:
        from app.claude_transition import processar_consulta_transicao
        
        # Testar query simples
        resultado = processar_consulta_transicao("Como estão as entregas do Atacadão?")
        print(f"   ✅ Query processada sem erro de event loop")
        print(f"   📝 Resultado: {resultado[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Testar SessionOrchestrator diretamente
    print("\n2️⃣ TESTANDO SESSION ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.session_orchestrator import get_session_orchestrator
        
        orchestrator = get_session_orchestrator()
        
        # Testar método _process_deliveries_status
        result = orchestrator._process_deliveries_status("entregas do atacadão")
        print(f"   ✅ _process_deliveries_status funcionou")
        print(f"   📝 Resultado: {result}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Testar IntegrationManager
    print("\n3️⃣ TESTANDO INTEGRATION MANAGER:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        integration = get_integration_manager()
        
        # Testar process_unified_query
        result = await integration.process_unified_query("entregas do atacadão")
        print(f"   ✅ process_unified_query funcionou")
        print(f"   📝 Resultado: {result}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n✅ TESTE COMPLETO!")

if __name__ == "__main__":
    # Executar teste
    asyncio.run(testar_sistema()) 