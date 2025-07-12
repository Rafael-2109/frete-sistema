#!/usr/bin/env python3
"""
🔍 TESTE SIMPLES - Agent Type Issue

Script simplificado para testar agent_type usando Flask app context
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Usar Flask app context
from app import create_app

app = create_app()

with app.app_context():
    print("🔍 TESTE SIMPLES - Agent Type Issue")
    print("=" * 50)
    
    try:
        # Teste 1: Importar AgentType
        from app.claude_ai_novo.utils.agent_types import AgentType
        print("✅ AgentType importado com sucesso")
        
        # Teste 2: Testar FretesAgent
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        
        agent = FretesAgent()
        print("✅ FretesAgent criado com sucesso")
        
        # Verificar propriedades
        if hasattr(agent, 'agent_type'):
            print(f"✅ agent_type encontrado: {agent.agent_type}")
            print(f"✅ agent_type.value: {agent.agent_type.value}")
        else:
            print("❌ agent_type não encontrado")
            print(f"📋 Propriedades disponíveis: {[attr for attr in dir(agent) if not attr.startswith('_')]}")
        
        # Teste 3: Testar via factory
        from app.claude_ai_novo.coordinators.specialist_agents import create_fretes_agent
        
        agent2 = create_fretes_agent()
        print("✅ create_fretes_agent criado com sucesso")
        
        if hasattr(agent2, 'agent_type'):
            print(f"✅ Factory agent_type: {agent2.agent_type}")
            print(f"✅ Factory agent_type.value: {agent2.agent_type.value}")
        else:
            print("❌ Factory agent_type não encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc() 