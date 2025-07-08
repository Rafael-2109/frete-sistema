#!/usr/bin/env python3
"""
🔧 TESTE ESPECÍFICO - Correção do erro de convergência
"""

import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🔧 TESTE CORREÇÃO DE CONVERGÊNCIA")
print("=" * 50)

try:
    from app.claude_ai_novo.multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
    
    # Criar orchestrator
    orchestrator = MultiAgentOrchestrator()
    print("✅ MultiAgentOrchestrator criado com sucesso")
    
    # Simular respostas com scores iguais (que causavam erro)
    mock_responses = [
        {
            'response': 'Resposta do agente 1',
            'relevance': 0.8,
            'confidence': 0.7,
            'agent': 'entregas'
        },
        {
            'response': 'Resposta do agente 2', 
            'relevance': 0.8,  # Score igual - era isso que causava erro
            'confidence': 0.7,  # Score igual
            'agent': 'fretes'
        }
    ]
    
    mock_validation = {
        'validation_score': 1.0,
        'approval': True,
        'inconsistencies': []
    }
    
    # Testar convergência (onde estava o erro)
    try:
        import asyncio
        async def test_convergence():
            result = await orchestrator._converge_responses(
                "teste", mock_responses, mock_validation
            )
            return result
        
        resultado = asyncio.run(test_convergence())
        print("✅ Convergência funcionou sem erro!")
        print(f"📝 Resultado: {resultado[:100]}...")
        
    except Exception as e:
        if "'<' not supported" in str(e):
            print("❌ Erro de comparação ainda existe")
        else:
            print(f"❌ Outro erro: {e}")
    
    print("\n🎯 TESTE COMPLETO!")
    
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    import traceback
    traceback.print_exc() 