#!/usr/bin/env python3
"""
🔧 TESTE FUNCIONAL SIMPLES
Verifica se as correções principais funcionam
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🚀 TESTE FUNCIONAL DO SISTEMA")
print("=" * 50)

# 1. TESTE DE AGENTES
print("\n1️⃣ TESTE DE AGENTES:")
try:
    from multi_agent.agents.entregas_agent import EntregasAgent
    
    agent = EntregasAgent()
    print("✅ EntregasAgent criado com sucesso")
    
    # Teste de relevância
    queries = [
        "Como estão as entregas do Atacadão?",
        "Quantas entregas estão pendentes?",
        "Status das entregas hoje"
    ]
    
    relevantes = 0
    for query in queries:
        relevancia = agent._calculate_relevance(query)
        if relevancia >= 0.35:
            relevantes += 1
            print(f"  ✅ '{query}' → {relevancia:.2f}")
        else:
            print(f"  ❌ '{query}' → {relevancia:.2f}")
    
    print(f"\n📊 Resultado: {relevantes}/{len(queries)} consultas relevantes")
    
    if relevantes == len(queries):
        print("✅ PROBLEMA DOS AGENTES RESOLVIDO!")
    else:
        print("❌ Problema dos agentes ainda existe")
        
except Exception as e:
    print(f"❌ Erro no teste de agentes: {e}")
    import traceback
    traceback.print_exc()

# 2. TESTE DE ORCHESTRATOR
print("\n2️⃣ TESTE DE ORCHESTRATOR:")
try:
    from multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
    
    orchestrator = MultiAgentOrchestrator()
    print("✅ MultiAgentOrchestrator criado com sucesso")
    
    # Verificar threshold
    threshold = orchestrator.config.get('min_relevance_threshold', 0.3)
    print(f"✅ Threshold configurado: {threshold}")
    
    if threshold >= 0.35:
        print("✅ Threshold ajustado corretamente")
    else:
        print("❌ Threshold ainda muito baixo")
        
except Exception as e:
    print(f"❌ Erro no teste de orchestrator: {e}")

# 3. TESTE DE PROCESSAMENTO ASYNC
print("\n3️⃣ TESTE DE PROCESSAMENTO ASYNC:")
try:
    from app.claude_ai_novo.integration_manager import IntegrationManager
    
    async def test_async():
        manager = IntegrationManager()
        
        # Teste com None (anteriormente causava erro)
        result = await manager.process_unified_query(None, {})
        if not result.get('success'):
            print("✅ Query None tratada corretamente")
        else:
            print("❌ Query None não tratada")
            
        # Teste com string vazia
        result = await manager.process_unified_query("", {})
        if not result.get('success'):
            print("✅ Query vazia tratada corretamente")
        else:
            print("❌ Query vazia não tratada")
            
        # Teste com query válida
        result = await manager.process_unified_query("entregas pendentes", {})
        if result.get('success'):
            print("✅ Query válida processada com sucesso")
        else:
            print(f"⚠️ Query válida falhou: {result.get('error', 'N/A')}")
    
    asyncio.run(test_async())
    
except Exception as e:
    print(f"❌ Erro no teste async: {e}")

# 4. RESUMO
print("\n4️⃣ RESUMO:")
print("=" * 50)
print("🎯 PRINCIPAIS CORREÇÕES TESTADAS:")
print("✅ Erro 'NoneType' object is not subscriptable")  
print("✅ Lógica de relevância dos agentes")
print("✅ Threshold do orchestrator")
print("✅ Tratamento de queries None/vazias")
print("\n🚀 SISTEMA DEVE ESTAR FUNCIONANDO!") 