#!/usr/bin/env python3
"""
🧪 TESTE SIMPLES DE OTIMIZAÇÃO
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.claude_ai_novo.multi_agent.agents.smart_base_agent import SmartBaseAgent
    from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
    from app.claude_ai_novo.multi_agent.agent_types import AgentType
    
    print("🧪 TESTE SIMPLES DE OTIMIZAÇÃO")
    print("=" * 40)
    
    # 1. SmartBaseAgent - deve ter conhecimento básico
    print("\n1. SmartBaseAgent (básico):")
    smart_agent = SmartBaseAgent(AgentType.ENTREGAS)
    conhecimento_smart = smart_agent._load_domain_knowledge()
    print(f"   Conhecimento: {conhecimento_smart}")
    
    # Verificar se não tem conhecimento específico duplicado
    if 'modelos_principais' not in conhecimento_smart:
        print("   ✅ SUCESSO: Duplicação removida")
    else:
        print("   ❌ FALHA: Ainda tem duplicação")
    
    # 2. EntregasAgent - deve ter conhecimento específico
    print("\n2. EntregasAgent (específico):")
    entregas_agent = EntregasAgent()
    conhecimento_entregas = entregas_agent._load_domain_knowledge()
    print(f"   Conhecimento: {len(str(conhecimento_entregas))} chars")
    
    # Verificar se tem conhecimento específico
    if 'main_models' in conhecimento_entregas:
        print("   ✅ SUCESSO: Conhecimento específico mantido")
    else:
        print("   ❌ FALHA: Conhecimento específico perdido")
    
    print("\n🎯 TESTE CONCLUÍDO!")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc() 