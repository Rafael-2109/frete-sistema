#!/usr/bin/env python3
"""
Teste direto do sistema Claude AI novo
"""

import logging
import traceback
import asyncio

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def testar_sistema():
    """Testa o sistema Claude AI novo diretamente"""
    try:
        print("1. Importando OrchestratorManager...")
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        print("✅ OrchestratorManager importado")
        
        print("\n2. Obtendo instância do OrchestratorManager...")
        manager = get_orchestrator_manager()
        print(f"✅ Manager obtido: {type(manager)}")
        
        print("\n3. Testando query simples...")
        query = "Como estão as entregas do Atacadão?"
        context = {
            'user_id': 1,
            'username': 'teste',
            'perfil': 'admin'
        }
        
        resultado = asyncio.run(manager.process_query(query, context))
        print(f"✅ Resultado obtido: {type(resultado)}")
        
        if isinstance(resultado, dict):
            print(f"   - Success: {resultado.get('success', False)}")
            print(f"   - Response: {str(resultado.get('response', ''))[:100]}...")
            print(f"   - Error: {resultado.get('error', 'None')}")
        else:
            print(f"   - Resultado: {str(resultado)[:100]}...")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        print("\nTraceback completo:")
        traceback.print_exc()
        return False

def testar_domain_agents():
    """Testa os domain agents diretamente"""
    try:
        print("\n\n4. Testando Domain Agents...")
        
        print("   a) Importando EntregasAgent...")
        from app.claude_ai_novo.coordinators.domain_agents import EntregasAgent
        print("   ✅ EntregasAgent importado")
        
        print("   b) Criando instância...")
        agent = EntregasAgent()
        print(f"   ✅ Agent criado: {type(agent)}")
        
        print("   c) Verificando método process_query...")
        has_method = hasattr(agent, 'process_query')
        print(f"   ✅ Método process_query existe: {has_method}")
        
        if has_method:
            print("   d) Testando process_query...")
            result = agent.process_query("Como estão as entregas do Atacadão?", {})
            print(f"   ✅ Resultado: {result.get('agent', 'unknown')} - relevance: {result.get('relevance', 0)}")
            
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO nos Domain Agents: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== TESTE DO SISTEMA CLAUDE AI NOVO ===\n")
    
    # Testar sistema principal
    sistema_ok = testar_sistema()
    
    # Testar domain agents
    agents_ok = testar_domain_agents()
    
    print("\n\n=== RESUMO ===")
    print(f"Sistema principal: {'✅ OK' if sistema_ok else '❌ FALHOU'}")
    print(f"Domain agents: {'✅ OK' if agents_ok else '❌ FALHOU'}")
    
    if sistema_ok and agents_ok:
        print("\n✅ TODOS OS TESTES PASSARAM!")
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!") 