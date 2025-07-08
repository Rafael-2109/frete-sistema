#!/usr/bin/env python3
"""
Teste para verificar se a correção da relevância dos agentes funcionou
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from multi_agent.agents.entregas_agent import EntregasAgent
    from multi_agent.agents.fretes_agent import FretesAgent
    
    print("✅ Imports dos agentes OK")
    
    # Teste do agente de entregas
    entregas_agent = EntregasAgent()
    
    # Teste de relevância
    queries = [
        "Como estão as entregas do Atacadão?",
        "Quantas entregas estão pendentes?", 
        "Status das entregas hoje",
        "Sobre vendas e marketing"  # Deve ter relevância baixa
    ]
    
    print("\n📊 TESTE DE RELEVÂNCIA:")
    for query in queries:
        relevance = entregas_agent._calculate_relevance(query)
        print(f"Query: '{query}' -> Relevância: {relevance:.2f}")
    
    print("\n🎯 RESULTADO:")
    print("✅ Se relevância >= 0.35 para consultas de entregas, problema RESOLVIDO!")
    
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    import traceback
    traceback.print_exc() 